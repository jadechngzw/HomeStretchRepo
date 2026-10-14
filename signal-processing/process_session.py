from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


CSV_PATH = Path(
    "/Users/jadechng/Documents/ChatGPT/VITALWAVE/"
    "vitalwave_v0/recordings/"
    "session-1003_20261003-210347_a3b16da1.csv"
)

data = pd.read_csv(CSV_PATH)

# Use one shared time origin for all sensors.
data["time_sec"] = (
    data["watch_ms"] - data["watch_ms"].min()
) / 1000

# Keep invalid readings for now so their positions remain visible.
accel = data.loc[data["sensor"] == "acceleration"].copy()
gyro = data.loc[data["sensor"] == "gyroscope"].copy()
ppg = data.loc[data["sensor"] == "ppg_green"].copy()

for name, stream in [
    ("Accelerometer", accel),
    ("Gyroscope", gyro),
    ("Green PPG", ppg),
]:
    invalid_count = (stream["valid"] != 1).sum()
    print(f"{name}: {len(stream)} readings, {invalid_count} invalid")


fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

for ax, stream, title, unit in [
    (axes[0], accel, "Right-wrist acceleration", "g"),
    (axes[1], gyro, "Right-wrist rotation speed", "degrees/s"),
]:
    values = stream[["x", "y", "z"]].copy()

    # Leave gaps where readings were invalid.
    values.loc[stream["valid"] != 1, :] = float("nan")

    for column in ["x", "y", "z"]:
        ax.plot(
            stream["time_sec"],
            values[column],
            label=column,
            linewidth=0.8,
        )

    ax.set_title(title)
    ax.set_ylabel(unit)
    ax.legend()
    ax.grid(alpha=0.3)

axes[1].set_xlabel("Seconds from recording start")
plt.tight_layout()
plt.show()