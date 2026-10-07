"""Generate a compact all-exercise segmentation review sheet."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rehab_pipeline import EXERCISES, clean_recording


def plot_overview(data_root, models):
    fig, axes = plt.subplots(7, 2, figsize=(16, 21), layout="constrained")
    for ax, (exercise_id, name) in zip(axes.flat, EXERCISES.items()):
        config = json.loads((models / name / "feature_config.json").read_text())
        rows = json.loads((models / name / "segment_audit.json").read_text())
        record_id = next(r["recording_index"] for r in rows if r["accepted"])
        source = np.load(data_root / "Rehab_exercise" / "d01_raw_data" / f"{exercise_id}_1.npy")
        signal = clean_recording(source[record_id])[:, config["segmentation"]["channel_index"]]
        fs = config["sampling_rate_hz_assumed"]
        ax.plot(np.arange(len(signal)) / fs, signal, linewidth=1)
        for row in rows:
            if row["recording_index"] == record_id:
                ax.axvspan(row["start_sample"] / fs, row["end_sample"] / fs,
                           color="green" if row["accepted"] else "red", alpha=.1)
                ax.axvline(row["start_sample"] / fs, color="gray", linewidth=.5)
        ax.set(title=f"{exercise_id}: {name}\nrecord {record_id}, {config['segmentation']['channel_name']}",
               xlabel="Nominal seconds", ylabel="Degrees")
        ax.title.set_fontsize(9)
    fig.suptitle("Segmentation proposals: green retained, red excluded. Manual validation still required.")
    fig.savefig(models / "segmentation_overview.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    plot_overview(args.data_root, args.models)
