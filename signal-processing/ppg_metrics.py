import heartpy as hp
import numpy as np
from pathlib import Path

sample_rate = 64.0
max_hr = 140
PPG_FILE = Path("C:/Users/ahasa/Documents/Fall2026Repos/PPG-Sport/dataset/S01L_running_ppg.npy")


def load_ppg_data():
    data = np.load(PPG_FILE).flatten()
    return data


def analyze_ppg(data):
    wd, m = hp.process(data, sample_rate)
    return wd, m


def extract_metrics(wd, m):
    rr_intervals = wd.get("RR_list", [])
    instantaneous_hrs = [60000 / rr for rr in rr_intervals if 300 < rr < 2000]

    time_above_limit_sec = round(sum(
        rr / 1000 for rr, hr in zip(rr_intervals, instantaneous_hrs)
        if hr > max_hr
    ), 2)

    total_beats = len(rr_intervals)
    rejected_beats = len(wd.get("removed_beats", []))
    valid_coverage_pct = round(((total_beats - rejected_beats) / total_beats) * 100, 1) if total_beats > 0 else 0.0

    metrics = {}
    metrics['bpm'] = round(m['bpm'], 1)
    metrics['peak_hr_bpm'] = round(max(instantaneous_hrs), 1) if instantaneous_hrs else None
    metrics['time_above_max_hr_sec'] = time_above_limit_sec
    metrics['max_hr_bpm'] = max_hr
    metrics['valid_signal_coverage_pct'] = valid_coverage_pct
    return metrics


def print_metrics(metrics):
    print("\n── PPG Cardiac Metrics ──────────────────────────")
    print(f"  Loaded File:              {PPG_FILE.name}")
    print(f"  Pulse Rate:               {metrics['bpm']} bpm")
    print(f"  Peak HR:                  {metrics['peak_hr_bpm']} bpm")
    print(f"  Exertion Limit:           {metrics['max_hr_bpm']} bpm")
    print(f"  Time Above Exertion:      {metrics['time_above_max_hr_sec']} sec")
    print(f"  Valid Signal Coverage:    {metrics['valid_signal_coverage_pct']}%")
    print("─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    data = load_ppg_data()
    print(f"Loaded: {PPG_FILE.name} | Shape: {data.shape} | Sample Rate: {sample_rate} Hz")
    wd, m = analyze_ppg(data)
    metrics = extract_metrics(wd, m)
    print_metrics(metrics)
