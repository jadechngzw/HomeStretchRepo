#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks

''' csv file keys: 
'time', 'seconds_elapsed', 'rotationRateX', 'rotationRateY',
'rotationRateZ', 'gravityX', 'gravityY', 'gravityZ', 'accelerationX',
'accelerationY', 'accelerationZ', 'quaternionW', 'quaternionX',
'quaternionY', 'quaternionZ', 'pitch', 'roll', 'yaw'

Sensor logger sampling rate is 100 Hz
'''



# =========================
# FILTERS
# =========================
def highpass(x, Fs, cutoff_hz, order=2):
    nyq = 0.5 * Fs
    b, a = butter(order, cutoff_hz / nyq, btype='high')
    return filtfilt(b, a, x)

def lowpass(x, Fs, cutoff_hz, order=2):
    nyq = 0.5 * Fs
    b, a = butter(order, cutoff_hz / nyq, btype='low')
    return filtfilt(b, a, x)

# =========================
# EXERCISE DETECTION
# =========================
def detect_exercise_bounds(signal, time, Fs, rms_window_sec=0.5, threshold_ratio=0.2):
    
    signal = lowpass(signal, Fs, 1, order=2)
    signal = highpass(signal, Fs, cutoff_hz=0.1, order=2)

    window_samples = int(rms_window_sec * Fs)
    squared = signal**2
    rms = np.sqrt(np.convolve(
        squared,
        np.ones(window_samples)/window_samples,
        mode='same'
    ))

    threshold = threshold_ratio * np.max(rms)
    active = rms > threshold

    active_indices = np.where(active)[0]

    if len(active_indices) == 0:
        return None, None

    start_idx = active_indices[0]
    end_idx   = active_indices[-1]

    return time[start_idx], time[end_idx]

# =========================
# REP SEGMENTATION
# =========================
def segment_rep(signal, time, Fs):

    signal = lowpass(signal, Fs, 1, order=2)
    signal = highpass(signal, Fs, cutoff_hz=0.1, order=2)
    
    peaks, _ = find_peaks(signal, prominence=0.05, distance=20)

    rep_times = []
    
    for i in range(len(peaks) - 1):
        rep_times.append((time[peaks[i]], time[peaks[i+1]]))
    
    return rep_times, len(rep_times)

# =========================
# METRICS
# =========================
def compute_snr_ratio(signal, Fs):
    
    movement = lowpass(signal, Fs, cutoff_hz=2, order=2)
    movement = highpass(movement, Fs, cutoff_hz=0.1, order=2)
    
    noise = highpass(signal, Fs, cutoff_hz=3, order=2)
    
    signal_rms = np.sqrt(np.mean(movement**2))
    noise_rms  = np.sqrt(np.mean(noise**2))
    
    if noise_rms == 0:
        return np.inf, np.inf
    
    snr_ratio = signal_rms / noise_rms
    snr_db = 20 * np.log10(snr_ratio)
    
    return snr_ratio, snr_db

def compute_tremor_energy_ratio(signal, Fs):
    
    signal = signal - np.mean(signal)
    N = len(signal)

    freqs = np.fft.rfftfreq(N, d=1/Fs)
    fft_vals = np.fft.rfft(signal)
    power = np.abs(fft_vals)**2

    movement_mask = (freqs >= 0.1) & (freqs <= 2)
    tremor_mask = (freqs >= 3) & (freqs <= 8)

    movement_power = np.sum(power[movement_mask])
    tremor_power = np.sum(power[tremor_mask])

    if movement_power == 0:
        return np.inf

    return tremor_power / movement_power

# =========================
# CLASSIFICATION
# =========================
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

# =========================
# MAIN PIPELINE
# =========================
def run_signal_processing(df):

    time = df['seconds_elapsed'].values
    Fs = 1 / np.mean(np.diff(time))

    sig = df['gravityX'].values

    start_time, end_time = detect_exercise_bounds(sig, time, Fs)

    if start_time is not None:
        df = df[(df['seconds_elapsed'] >= start_time) &
                (df['seconds_elapsed'] <= end_time)]

    time = df['seconds_elapsed'].values
    sig = df['gravityX'].values

    rep_times, n_reps = segment_rep(sig, time, Fs)

    rot_x = df['rotationRateX'].values
    rot_y = df['rotationRateY'].values
    rot_z = df['rotationRateZ'].values

    rot_mag = np.sqrt(rot_x**2 + rot_y**2 + rot_z**2)

    signal = lowpass(rot_mag, Fs, 10, order=2)
    signal = highpass(signal, Fs, cutoff_hz=0.1, order=2)

    snr_ratio, snr_db = compute_snr_ratio(signal, Fs)
    tremor_ratio = compute_tremor_energy_ratio(signal, Fs)

    log_tremor_ratio = np.log10(tremor_ratio + 1)

    movement_classification, tremor_level = classify_movement(
        snr_db, log_tremor_ratio
    )

    return {
        "num_reps": int(n_reps),
        "snr_db": float(snr_db),
        "tremor_ratio": float(log_tremor_ratio),
        "classification": movement_classification,
        "tremor_level": tremor_level,
        "duration_sec": float(time[-1] - time[0])
    }

# =========================
# TEST BLOCK (SAFE)
# =========================
if __name__ == "__main__":
    file_path = r"C:\Users\ahasa\Downloads\001_BicepCurl_L_T.csv"
    df = pd.read_csv(file_path)

    results = run_signal_processing(df)
    print(results)