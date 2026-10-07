"""Score offline orientation recordings with a saved exercise model."""
import json
import pickle
from pathlib import Path

import numpy as np

from rehab_pipeline import clean_recording, segment_repetitions, normalize_repetition, calculate_features


def score_recording(recording, model_directory):
    """Return candidate scores and quality status; load only trusted pickles.

    recording is a source-format (time, 6) orientation array in degrees.
    This is an offline reference, not a live raw-IMU or mobile interface.
    """
    directory = Path(model_directory)
    config = json.loads((directory / "feature_config.json").read_text())
    model = pickle.loads((directory / f"{config['exercise_name']}_isolation_forest.pkl").read_bytes())
    scaler = pickle.loads((directory / "scaler.pkl").read_bytes())
    session = clean_recording(recording, config["smoothing"]["window_samples"])
    results = []
    low, high = config["duration_limits_seconds"]
    for segment, repetition in segment_repetitions(session, config["segmentation"]):
        if len(repetition) < 5:
            results.append({**segment, "status": "unscorable", "reason": "too_short", "anomaly_score": None})
            continue
        features = calculate_features(normalize_repetition(repetition), config["sampling_rate_hz_assumed"])
        quality_ok = (not segment["is_edge"] and low <= features["duration_seconds"] <= high
                      and features["completion_error"] <= config["completion_error"]["threshold_degrees"])
        vector = np.array([[features[name] for name in config["feature_columns"]]])
        score = float(-model.decision_function(scaler.transform(vector))[0])
        results.append({**segment, "features": features, "quality_passed": quality_ok,
                        "anomaly_score": score,
                        "status": ("reference_outlier" if score > 0 else "reference_like") if quality_ok else "unscorable"})
    return results
