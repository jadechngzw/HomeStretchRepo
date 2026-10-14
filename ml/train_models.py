"""Train separate reproducible, exploratory REHAB anomaly models."""
import argparse
import hashlib
import json
import pickle
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from rehab_pipeline import (CHANNELS, EXERCISES, FEATURE_COLUMNS, clean_recording,
                            fit_segmentation, segment_repetitions, normalize_repetition,
                            calculate_features)


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train_exercise(data_dir, output_dir, exercise_id, name, fs):
    source = data_dir / f"{exercise_id}_1.npy"
    data = np.load(source, allow_pickle=False)
    if data.ndim != 3 or data.shape[2] != 6:
        raise ValueError(f"Unexpected shape: {data.shape}")
    # Exact duplicate source rows are kept together across the split.
    groups = np.array([hashlib.sha256(row.tobytes()).hexdigest() for row in data])
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_ids, test_ids = next(splitter.split(data, groups=groups))
    train_set = set(train_ids.tolist())
    sessions, skipped = {}, {}
    for index, record in enumerate(data):
        try:
            sessions[index] = clean_recording(record)
        except ValueError as error:
            skipped[str(index)] = str(error)
    settings = fit_segmentation([sessions[i] for i in train_ids if i in sessions], fs)
    rows = []
    for record_id, session in sessions.items():
        for segment_info, repetition in segment_repetitions(session, settings):
            if len(repetition) < 5:
                rows.append({"recording_index": record_id, **segment_info,
                             "split": "train" if record_id in train_set else "test",
                             "accepted": False, "reasons": ["too_short"]})
                continue
            features = calculate_features(normalize_repetition(repetition), fs)
            rows.append({"recording_index": record_id, **segment_info,
                         "split": "train" if record_id in train_set else "test", **features})
    interior = [r for r in rows if r["split"] == "train" and not r["is_edge"] and "completion_error" in r]
    if len(interior) < 20:
        raise ValueError(f"Only {len(interior)} training interior candidates.")
    # Duration quantiles exclude clear cycle-merging errors before completion calibration.
    durations = np.array([r["duration_seconds"] for r in interior])
    duration_low, duration_high = np.quantile(durations, [0.01, 0.99]).tolist()
    eligible = [r for r in interior if duration_low <= r["duration_seconds"] <= duration_high]
    completion_limit = float(np.quantile([r["completion_error"] for r in eligible], 0.95))
    for row in rows:
        if "completion_error" not in row:
            continue
        reasons = []
        if row["is_edge"]:
            reasons.append("recording_edge_uncertain")
        if not duration_low <= row["duration_seconds"] <= duration_high:
            reasons.append("duration_outside_training_q01_q99")
        if row["completion_error"] > completion_limit:
            reasons.append("completion_above_training_q95")
        row.update(accepted=not reasons, reasons=reasons)
    selected = {split: [r for r in rows if r["split"] == split and r["accepted"]]
                for split in ("train", "test")}
    matrices = {split: np.array([[r[f] for f in FEATURE_COLUMNS] for r in selected[split]], dtype=np.float64)
                for split in selected}
    if min(len(matrices["train"]), len(matrices["test"])) < 5:
        raise ValueError("Insufficient accepted training or held-out candidates.")
    scaler = StandardScaler().fit(matrices["train"])
    model = IsolationForest(n_estimators=200, max_samples=256, contamination=0.05,
                            random_state=42, n_jobs=1).fit(scaler.transform(matrices["train"]))
    for row in rows:
        if "completion_error" in row:
            vector = np.array([[row[f] for f in FEATURE_COLUMNS]])
            row["anomaly_score"] = float(-model.decision_function(scaler.transform(vector))[0])
    scores = {split: np.array([r["anomaly_score"] for r in selected[split]]) for split in selected}
    destination = output_dir / name
    destination.mkdir(parents=True, exist_ok=True)
    model_path = destination / f"{name}_isolation_forest.pkl"
    scaler_path = destination / "scaler.pkl"
    model_path.write_bytes(pickle.dumps(model, protocol=4))
    scaler_path.write_bytes(pickle.dumps(scaler, protocol=4))
    lower = int(exercise_id) >= 13
    config = {
        "schema_version": 1, "exercise_id": exercise_id, "exercise_name": name,
        "feature_columns": FEATURE_COLUMNS, "channel_order": list(CHANNELS),
        "source_columns": [0, 1, 2], "sensor": "S3" if lower else "S1",
        "dataset_placement": "lower leg, 10-20 cm below patella" if lower else "forearm, about 10 cm above dorsal wrist crease",
        "intended_watch_placement": "ankle" if lower else "wrist",
        "deployment_validated": False, "angle_units": "degrees",
        "sampling_rate_hz_assumed": fs, "timebase_verified_from_timestamps": False,
        "smoothing": {"type": "centered_moving_average", "window_samples": 5, "edge_mode": "nearest"},
        "angle_unwrap": {"period_degrees": 360, "axis": "time"},
        "source_quality": "reject adjacent angle jumps >180 degrees before unwrapping",
        "padding": "trim trailing rows zero across all six source columns before selecting first three",
        "baseline": "subtract first-five-sample per-channel mean after segmentation",
        "segmentation": settings,
        "duration_limits_seconds": [duration_low, duration_high],
        "completion_error": {"definition": "RMS of last-five-sample mean normalized pitch and roll",
                             "percentile": 95, "threshold_degrees": completion_limit,
                             "calibration_population": "training interior segments within training duration q01-q99",
                             "calibration_count": len(eligible)},
        "training_edge_policy": "exclude; retain in segment audit",
        "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
        "contamination": 0.05, "anomaly_score": "negative decision_function; positive means reference outlier",
        "anomaly_threshold": 0.0, "score_samples_threshold": float(model.offset_),
        "quality_failure_output": "unscorable; do not equate with typical/atypical",
    }
    versions = {"python": platform.python_version(), "numpy": np.__version__,
                "scipy": scipy.__version__, "scikit_learn": sklearn.__version__,
                "matplotlib": matplotlib.__version__}
    metadata = {
        "exercise_id": exercise_id, "exercise_name": name,
        "created_utc": datetime.now(timezone.utc).isoformat(), "status": "exploratory_unvalidated",
        "source_file": source.name, "source_sha256": sha256(source), "source_shape": list(data.shape),
        "unique_source_recordings": len(set(groups.tolist())), "participant_count": None,
        "participant_ids_available": False, "split_unit": "source recording grouped by exact duplicate hash",
        "train_recording_indices": train_ids.tolist(), "test_recording_indices": test_ids.tolist(),
        "skipped_recordings": skipped, "trimmed_padding_samples": int(sum(data.shape[1] - len(s) for s in sessions.values())),
        "segmented_candidates": len(rows), "training_interior_candidates": len(interior),
        "completion_calibration_candidates": len(eligible),
        "train_repetitions": len(selected["train"]), "test_repetitions": len(selected["test"]),
        "rejected_candidates": sum(not r["accepted"] for r in rows),
        "rejection_reason_counts_overlapping": dict(Counter(reason for r in rows for reason in r["reasons"])),
        "train_recordings_contributing": len({r["recording_index"] for r in selected["train"]}),
        "test_recordings_contributing": len({r["recording_index"] for r in selected["test"]}),
        "completion_threshold_degrees": completion_limit, "segmentation": settings,
        "train_reference_outlier_rate": float(np.mean(scores["train"] > 0)),
        "test_reference_outlier_rate": float(np.mean(scores["test"] > 0)),
        "accuracy": None, "sensitivity": None, "specificity": None,
        "review_flags": (["completion_p95_exceeds_45_degrees"] if completion_limit > 45 else []),
        "model_parameters": model.get_params(), "versions": versions,
        "model_bytes": model_path.stat().st_size, "scaler_bytes": scaler_path.stat().st_size,
        "artifact_sha256": {model_path.name: sha256(model_path), "scaler.pkl": sha256(scaler_path)},
        "pipeline_sha256": {f: sha256(Path(__file__).parent / f) for f in ("rehab_pipeline.py", "train_models.py")},
        "limitations": ["No correctness labels; outlier rates are not accuracy.",
                        "No patient mapping; split cannot establish generalization to unseen patients.",
                        "Source placement differs from intended watch placement.",
                        "Automatic cycle segmentation and nominal 50 Hz require validation.",
                        "Completion filtering narrows learned movement distribution.",
                        "Yaw uses source sensor fusion; six-axis watch transfer is unvalidated."],
    }
    # Verify serialized artifacts reproduce scores before reporting success.
    loaded_model = pickle.loads(model_path.read_bytes())
    loaded_scaler = pickle.loads(scaler_path.read_bytes())
    np.testing.assert_allclose(-loaded_model.decision_function(loaded_scaler.transform(matrices["test"])), scores["test"])
    metadata["serialization_verified"] = True
    save_json(destination / "feature_config.json", config)
    save_json(destination / "metadata.json", metadata)
    save_json(destination / "segment_audit.json", rows)
    plot_diagnostics(destination, sessions, rows, config, scores)
    print(f"{exercise_id} {name}: train={len(selected['train'])}, test={len(selected['test'])}, completion95={completion_limit:.2f}, channel={settings['channel_name']}", flush=True)
    return metadata


