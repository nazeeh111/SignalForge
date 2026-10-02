"""Offline converter regressions. No acquisition or transmission is imported."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "offline-noise-sdr/generate/rf-pwm.py"


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.source = self.root / "input.iq"
        self.output = self.root / "timings.txt"
        self.original_output = b"previous complete result\n"
        self.output.write_bytes(self.original_output)
        self.samples = ((.25 + .15 * np.sin(np.arange(64) / 8)) *
                        np.exp(1j * np.arange(64) / 100)).astype(np.complex64)
        self.samples.tofile(self.source)

    def run_converter(self, *options, output=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "generate", "--input-file", str(self.source),
             "--output-file", str(output or self.output), "--fs-in", "64000",
             "--fs-out", "512000", "--f-if", "64000", *options],
            capture_output=True, text=True, timeout=8,
            env={**os.environ, "MPLBACKEND": "Agg"})

    def assert_rejected(self, *options):
        result = self.run_converter(*options)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.output.read_bytes(), self.original_output)

    def test_nonfinite_iq_is_rejected_without_hanging(self):
        self.samples[8] = complex(float("nan"), 0)
        self.samples.tofile(self.source)
        self.assert_rejected()

    def test_invalid_amplitude_preserves_previous_output(self):
        self.samples[8] = 2 + 0j
        self.samples.tofile(self.source)
        self.assert_rejected()

    def test_interpolation_overshoot_cannot_publish_invalid_timings(self):
        np.array([0, 0, 1, 1], dtype=np.complex64).tofile(self.source)
        self.assert_rejected()

    def test_constant_amplitude_normalization_is_rejected(self):
        np.full(64, .5 + 0j, np.complex64).tofile(self.source)
        self.assert_rejected("--normalize")

    def test_invalid_rates_are_rejected(self):
        for option, value in [("--fs-in", "0"), ("--fs-out", "-1"),
                              ("--f-if", "nan"), ("--fs-out", "nan")]:
            with self.subTest(option=option, value=value):
                self.assert_rejected(option, value)

    def test_truncated_and_short_input_are_rejected(self):
        for data in [b"", b"x", np.ones(3, np.complex64).tobytes(),
                     self.samples.tobytes() + b"x"]:
            with self.subTest(size=len(data)):
                self.source.write_bytes(data)
                self.assert_rejected()

    def test_input_alias_cannot_be_overwritten(self):
        original = self.source.read_bytes()
        for mode in ["same", "hardlink", "symlink"]:
            with self.subTest(mode=mode):
                alias = self.source if mode == "same" else self.root / mode
                if mode == "hardlink": os.link(self.source, alias)
                if mode == "symlink": alias.symlink_to(self.source)
                result = self.run_converter(output=alias)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.source.read_bytes(), original)

    def test_negative_only_carrier_completes(self):
        np.full(64, -.5 + 0j, np.complex64).tofile(self.source)
        result = self.run_converter("--f-if", "0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_bytes(), b"")

    def test_failed_publication_preserves_previous_output_and_cleans_temporary(self):
        spec = importlib.util.spec_from_file_location("rf_pwm", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for operation in ("fsync", "replace"):
            with self.subTest(operation=operation):
                with patch.object(module.os, operation, side_effect=OSError("injected write failure")):
                    with contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaises(module.click.ClickException):
                            module.generate.callback(str(self.source), str(self.output),
                                                     64000, 512000, 64000, False, False)
                self.assertEqual(self.output.read_bytes(), self.original_output)
                self.assertEqual(list(self.root.glob(".rf-pwm-*")), [])

    def test_valid_conversion_produces_nonnegative_timings(self):
        result = self.run_converter()
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [tuple(map(int, line.split())) for line in self.output.read_text().splitlines()]
        self.assertTrue(rows)
        self.assertTrue(all(0 <= high <= period and period > 0 for high, period in rows))


if __name__ == "__main__":
    unittest.main()
