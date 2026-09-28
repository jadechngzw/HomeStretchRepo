"""
main.py — Mbient IMU Pipeline for Cloud Run
--------------------------------------------
Receives Eventarc events from GCS, downloads accelerometer + gyroscope CSVs,
runs the Mbient IMU pipeline, and writes results to Firestore.

Expects files to be uploaded in pairs with matching names:
    <session_name>_Accelerometer.csv
    <session_name>_Gyroscope.csv

Triggered by accelerometer file upload only — derives gyro filename automatically.
"""

import os
import json
import tempfile
import logging

import numpy as np
import pandas as pd
import joblib
from flask import Flask, request
from scipy.signal import butter, filtfilt, find_peaks
from google.cloud import storage, firestore

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

# =============================================================================
# CONFIG
# =============================================================================
MODEL_PATH   = 'isolation_forest.pkl'
SCALER_PATH  = 'scaler.pkl'
THRESHOLD    = -0.19
FEATURE_COLS = ['duration', 'norm_amp', 'dom_freq', 'log_tremor']
DEG2RAD      = np.pi / 180

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
# METRICS
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
# FEATURE EXTRACTION (per rep)
# =============================================================================
def extract_rep_features(rep_signal, rep_time, Fs, all_peak_amps):
    sig      = rep_signal
    duration = rep_time[-1] - rep_time[0]

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

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def run_pipeline_accel_only(accel_path, file_name):
    accel = pd.read_csv(accel_path)
    accel.columns = ['epoc_ms', 'timestamp', 'elapsed_s', 'ax', 'ay', 'az']

    Fs      = 1 / accel['elapsed_s'].diff().median()
    time    = accel['elapsed_s'].values
    sig_raw = accel['ay'].values

    log.info(f"Fs: {Fs:.1f} Hz | Duration: {time[-1]:.1f}s")

    start_t, end_t = detect_exercise_bounds(sig_raw, time, Fs)
    if start_t is not None:
        mask    = (time >= start_t) & (time <= end_t)
        time    = time[mask]
        sig_raw = sig_raw[mask]
    else:
        log.warning("Exercise bounds not detected, using full signal")

    sig_norm     = (sig_raw - np.mean(sig_raw)) / (np.std(sig_raw) + 1e-8)
    rep_segments = segment_reps(sig_norm, time, Fs)
    n_reps       = len(rep_segments)
    log.info(f"Reps detected: {n_reps}")

    if n_reps == 0:
        log.warning("No reps detected")
        return None

    all_peak_amps = [np.max(r['signal']) - np.min(r['signal']) for r in rep_segments]
    records = []
    for i, rep in enumerate(rep_segments):
        if len(rep['signal']) < 10:
            continue
        feats = extract_rep_features(rep['signal'], rep['time'], Fs, all_peak_amps)
        feats['rep_idx'] = i
        records.append(feats)

    df_reps = pd.DataFrame(records)
    df_reps[FEATURE_COLS] = df_reps[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)
    df_reps = df_reps.dropna(subset=FEATURE_COLS)

    iso_forest = joblib.load(MODEL_PATH)
    scaler     = joblib.load(SCALER_PATH)

    X = scaler.transform(df_reps[FEATURE_COLS])
    df_reps['anomaly_score'] = iso_forest.decision_function(X)
    df_reps['predicted']     = np.where(df_reps['anomaly_score'] > THRESHOLD, 'Typical', 'Atypical')

    n_typical        = int((df_reps['predicted'] == 'Typical').sum())
    n_atypical       = int((df_reps['predicted'] == 'Atypical').sum())
    atypical_rep_ids = df_reps[df_reps['predicted'] == 'Atypical']['rep_idx'].tolist()

    snr_ratio, snr_db            = compute_snr_ratio(sig_norm, Fs)
    tremor_ratio                 = compute_tremor_energy_ratio(sig_norm, Fs)
    log_tremor                   = np.log10(tremor_ratio + 1)
    classification, tremor_level = classify_movement(snr_db, log_tremor)

    return {
        'file_name':        file_name,
        'duration_sec':     float(time[-1] - time[0]),
        'num_reps':         n_reps,
        'num_typical':      n_typical,
        'num_atypical':     n_atypical,
        'atypical_rep_ids': atypical_rep_ids,
        'snr_db':           float(snr_db),
        'tremor_ratio':     float(log_tremor),
        'tremor_level':     tremor_level,
        'classification':   classification,
    }

# =============================================================================
# FLASK ROUTE — receives Eventarc events
# =============================================================================
@app.route("/", methods=["POST"])
def handle_event():
    event = request.get_json()
    if not event:
        return "Bad request", 400

    bucket_name = event.get("bucket", "")
    file_name   = event.get("name", "")

    if not file_name.lower().endswith(".csv"):
        log.info(f"Ignoring non-CSV file: {file_name}")
        return "ok", 200

    # Only trigger on accelerometer file
    if "_Accelerometer" not in file_name:
        log.info(f"Ignoring non-accelerometer file: {file_name}")
        return "ok", 200

    log.info(f"Processing: gs://{bucket_name}/{file_name}")

    gcs = storage.Client()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as accel_tmp:
        gcs.bucket(bucket_name).blob(file_name).download_to_filename(accel_tmp.name)
        accel_path = accel_tmp.name

    results = run_pipeline_accel_only(accel_path, file_name)
    if results is None:
        log.warning("Pipeline returned no results")
        return "ok", 200

    log.info(f"Results: {results}")

    db      = firestore.Client()
    session = os.path.basename(file_name).replace(".csv", "")
    db.collection("sessions").document(session).set(results)
    log.info(f"Firestore written → sessions/{session}")

    return "ok", 200

# =============================================================================
# HEALTH CHECK
# =============================================================================
@app.route("/", methods=["GET"])
def health():
    return "healthy", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
