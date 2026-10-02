#!/usr/bin/python3.6
# SignalForge offline sample-to-timing conversion; validated inputs, retained timing format.

# SignalForge research workspace

import os
from pathlib import Path
import tempfile

import numpy as np
import click
from scipy.interpolate import interp1d

@click.group()
def cli():
    """
    """

@cli.command()
@click.option("--input-file", default="/tmp/time",
              show_default=True,
              type=click.Path(dir_okay=False),
              help="File with baseband IQ data (gr-complex format).")
@click.option("--output-file", default="/tmp/rfpwm", 
              show_default=True,
              type=click.Path(dir_okay=False),
              help="File with RF-PWM timings.")
@click.option("--fs-in", default=48e3, show_default=True,
              help="Sampling frequency of the IQ file.")
@click.option("--fs-out", default=4.8e6, show_default=True,
              help="Sampling frequency of the IQ file.")
@click.option("--f-if", default=5e3, show_default=True,
              help="Intermediate frequency.")
@click.option("--plot/--no-plot", default=False, show_default=True,
              help="Visualize data (use only with small files/frequencies).")
@click.option("--normalize/--no-normalize", default=False, show_default=True,
              help="Normalize amplitude.")
def generate(input_file, output_file, fs_in, fs_out, f_if, plot, normalize):
    """
    Generate RF-PWM square wave timings starting from IQ baseband
    """
    if not all(np.isfinite(value) for value in (fs_in, fs_out, f_if)):
        raise click.ClickException("Sampling and intermediate frequencies must be finite.")
    if fs_in <= 0 or fs_out < fs_in or not np.isfinite(fs_out / fs_in):
        raise click.ClickException("Sampling rates must be positive, with fs-out at least fs-in.")
    source = Path(input_file)
    destination = Path(output_file)
    try:
        if source.resolve() == destination.resolve() or (destination.exists() and source.samefile(destination)):
            raise click.ClickException("Input and output must be different files.")
        if not source.is_file():
            raise click.ClickException("Input must be a regular I/Q file.")
        print("Opening IQ file")
        with source.open("rb") as f:
            size = os.fstat(f.fileno()).st_size
            if size < 4 * np.dtype(np.complex64).itemsize or size % np.dtype(np.complex64).itemsize:
                raise click.ClickException("Input must contain at least four complete complex64 samples.")
            data = np.fromfile(f, dtype=np.complex64)
        if data.nbytes != size or not np.isfinite(data).all():
            raise click.ClickException("I/Q samples must be complete and finite.")
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc

    print("Starting RF-PWM conversion")
    print("Amplitude and phase")
    a = np.absolute(data)
    phi = np.angle(data)

    if(normalize):
        print("Normalization")
        spread = np.ptp(a)
        if not np.isfinite(spread) or spread <= 0:
            raise click.ClickException("Normalization requires varying finite amplitudes.")
        a = (a - np.min(a)) / spread
    if not np.isfinite(a).all() or np.any(a > 1):
        raise click.ClickException("I/Q amplitudes must be at most 1; use --normalize for varying amplitudes.")

    print("Pre-distortion") 
    a2 = np.arcsin(a) / np.pi

    print("Resampling fs-in to fs-out")
    Nsa = len(a2)*int(fs_out/fs_in)
    x = np.linspace(0,len(a2),len(a2))
    xresampled = np.linspace(0,len(a2),len(a2)*int(fs_out/fs_in))

    fa2 = interp1d(x, a2, kind='cubic')
    fphi2 = interp1d(x, phi, kind='cubic')
    a2_resampled = fa2(xresampled)
    phi_resampled = fphi2(xresampled)
    # Cubic interpolation can overshoot even when every input amplitude is valid.
    if not np.isfinite(a2_resampled).all() or np.any(a2_resampled < -1e-12) or np.any(a2_resampled > .5 + 1e-12):
        raise click.ClickException("Interpolated amplitudes leave the valid pulse-width range.")
    a2_resampled = np.clip(a2_resampled, 0, .5)

    # a2_resampled = a2.repeat(int(fs_out/fs_in))
    # phi_resampled = phi.repeat(int(fs_out/fs_in)) 

    print("Generating IF carrier")
    # lambda function to rf-pwm modulate a square wave
    modulate = lambda phi, i : np.sign(np.cos(2*np.pi*f_if*i/fs_out +
       + phi))
    time = np.linspace(0, Nsa, Nsa)
    with np.errstate(over='ignore', invalid='ignore'):
        y = modulate(phi_resampled, time)
    if not np.isfinite(y).all() or not np.isfinite(a2_resampled).all():
        raise click.ClickException("Conversion exceeds finite numerical limits.")

    print("Generating pulse timings")
    th = []
    t = []
    i = 0
    if(y[i] < 0):
       while i < len(y) and y[i] < 0:
           i = i + 1
    while(i < len(y)):
       j = 0
       while i+j < len(y) and y[i+j] >= 0:
           j = j + 1
       while i+j < len(y) and y[i+j] < 0:
           j = j + 1
       t.append(j)
       th.append(a2_resampled[i] * j)
       i = i + j
    
    th = np.array(th)
    t = np.array(t)
    
    print("Saving output file with timings")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=destination.parent,
                                         prefix=".rf-pwm-", delete=False) as f:
            temporary = Path(f.name)
            for x,q in zip(th,t):
                Th_ns = 1e9 * x / fs_out
                T_ns = 1e9 * q / fs_out
                f.write("%d %d\n" % (Th_ns, T_ns))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, destination)
    except (OSError, ValueError, OverflowError) as exc:
        raise click.ClickException("Cannot save timing file: " + str(exc)) from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    
    if(plot):
        from matplotlib import pyplot as plt
        time = [i/fs_in for i in range(len(data))]
        time2 = [i/fs_out for i in range(len(y))]
        
        plt.subplots_adjust(hspace = 1) 
        
        plt.subplot(5, 1, 1)
        plt.title("Spectrogram")
        plt.xlabel("Time (s)")
        plt.ylabel("Frequency (Hz)")
        plt.specgram(data, Fs=fs_in)
        
        plt.subplot(5, 1, 2)
        plt.title("IQ data")
        plt.xlabel("Time (s)")
        plt.ylabel("I(t), Q(t)")
        plt.plot(time, data.real, label="I(t)")
        plt.plot(time, data.imag, label="Q(t)")
        plt.legend()
        
        plt.subplot(5, 1, 3)
        plt.title("Amplitude and pre-distorted amplitude")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude(t)")
        plt.plot(time, a, label="Original")
        plt.plot(time, a2, label="Pre-distorted")
        plt.legend()
        
        plt.subplot(5, 1, 4)
        plt.title("Phase")
        plt.xlabel("Time (s)")
        plt.ylabel("Phase(t) (rad)")
        plt.plot(time, phi)
 
        plt.subplot(5, 1, 5)
        plt.title("RF-PWM")
        plt.xlabel("Time (s)")
        plt.ylabel("RF-PWM(t)")
        plt.plot(time2, y)
        plt.show()

if __name__ == "__main__":
    cli()