def plot_diagnostics(destination, sessions, rows, config, scores):
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), layout="constrained")
    fs = config["sampling_rate_hz_assumed"]
    channel = config["segmentation"]["channel_index"]
    for ax, record_id in zip(axes, list(sessions)[:3]):
        signal = sessions[record_id][:, channel]
        ax.plot(np.arange(len(signal)) / fs, signal, linewidth=1)
        for row in rows:
            if row["recording_index"] == record_id:
                ax.axvspan(row["start_sample"] / fs, row["end_sample"] / fs,
                           color="green" if row["accepted"] else "red", alpha=0.10)
                ax.axvline(row["start_sample"] / fs, color="gray", linewidth=0.6)
        ax.set(title=f"Recording {record_id}: green=retained, red=excluded", ylabel="Angle (degrees)", xlabel="Nominal seconds")
    fig.suptitle(destination.name + " / " + CHANNELS[channel])
    fig.savefig(destination / "segmentation_examples.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    for split in scores:
        ax.hist(scores[split], bins=25, alpha=0.5, label=split, density=True)
    ax.axvline(0, color="black", linestyle="--")
    ax.set(xlabel="Anomaly score (higher = more unusual)", ylabel="Density", title=destination.name)
    ax.legend()
    fig.savefig(destination / "score_distribution.png", dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True, help="REHAB root containing Rehab_exercise")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "models")
    parser.add_argument("--sampling-rate", type=float, default=50.0)
    args = parser.parse_args()
    if args.sampling_rate <= 0:
        parser.error("sampling rate must be positive")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output must be new or empty; preserve prior runs using a new output directory.")
    args.output.mkdir(parents=True, exist_ok=True)
    summaries = [train_exercise(args.data_root / "Rehab_exercise" / "d01_raw_data", args.output,
                               exercise_id, name, args.sampling_rate) for exercise_id, name in EXERCISES.items()]
    save_json(args.output / "training_summary.json", summaries)
    lines = ["# Training Results", "", "Generated by train_models.py. Counts refer to algorithmically segmented candidates, not labeled clinical repetitions or unique patients.", "",
             "| Exercise | Source rows | Train reps | Test reps | Excluded | Completion p95 (deg) | Axis | Held-out outliers |",
             "|---|---:|---:|---:|---:|---:|---|---:|"]
    for m in summaries:
        lines.append(f"| {m['exercise_name']} | {m['source_shape'][0]} | {m['train_repetitions']} | {m['test_repetitions']} | {m['rejected_candidates']} | {m['completion_threshold_degrees']:.2f} | {m['segmentation']['channel_name']} | {m['test_reference_outlier_rate']:.1%} |")
    lines += ["", "See ../METHODOLOGY.md for definitions, assumptions and limitations. Per-exercise JSON files record exact thresholds, split indices, versions and feature order."]
    (args.output / "TRAINING_RESULTS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
