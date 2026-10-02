# SignalForge preservation record

## Change boundary

The repository presentation, documentation entry points and source comments were updated. At initial publication, executable entry points, algorithms, defaults, filenames, formats and numerical operations were preserved. The later offline converter repair below changes invalid-input and output-publication behavior. The combined source retains its GPL terms and separate bundled-component notices. New presentation and documentation are MIT.

## Verified locally

All six Python files passed parsing with baseline-identical executable syntax trees. All 98 tracked native-source, header, Makefile and flowgraph files preserve executable content; changed attribution comments are non-executable. Eight shell scripts passed `bash -n`. The unchanged offline converter function produced byte-identical timing files and stdout in six small deterministic cases using NumPy 2.3.5/SciPy 1.18.1. This isolated function check did not execute the CLI, plots or transmit code. A full native build was unavailable because the specified Linux/Windows/Android/OpenWrt toolchains are not present on this macOS host.

The source comparison checks Python syntax trees without comments or source locations, so changes in documentation do not obscure computational changes. This is an equivalence check against the supplied source, not a claim that every experiment is correct or portable. Existing invalid-escape warnings in legacy Python strings also occur in the baseline and were not changed.

## Execution boundary

No RF transmission, signal acquisition, connected-device commands, firmware changes or live-target experiments were performed. No external experimental datasets were downloaded. Build and reproduction requirements remain those documented by the source; absent dependencies have not been silently replaced with new algorithms.

## Offline converter repair (October 2, 2026)

`offline-noise-sdr/generate/rf-pwm.py` now rejects incomplete/nonfinite complex64 input, fewer than four samples, nonfinite frequencies, invalid sampling rates, amplitudes outside the arcsine domain, undefined constant-amplitude normalization, and cubic interpolation overshoot outside the pulse-width domain (apart from floating-point roundoff). Input/output aliases, including hard links and symlinks, are rejected. A carrier that stays negative returns an empty timing file; zero-valued carrier samples are treated as high so the pulse loop always advances. Existing finite positive/negative carrier calculations and the text timing format are preserved.

Timing output is written to a temporary file beside the destination, flushed and synced before replacement. Validation and failed publication leave an existing output intact. This is file-publication protection, not a power-loss guarantee for every filesystem. Plotting dependencies load only when `--plot` is requested.

Run the converter checks with `python3 -m unittest discover -s tests -v` in an environment with NumPy, SciPy and Click. They execute the actual offline CLI with synthetic input, check failure preservation and input aliases, and inject sync/replacement failures. No transmitter, acquisition or hardware path is imported or executed. Six prior valid conversion fixtures remain byte-identical to the pre-repair converter; this does not validate every modulation or platform build.
