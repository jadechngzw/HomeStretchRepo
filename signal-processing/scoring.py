import random
import numpy as np
from pathlib import Path
from ppg_metrics import analyze_ppg, extract_metrics
from read_watch_data import load_watch_data, load_ppg_data
from imu_metrics import (
    segment_reps,
    classify_repetitions,
    compute_snr_db,
    compute_tremor_energy_ratio,
    detect_rest_periods,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
FILEPATH = REPO_ROOT / "mbientcode" / "mbientdata" / "left_atypical_Accelerometer.csv" #path to IMU data 
MODELPATH = REPO_ROOT / "mbientcode-cloud" / "isolation_forest.pkl"
SCALERPATH = REPO_ROOT / "mbientcode-cloud" / "scaler.pkl"

# Thresholds and file path can change that can be clinician defined
rep_goal = 10
snr_threhold = 15
smoothness_threshold = 0.7
hr_rest_max = 100
hr_active_max = 160


# Reading IMU Data
def read_imu_data(file_path, signal_column="ay",
                  model_path=MODELPATH, scaler_path=SCALERPATH):

    data = load_watch_data(file_path, signal_column)
    signal, time, sample_rate = data["signal"], data["time"], data["sample_rate"]

    all_reps = segment_reps(signal, time, sample_rate)

    reps = [
        rep for rep in all_reps
        if 0.8 <= rep["t_end"] - rep["t_start"] <= 3.0  # REMOVES ANY REPS WITH UNREALISTIC LENGTHS
    ]

    results = classify_repetitions(reps, sample_rate, model_path, scaler_path)

    if reps:
        exercise_mask = (
            (time >= reps[0]["t_start"]) &
            (time <= reps[-1]["t_end"])
        )

        rest_periods = detect_rest_periods(
            signal[exercise_mask],
            time[exercise_mask],
            sample_rate,
        )
    else:
        rest_periods = []

    rest_time = sum(period["duration"] for period in rest_periods)

    rep_durations = [
        round(float(rep["t_end"] - rep["t_start"]), 2)
        for rep in reps
    ]

    exercise_time = ( reps[-1]["t_end"] - reps[0]["t_start"]
        if reps else 0
    )

    active_time = max(exercise_time - rest_time, 0)

    total_duration = float(time[-1] - time[0])
    classifications = results["classification"].tolist() if not results.empty else []
    typical_reps = classifications.count("Typical")
    atypical_reps = classifications.count("Atypical")

    snr = compute_snr_db(signal, sample_rate)
    tremor = compute_tremor_energy_ratio(signal, sample_rate)
    smoothness = np.clip(1 / (1 + tremor), 0, 1)

    return {
        "accepted_reps": len(results),
        "rep_durations": rep_durations,
        "average_rep_duration": round(np.mean(rep_durations), 2) if rep_durations else 0,
        "active_time": round(float(active_time), 2),
        "rest_time": round(float(rest_time), 2),
        "rest_periods": rest_periods,
        "rest_status": "Rest detected" if rest_periods else "No rest detected",
        "snr_db": round(float(snr), 2),
        "tremor_score": round(float(tremor), 4),
        "smoothness": round(float(smoothness), 2),
        "typical_reps": typical_reps,
        "atypical_reps": atypical_reps,
        "rep_classifications": classifications,
        "classification": max(set(classifications), key=classifications.count)
                        if classifications else "Unknown",
        "duration": round(total_duration, 2),
    }


# HR Data
def read_hr_data():
    return load_ppg_data()


# Patient State
def infer_patient_state(imu, hr):
    flags = []
    score = 0

    if imu["accepted_reps"] >= rep_goal:
        flags.append("Rep Goal Met")
    else:
        flags.append("Rep Goal Not Met")
        score += 1

    if imu["snr_db"] < snr_threhold:
        flags.append("Low SNR")
        score += 1
    else:
        flags.append("Good Signal Quality")

    if imu["smoothness"] < smoothness_threshold or imu["classification"] == "Atypical":
        flags.append("Movement Quality Issue")
        score += 1
    else:
        flags.append("Good Movement Quality")

    if hr["bpm"] > hr_rest_max:
        flags.append("Elevated Resting HR")
        score += 1
    else:
        flags.append("Normal Resting HR")

    if hr["peak_hr_bpm"] > hr_active_max:
        flags.append("Elevated Active HR")
        score += 1
    else:
        flags.append("Normal Active HR")

    # Final Scoring
    if score == 0:
        patient_state = "Good"
    elif score <= 2:
        patient_state = "Moderate"
    else:
        patient_state = "Concern - Flagging your caretaker for review"

    return patient_state, flags

# Main
if __name__ == "__main__":
    imu = read_imu_data(FILEPATH)
    hr = read_hr_data()
    patient_state, flags = infer_patient_state(imu, hr)

    print("\n── Patient Session Summary ──────────────────")
    print(f"  Accepted Reps:       {imu['accepted_reps']}")
    print(f"  Rep Durations:       {imu['rep_durations']} sec")
    print(f"  Avg. Rep Duration:   {imu['average_rep_duration']} sec/rep")
    print(f"  Active Time:         {imu['active_time']} sec")
    print(f"  Rest Time:           {imu['rest_time']} sec")
    print(f"  Rest Status:         {imu['rest_status']}")
    print(f"  SNR:                 {imu['snr_db']} dB")
    print(f"  Tremor Score:        {imu['tremor_score']}")
    print(f"  Smoothness:          {imu['smoothness']}")
    print(f"  Typical Reps:        {imu['typical_reps']}")
    print(f"  Atypical Reps:       {imu['atypical_reps']}")
    print(f"  Rep Classifications: {imu['rep_classifications']}")
    print(f"  Overall Motion:      {imu['classification']}")
    print(f"  Total Duration:      {imu['duration']} sec")
    print(f"  Pulse Rate:          {hr['bpm']} bpm")
    print(f"  Peak HR:             {hr['peak_hr_bpm']} bpm")
    print(f"  Time Above Exertion: {hr['time_above_max_hr_sec']} sec")
    print(f"  Valid Coverage:      {hr['valid_signal_coverage_pct']}%")

    print(f"\n── Patient State: {patient_state}")

    print("\n── Flags:")
    if flags:
        for flag in flags:
            print(f"  • {flag}")
    else:
        print("  • No flags")