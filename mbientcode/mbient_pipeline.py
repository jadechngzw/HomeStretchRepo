"""
mbient_pipeline_local.py
------------------------
Local test script for the Mbient IMU pipeline.
Prints what would be stored in Firestore to the command line.
Run with:
    python mbient_pipeline_local.py --accel accelerometer.csv --gyro gyroscope.csv
"""

import argparse
import json
import numpy as np
import pandas as pd
import joblib
from scipy.signal import butter, filtfilt, find_peaks
import os

# =============================================================================
# CONFIG
# =============================================================================
ACCEL_PATH     = None          # set via --accel arg
GYRO_PATH      = None          # set via --gyro arg
MODEL_PATH  = '/Volumes/disko!/HomeStretch/HomeStretchRepo/mbientcode/isolation_forest.pkl'
SCALER_PATH = '/Volumes/disko!/HomeStretch/HomeStretchRepo/mbientcode/scaler.pkl'
THRESHOLD      = -0.19         # tuned for Mbient
FEATURE_COLS   = ['duration', 'norm_amp', 'dom_freq', 'log_tremor']
DEG2RAD        = np.pi / 180

# =============================================================================
# FILTERS
# =============================================================================
def highpass(x, Fs, cutoff_hz, order=2):
    nyq = 0.5 * Fs
    b, a = butter(order, cutoff_hz / nyq, btype='high')
    return filtfilt(b, a, x)

def lowpass(x, Fs, cutoff_hz, order=2):
    nyq = 0.5 * Fs
    b, a = butter(order, cutoff_hz / nyq, btype='low')
    return filtfilt(b, a, x)

# =============================================================================
# EXERCISE BOUNDS DETECTION
# =============================================================================
def detect_exercise_bounds(signal, time, Fs, rms_window_sec=0.5, threshold_ratio=0.2):
    sig = lowpass(signal, Fs, 1, order=2)
    sig = highpass(sig, Fs, cutoff_hz=0.1, order=2)
    window_samples = int(rms_window_sec * Fs)
    rms = np.sqrt(np.convolve(sig**2, np.ones(window_samples)/window_samples, mode='same'))
    threshold = threshold_ratio * np.max(rms)
    active_indices = np.where(rms > threshold)[0]
    if len(active_indices) == 0:
        return None, None
    return time[active_indices[0]], time[active_indices[-1]]

# =============================================================================
# REP SEGMENTATION
# =============================================================================
def segment_reps(signal, time, Fs):
    sig = lowpass(signal, Fs, 1, order=2)
    sig = highpass(sig, Fs, 0.1, order=2)
    troughs, _ = find_peaks(-sig, prominence=0.5, distance=int(Fs * 1.0))
    rep_segments = []
    for i in range(len(troughs) - 1):
        t_start = time[troughs[i]]
        t_end   = time[troughs[i + 1]]
        mask    = (time >= t_start) & (time <= t_end)
        rep_segments.append({
            'signal':  signal[mask],
            'time':    time[mask],
            't_start': t_start,
            't_end':   t_end,
        })
    return rep_segments

# =============================================================================
# TREMOR ENERGY RATIO
# =============================================================================
def compute_tremor_energy_ratio(signal, Fs):
    signal = signal - np.mean(signal)
    freqs  = np.fft.rfftfreq(len(signal), d=1/Fs)
    power  = np.abs(np.fft.rfft(signal))**2
    move_p   = np.sum(power[(freqs >= 0.1) & (freqs <= 2)])
    tremor_p = np.sum(power[(freqs >= 3)   & (freqs <= 8)])
    if move_p == 0:
        return np.inf
    return tremor_p / move_p

# =============================================================================
# FEATURE EXTRACTION (per rep)
# =============================================================================
def extract_rep_features(rep_signal, rep_time, Fs, all_peak_amps):
    sig      = rep_signal
    t        = rep_time
    duration = t[-1] - t[0]

    peak_amp = np.max(sig) - np.min(sig)
    norm_amp = peak_amp / np.mean(all_peak_amps) if np.mean(all_peak_amps) > 0 else 0

    freqs    = np.fft.rfftfreq(len(sig), d=1/Fs)
    power    = np.abs(np.fft.rfft(sig))**2
    dom_freq = freqs[np.argmax(power)] if len(power) > 0 else 0

    tremor_ratio = compute_tremor_energy_ratio(sig, Fs)
    log_tremor   = np.log10(tremor_ratio + 1)

    return {
        'duration':   float(duration),
        'norm_amp':   float(norm_amp),
        'dom_freq':   float(dom_freq),
        'log_tremor': float(log_tremor),
    }

