# SignalForge preservation record

## Change boundary

The repository presentation, documentation entry points and source comments were updated. Existing executable entry points, algorithms, defaults, filenames, formats and numerical operations remain unchanged. The combined source retains its GPL terms and separate bundled-component notices. New presentation and documentation are MIT.

## Verified locally

All six Python files passed parsing with baseline-identical executable syntax trees. All 98 tracked native-source, header, Makefile and flowgraph files preserve executable content; changed attribution comments are non-executable. Eight shell scripts passed `bash -n`. The unchanged offline converter function produced byte-identical timing files and stdout in six small deterministic cases using NumPy 2.3.5/SciPy 1.18.1. This isolated function check did not execute the CLI, plots or transmit code. A full native build was unavailable because the specified Linux/Windows/Android/OpenWrt toolchains are not present on this macOS host.

The source comparison checks Python syntax trees without comments or source locations, so changes in documentation do not obscure computational changes. This is an equivalence check against the supplied source, not a claim that every experiment is correct or portable. Existing invalid-escape warnings in legacy Python strings also occur in the baseline and were not changed.

## Execution boundary

No RF transmission, signal acquisition, connected-device commands, firmware changes or live-target experiments were performed. No external experimental datasets were downloaded. Build and reproduction requirements remain those documented by the source; absent dependencies have not been silently replaced with new algorithms.
