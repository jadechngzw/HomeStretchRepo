"""Focused checks for channel mapping, padding, features and segmentation."""
import unittest

import numpy as np

from rehab_pipeline import (FEATURE_COLUMNS, calculate_features, clean_recording,
                            normalize_repetition, segment_repetitions)


class PipelineTests(unittest.TestCase):
    def test_sensor_selection_padding_and_wrap(self):
        record = np.ones((100, 6))
        record[:80, 0] = np.arange(80) * 2 + 160
        record[:80, 3:] = 900
        record[80:] = 0
        signal = clean_recording(record)
        self.assertEqual(signal.shape, (80, 3))
        self.assertLess(np.max(np.abs(np.diff(signal[:, 0]))), 3)
        np.testing.assert_allclose(signal[:, 1:], 1)

    def test_ambiguous_wrap_is_rejected(self):
        record = np.ones((100, 6))
        record[50:, 1] = -300
        with self.assertRaisesRegex(ValueError, "adjacent angle jump"):
            clean_recording(record)

    def test_features_preserve_amplitude_and_remove_offsets(self):
        t = np.linspace(0, 2 * np.pi, 201)
        signal = np.column_stack([30 * np.sin(t), 5 * np.cos(t), -20 * np.sin(t)])
        features = calculate_features(normalize_repetition(signal))
        shifted = calculate_features(normalize_repetition(signal + [120, 30, -40]))
        self.assertEqual(list(features), FEATURE_COLUMNS)
        self.assertEqual(len(features), 17)
        np.testing.assert_allclose(list(features.values()), list(shifted.values()), atol=1e-8)
        self.assertAlmostEqual(features["pitch_rom"], 60)
        self.assertAlmostEqual(features["duration_seconds"], 4)
        self.assertAlmostEqual(features["pitch_roll_correlation"], -1)

    def test_flat_channels_are_finite(self):
        features = calculate_features(np.zeros((20, 3)))
        self.assertTrue(np.isfinite(list(features.values())).all())

    def test_edges_remain_flagged(self):
        t = np.linspace(0, 8 * np.pi, 801)
        signal = np.column_stack([30 * np.cos(t)] * 3)
        segments = list(segment_repetitions(signal, {"channel_index": 0,
                        "minimum_distance_samples": 100, "prominence_degrees": 20}))
        self.assertEqual(len(segments), 5)
        self.assertTrue(segments[0][0]["is_edge"])
        self.assertTrue(segments[-1][0]["is_edge"])
        self.assertEqual(sum(not meta["is_edge"] for meta, _ in segments), 3)


if __name__ == "__main__":
    unittest.main()