def compute_snr_ratio(signal, Fs):
    movement = lowpass(signal, Fs, cutoff_hz=2, order=2)
    movement = highpass(movement, Fs, cutoff_hz=0.1, order=2)
    noise    = highpass(signal, Fs, cutoff_hz=3, order=2)
    rms_s = np.sqrt(np.mean(movement**2))
    rms_n = np.sqrt(np.mean(noise**2))
    if rms_n == 0:
        return np.inf, np.inf
    snr_ratio = rms_s / rms_n
    return snr_ratio, float(20 * np.log10(snr_ratio))

def classify_movement(snr_db, log_tremor_ratio):
    if log_tremor_ratio > 0.02:
        return "Poor Control / Tremor Dominant", "High"
    elif log_tremor_ratio > 0.012:
        return "Noticeable Jitter", "Moderate"
    else:
        if snr_db > 18:
            return "Very Smooth", "Low"
        elif snr_db > 14:
            return "Good Control", "Low"
        else:
            return "Noticeable Jitter", "Low"

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def run_pipeline(accel_path, gyro_path):
    # --- Load ---
    accel = pd.read_csv(accel_path)
    gyro  = pd.read_csv(gyro_path)
    accel.columns = ['epoc_ms', 'timestamp', 'elapsed_s', 'ax', 'ay', 'az']
    gyro.columns  = ['epoc_ms', 'timestamp', 'elapsed_s', 'gx', 'gy', 'gz']

    # Convert gyro to rad/s
    for col in ['gx', 'gy', 'gz']:
        gyro[col] = gyro[col] * DEG2RAD

    Fs         = 1 / accel['elapsed_s'].diff().median()
    time       = accel['elapsed_s'].values
    sig_raw    = accel['ay'].values

    print(f"\n{'='*60}")
    print(f"  Mbient IMU Pipeline — Local Test")
    print(f"{'='*60}")
    print(f"  Accel file : {accel_path}")
    print(f"  Gyro file  : {gyro_path}")
    print(f"  Fs         : {Fs:.1f} Hz")
    print(f"  Duration   : {time[-1]:.1f} s")

    # --- Detect exercise bounds ---
    start_t, end_t = detect_exercise_bounds(sig_raw, time, Fs)
    if start_t is not None:
        mask    = (time >= start_t) & (time <= end_t)
        time    = time[mask]
        sig_raw = sig_raw[mask]
        print(f"  Exercise   : {start_t:.1f}s → {end_t:.1f}s")
    else:
        print("  Exercise bounds: not detected, using full signal")

    # --- Normalize ---
    sig_norm = (sig_raw - np.mean(sig_raw)) / (np.std(sig_raw) + 1e-8)

    # --- Segment reps ---
    rep_segments = segment_reps(sig_norm, time, Fs)
    n_reps = len(rep_segments)
    print(f"  Reps found : {n_reps}")

    if n_reps == 0:
        print("\n  ERROR: No reps detected. Check prominence/distance params.")
        return

    # --- Extract features ---
    all_peak_amps = [np.max(r['signal']) - np.min(r['signal']) for r in rep_segments]
    records = []
    for i, rep in enumerate(rep_segments):
        if len(rep['signal']) < 10:
            continue
        feats = extract_rep_features(rep['signal'], rep['time'], Fs, all_peak_amps)
        feats['rep_idx'] = i
        feats['t_start'] = float(rep['t_start'])
        feats['t_end']   = float(rep['t_end'])
        records.append(feats)

    df_reps = pd.DataFrame(records)

    # --- Clean infs/nans ---
    df_reps[FEATURE_COLS] = df_reps[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)
    df_reps = df_reps.dropna(subset=FEATURE_COLS)

    # --- Load model + scaler ---
    iso_forest = joblib.load(MODEL_PATH)
    scaler     = joblib.load(SCALER_PATH)

    X = scaler.transform(df_reps[FEATURE_COLS])
    df_reps['anomaly_score'] = iso_forest.decision_function(X)
    df_reps['predicted']     = np.where(df_reps['anomaly_score'] > THRESHOLD, 'Typical', 'Atypical')

    # =============================================================================
    # PRINT REP-LEVEL RESULTS
    # =============================================================================
    print(f"\n{'='*60}")
    print(f"  Rep-by-Rep Results")
    print(f"{'='*60}")
    print(f"  {'Rep':<5} {'t_start':>8} {'t_end':>8} {'duration':>10} {'norm_amp':>10} {'dom_freq':>10} {'log_tremor':>12} {'score':>8} {'label':>10}")
    print(f"  {'-'*95}")
    for _, row in df_reps.iterrows():
        marker = '  ← ATYPICAL' if row['predicted'] == 'Atypical' else ''
        print(
            f"  {int(row['rep_idx']):<5}"
            f" {row['t_start']:>8.2f}"
            f" {row['t_end']:>8.2f}"
            f" {row['duration']:>10.3f}"
            f" {row['norm_amp']:>10.3f}"
            f" {row['dom_freq']:>10.3f}"
            f" {row['log_tremor']:>12.6f}"
            f" {row['anomaly_score']:>8.4f}"
            f" {row['predicted']:>10}"
            f"{marker}"
        )

    # =============================================================================
    # SUMMARY
    # =============================================================================
    n_typical  = (df_reps['predicted'] == 'Typical').sum()
    n_atypical = (df_reps['predicted'] == 'Atypical').sum()
    atypical_rep_indices = df_reps[df_reps['predicted'] == 'Atypical']['rep_idx'].tolist()

    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    print(f"  Total reps   : {n_reps}")
    print(f"  Typical      : {n_typical}")
    print(f"  Atypical     : {n_atypical}")
    if atypical_rep_indices:
        print(f"  Atypical reps: {atypical_rep_indices}")
    else:
        print(f"  Atypical reps: none")

    # =============================================================================
    # FIRESTORE PAYLOAD (what would be written)
    # =============================================================================
    # --- Load model + scaler ---
    iso_forest = joblib.load(MODEL_PATH)
    scaler     = joblib.load(SCALER_PATH)

    X = scaler.transform(df_reps[FEATURE_COLS])
    df_reps['anomaly_score'] = iso_forest.decision_function(X)
    df_reps['predicted']     = np.where(df_reps['anomaly_score'] > THRESHOLD, 'Typical', 'Atypical')

    n_typical          = int((df_reps['predicted'] == 'Typical').sum())
    n_atypical         = int((df_reps['predicted'] == 'Atypical').sum())
    atypical_rep_ids   = df_reps[df_reps['predicted'] == 'Atypical']['rep_idx'].tolist()

    # --- Session-level metrics (on full trimmed signal) ---
    snr_ratio, snr_db    = compute_snr_ratio(sig_norm, Fs)
    tremor_ratio         = compute_tremor_energy_ratio(sig_norm, Fs)
    log_tremor           = np.log10(tremor_ratio + 1)
    classification, tremor_level = classify_movement(snr_db, log_tremor)

    # --- Build Firestore doc ---
    session_id = os.path.basename(accel_path).replace('.csv', '')

    firestore_doc = {
        'file_name':        os.path.basename(accel_path),
        'duration_sec':     round(float(time[-1] - time[0]), 2),
        'num_reps':         n_reps,
        'num_typical':      n_typical,
        'num_atypical':     n_atypical,
        'atypical_rep_ids': atypical_rep_ids,
        'snr_db':           round(float(snr_db), 4),
        'tremor_ratio':     round(float(log_tremor), 6),
        'tremor_level':     tremor_level,
        'classification':   classification,
    }

    # --- Print ---
    print(f"\n{'='*60}")
    print(f"  Rep-by-Rep")
    print(f"{'='*60}")
    for _, row in df_reps.iterrows():
        marker = '  ← ATYPICAL' if row['predicted'] == 'Atypical' else ''
        print(f"  Rep {int(row['rep_idx']):>2}  {row['t_start']:.2f}s → {row['t_end']:.2f}s  {row['predicted']}{marker}")

    print(f"\n{'='*60}")
    print(f"  Firestore Document Preview")
    print(f"  Collection: sessions  |  Document: {session_id}")
    print(f"{'='*60}")
    print(json.dumps(firestore_doc, indent=2))

    return firestore_doc


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mbient IMU pipeline local test')
    parser.add_argument('--accel', required=True, help='Path to accelerometer CSV')
    parser.add_argument('--gyro',  required=True, help='Path to gyroscope CSV')
    args = parser.parse_args()

    run_pipeline(args.accel, args.gyro)