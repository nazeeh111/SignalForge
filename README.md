# SignalForge

Signal-generation research sources, offline I/Q conversion and platform-specific software-radio experiments.

[Try a small offline example](#try-the-converter-without-hardware) · [Source map](#source-map) · [Build requirements](#build-environment) · [Terms](#source-terms)

## Try the converter without hardware

From the repository root, in a Python environment with NumPy, SciPy and Click:

```sh
python3 -m pip install numpy scipy click
python3 - <<'PY'
import numpy as np
n = np.arange(64)
samples = ((0.25 + 0.15 * np.sin(n / 8)) * np.exp(1j * n / 100)).astype(np.complex64)
with open('demo-samples.iq', 'xb') as stream:
    samples.tofile(stream)
PY
python3 offline-noise-sdr/generate/rf-pwm.py generate --input-file demo-samples.iq --output-file demo-timings.txt --fs-in 64000 --fs-out 512000 --f-if 64000
```

This synthetic example produced **65 timing rows** in the checked environment (Python 3.14, NumPy 2.5.4, SciPy 1.18.1, Click 8.5.0). The first five were:

```text
942 11718
1328 15625
1422 15625
1514 15625
1603 15625
```

Each row is **high duration, period**, in integer nanoseconds. These are generated timing values, not measured RF output. The example exercises the offline converter only. Its I/Q creation refuses to overwrite an existing input; a successful conversion atomically replaces the named timing output. Use new filenames to preserve earlier runs.

For a diagnostic check, run `python3 -m unittest discover -s tests -v`. It covers malformed samples, amplitude/rate validation, aliases and failed output replacement as well as a valid conversion. The native transmit and modem paths have separate platform requirements below.

## Offline conversion

With NumPy, SciPy and Click installed, run:

```sh
python3 offline-noise-sdr/generate/rf-pwm.py generate --input-file samples.iq --output-file timings.txt
```

Input is a file of at least four finite `complex64` samples. Amplitudes must be at most one, or use `--normalize` for a varying-amplitude input. Sampling rates must be positive, and `--fs-out` must be an integer multiple of `--fs-in`. Fractional ratios are rejected because the retained resampler would otherwise shorten the generated timings. Input and output must be different files. Invalid inputs and failed publication preserve an existing output. Add `--plot` only when Matplotlib is installed. Conversion writes timing data and does not transmit a signal.

## Source map

| Path | Purpose |
| --- | --- |
| `offline-noise-sdr/generate/rf-pwm.py` | Convert stored I/Q samples to RF-PWM timing files |
| `offline-noise-sdr/transmit/` | Platform-specific timing-file implementation |
| `fldigi-noise-sdr/` | Modem integration and platform-specific implementation |
| `gnuradio/` | GNU Radio flowgraphs |
| `gnss/` | Existing satellite-navigation research fixtures and scripts |
| `scripts/` | Plotting and stored-data analysis |
| `configs/` | Application configuration examples |

I/Q stores the two components of a complex signal. RF-PWM represents a radio waveform as pulse timings. Existing filenames, commands, binary layouts, rates and platform options retain their established meanings.

## Build environment

The Makefiles select architecture with `ARCH` and operation with `OP`. Their existing defaults and target names are unchanged. The sources target Linux/Windows x86, Android ARM and OpenWrt MIPS toolchains; this macOS checkout does not provide a matching cross-compilation environment.

Use the existing [offline Makefile](offline-noise-sdr/transmit/Makefile), [modem Makefile](fldigi-noise-sdr/Makefile) and [environment provisioning reference](vagrant/bootstrap.sh) to inspect requirements. Provisioning scripts are not part of the publication checks.

[Preservation and verification](COMPATIBILITY.md) documents offline source checks. No RF transmission, acquisition or connected-device activity was performed. Bundled component terms remain in [third-party notices](THIRD_PARTY_NOTICES.md).

## Source terms

The combined source retains its [GPL terms](LICENSE) and separate component notices. New presentation and documentation are available under [MIT](LICENSE-MIT); see [scope](COPYRIGHT).
