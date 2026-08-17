import sys
import types
import unittest

import numpy as np


class _NoOp:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class _FakeTask:
    blocks = []

    def __init__(self):
        self.ai_channels = _NoOp()
        self.timing = _NoOp()
        self.triggers = types.SimpleNamespace(
            start_trigger=types.SimpleNamespace(
                cfg_dig_edge_start_trig=lambda *args, **kwargs: None,
                retriggerable=0,
            )
        )
        self._blocks = iter(self.blocks)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def start(self):
        return None

    def read(self, **_kwargs):
        return next(self._blocks)


fake_artdaq = types.ModuleType("artdaq")
fake_artdaq.Task = _FakeTask
fake_artdaq.constants = types.SimpleNamespace(
    TerminalConfiguration=types.SimpleNamespace(RSE=0),
    AcquisitionType=types.SimpleNamespace(FINITE=0),
    Edge=types.SimpleNamespace(RISING=1, FALLING=0),
)
sys.modules.setdefault("artdaq", fake_artdaq)

from fp_lock_pfi_trigger import FPWorkPointStabilizerPFI, State


def _bare_stabilizer(wavelength, voltage):
    stabilizer = FPWorkPointStabilizerPFI.__new__(FPWorkPointStabilizerPFI)
    stabilizer.wp_savgol_window = 7
    stabilizer.wp_savgol_poly = 2
    stabilizer.wp_extrema_n = 2
    stabilizer.wp_refine_radius = 3
    stabilizer.wp_min_peak_distance = 5
    stabilizer.wp_min_contrast = 0.003
    stabilizer.wp_min_span_nm = 0.03
    stabilizer.wp_linearity_min = 0.75
    stabilizer._scan_wl = np.asarray(wavelength, dtype=float)
    stabilizer._scan_v = np.asarray(voltage, dtype=float)
    stabilizer.workpoint_wl = 0.0
    stabilizer.workpoint_v = 0.0
    stabilizer.workpoint_slope = 0.0
    stabilizer.lock_range_nm = 0.3
    stabilizer.workpoint_mode = "auto"
    stabilizer.state = State.IDLE
    return stabilizer


def _fp_valley(wavelength, center, fwhm):
    distance = ((np.asarray(wavelength) - center + 2.0) % 4.0) - 2.0
    return 1.2 - 1.0 / (1.0 + (distance / (fwhm / 2.0)) ** 2)


class TriggeredSpectrumTests(unittest.TestCase):
    def test_complete_trigger_samples_keep_wavelength_resolution(self):
        _FakeTask.blocks = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        stabilizer = FPWorkPointStabilizerPFI.__new__(FPWorkPointStabilizerPFI)
        stabilizer.scan_start = 1540.0
        stabilizer.scan_stop = 1540.2
        stabilizer.scan_speed = 10.0
        stabilizer.sample_rate = 10000.0
        stabilizer.trigger_spacing_nm = 0.1
        stabilizer.trigger_timeout_s = 0.1
        stabilizer.first_read_timeout_s = 0.1
        stabilizer.daq = types.SimpleNamespace(channel_str="Dev1/ai7")
        stabilizer.laser = types.SimpleNamespace(start_sweep=lambda: None)
        stabilizer._trigger_line = lambda: "Dev1/PFI0"
        stabilizer._edge_const = lambda: 1

        wavelength, voltage, timeouts, received = stabilizer._read_triggered_spectrum(
            trigger_count=2,
            samples_per_trigger=3,
        )

        np.testing.assert_allclose(
            wavelength,
            [1540.0, 1540.001, 1540.002, 1540.1, 1540.101, 1540.102],
            atol=1e-10,
        )
        np.testing.assert_allclose(voltage, [1, 2, 3, 4, 5, 6])
        self.assertEqual(timeouts, 0)
        self.assertEqual(received, 2)

    def test_sharp_valley_half_height_is_found(self):
        rng = np.random.default_rng(20260817)
        trigger_starts = np.arange(1540.0, 1544.00001, 0.1)
        sample_offsets = np.arange(80, dtype=float) * 0.001
        wavelength = (trigger_starts[:, None] + sample_offsets).reshape(-1)
        wavelength = wavelength[wavelength <= 1544.0]
        center = 1542.027
        fwhm = 0.04
        voltage = _fp_valley(wavelength, center, fwhm)
        voltage += rng.normal(0.0, 0.002, voltage.size)

        stabilizer = _bare_stabilizer(wavelength, voltage)
        stabilizer.set_workpoint_auto()

        ideal_points = np.array([center - fwhm / 2.0, center + fwhm / 2.0])
        wavelength_error = float(np.min(np.abs(ideal_points - stabilizer.workpoint_wl)))
        self.assertEqual(stabilizer.state, State.SET)
        self.assertLess(wavelength_error, 0.01)
        self.assertAlmostEqual(stabilizer.workpoint_v, 0.7, delta=0.08)
        self.assertGreater(abs(stabilizer.workpoint_slope), 1.0)


if __name__ == "__main__":
    unittest.main()
