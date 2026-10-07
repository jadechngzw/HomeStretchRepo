"""Verify exported schemas, split isolation, thresholds and inference parity."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from predict import score_recording
from rehab_pipeline import EXERCISES, FEATURE_COLUMNS


def verify(data_root, models):
    total_train = total_test = 0
    for exercise_id, name in EXERCISES.items():
        folder = models / name
        metadata = json.loads((folder / "metadata.json").read_text())
        config = json.loads((folder / "feature_config.json").read_text())
        audit = json.loads((folder / "segment_audit.json").read_text())
        assert config["feature_columns"] == FEATURE_COLUMNS
        assert len(FEATURE_COLUMNS) == 17
        train_ids = set(metadata["train_recording_indices"])
        test_ids = set(metadata["test_recording_indices"])
        assert not train_ids & test_ids
        source = data_root / "Rehab_exercise" / "d01_raw_data" / f"{exercise_id}_1.npy"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata["source_sha256"]
        data = np.load(source, allow_pickle=False)
        train_hashes = {hashlib.sha256(data[i].tobytes()).hexdigest() for i in train_ids}
        test_hashes = {hashlib.sha256(data[i].tobytes()).hexdigest() for i in test_ids}
        assert not train_hashes & test_hashes
        low, high = config["duration_limits_seconds"]
        calibration = [r["completion_error"] for r in audit if r["split"] == "train"
                       and not r["is_edge"] and "completion_error" in r
                       and low <= r["duration_seconds"] <= high]
        np.testing.assert_allclose(np.quantile(calibration, .95), metadata["completion_threshold_degrees"])
        for split in ("train", "test"):
            accepted = [r for r in audit if r["split"] == split and r["accepted"]]
            assert len(accepted) == metadata[f"{split}_repetitions"]
            assert all(not r["is_edge"] for r in accepted)
            assert np.isfinite([[r[f] for f in FEATURE_COLUMNS] for r in accepted]).all()
        record_id = next(r["recording_index"] for r in audit if r["split"] == "test" and r["accepted"])
        predictions = score_recording(data[record_id], folder)
        expected = [r for r in audit if r["recording_index"] == record_id]
        assert len(predictions) == len(expected)
        for prediction, row in zip(predictions, expected):
            assert prediction["start_sample"] == row["start_sample"]
            if "anomaly_score" in row:
                np.testing.assert_allclose(prediction["anomaly_score"], row["anomaly_score"])
                assert prediction["quality_passed"] == row["accepted"]
        for filename, checksum in metadata["artifact_sha256"].items():
            assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == checksum
        total_train += metadata["train_repetitions"]
        total_test += metadata["test_repetitions"]
        print(f"PASS {name}")
    print(f"Verified {len(EXERCISES)} models; {total_train} training and {total_test} held-out candidates.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--models", type=Path, default=Path(__file__).parent / "models")
    args = parser.parse_args()
    verify(args.data_root, args.models)
