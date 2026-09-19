import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import joblib
import pandas as pd

'''
FILE Contains helper functions: 
getnumreps()
getrepduration()
gettotalactivetime()
getresttime()
getsnr()
gettremorscore()
classifyrep()
classify_repetitions()
'''

def highpass(signal, sample_rate, cutoff_hz, order=2):
    nyquist = 0.5 * sample_rate
    b, a = butter(order, cutoff_hz / nyquist, btype="high")
    return filtfilt(b, a, signal)


def lowpass(signal, sample_rate, cutoff_hz, order=2):
    nyquist = 0.5 * sample_rate
    b, a = butter(order, cutoff_hz / nyquist, btype="low")
    return filtfilt(b, a, signal)


def segment_reps(signal, time, sample_rate):
    """
    Detect repetitions and return each repetition as a dictionary.
    """

    filtered_signal = lowpass(signal, sample_rate, 1.0)
    filtered_signal = highpass(filtered_signal, sample_rate, 0.1)

    peaks, _ = find_peaks(
        filtered_signal,
        prominence=0.05,
        distance=int(sample_rate * 1.0),
    )

    repetitions = []

    for start_peak, end_peak in zip(peaks[:-1], peaks[1:]):
        start_time = time[start_peak]
        end_time = time[end_peak]

        mask = (time >= start_time) & (time <= end_time)

        repetitions.append(
            {
                "signal": signal[mask],
                "time": time[mask],
                "t_start": start_time,
                "t_end": end_time,
            }
        )

    return repetitions


def compute_snr_db(signal, sample_rate):
    """
    Signal-to-noise ratio in decibels.
    Higher values generally indicate cleaner movement.
    """

    movement = highpass(
        lowpass(signal, sample_rate, 2.0),
        sample_rate,
        0.1,
    )

    noise = highpass(signal, sample_rate, 3.0)

    signal_rms = np.sqrt(np.mean(movement**2))
    noise_rms = np.sqrt(np.mean(noise**2))

    if noise_rms == 0:
        return np.inf

    return 20 * np.log10(signal_rms / noise_rms)


def compute_tremor_energy_ratio(signal, sample_rate):
    """
    Compares tremor-frequency energy to movement-frequency energy.
    Higher values may indicate more tremor-like activity.
    """

    centered_signal = signal - np.mean(signal)

    frequencies = np.fft.rfftfreq(
        len(centered_signal),
        d=1 / sample_rate,
    )

    power = np.abs(np.fft.rfft(centered_signal)) ** 2

    movement_power = np.sum(
        power[(frequencies >= 0.1) & (frequencies <= 2.0)]
    )

    tremor_power = np.sum(
        power[(frequencies >= 3.0) & (frequencies <= 8.0)]
    )

    if movement_power == 0:
        return np.inf

    return tremor_power / movement_power


def extract_rep_features(rep_signal, rep_time, sample_rate, all_amplitudes):
    """
    Extract useful features from one repetition.
    """

    duration = rep_time[-1] - rep_time[0]

    amplitude = np.max(rep_signal) - np.min(rep_signal)
    average_amplitude = np.mean(all_amplitudes)

    normalized_amplitude = (
        amplitude / average_amplitude
        if average_amplitude > 0
        else 0
    )

    peak_index = np.argmax(rep_signal)

    rise_time = rep_time[peak_index] - rep_time[0]
    fall_time = rep_time[-1] - rep_time[peak_index]

    symmetry = (
        rise_time / fall_time
        if fall_time > 1e-6
        else rise_time / 1e-6
    )

    symmetry = np.clip(symmetry, 0, 10)

    zero_crossings = np.where(np.diff(np.sign(rep_signal)))[0]

    zero_crossing_rate = (
        len(zero_crossings) / duration
        if duration > 0
        else 0
    )

    frequencies = np.fft.rfftfreq(
        len(rep_signal),
        d=1 / sample_rate,
    )

    power = np.abs(np.fft.rfft(rep_signal)) ** 2
    dominant_frequency = (
        frequencies[np.argmax(power)]
        if len(power) > 0
        else 0
    )

    snr_db = compute_snr_db(rep_signal, sample_rate)

    tremor_ratio = compute_tremor_energy_ratio(
        rep_signal,
        sample_rate,
    )

    log_tremor = np.log10(tremor_ratio + 1)

    return {
        "duration": duration,
        "norm_amp": normalized_amplitude,
        "symmetry": symmetry,
        "zcr": zero_crossing_rate,
        "dom_freq": dominant_frequency,
        "snr_db": snr_db,
        "tremor_ratio": tremor_ratio,
        "log_tremor": log_tremor,
    }

def calculate_active_time(repetitions):
    """
    Total time spent performing repetitions.
    """

    return sum(
        rep["t_end"] - rep["t_start"]
        for rep in repetitions
    )


def calculate_rest_time(repetitions):
    """
    Time between repetitions.

    This only measures gaps between detected repetitions.
    It does not include rest before the first repetition
    or after the final repetition.
    """

    if len(repetitions) < 2:
        return 0.0

    rest_times = []

    for previous_rep, current_rep in zip(
        repetitions[:-1],
        repetitions[1:],
    ):
        rest_time = current_rep["t_start"] - previous_rep["t_end"]
        rest_times.append(max(rest_time, 0.0))

    return sum(rest_times)

def detect_rest_periods(signal, time, sample_rate,
                        threshold_ratio=0.15, min_rest_seconds=0.5):
    filtered = highpass(lowpass(signal, sample_rate, 2), sample_rate, 0.1)

    window = max(1, int(0.25 * sample_rate))
    rms = np.sqrt(np.convolve(
        filtered ** 2, np.ones(window) / window, mode="same"
    ))

    if np.max(rms) == 0:
        return []

    resting = rms < threshold_ratio * np.max(rms)
    changes = np.diff(np.pad(resting.astype(int), (1, 1)))
    starts, ends = np.where(changes == 1)[0], np.where(changes == -1)[0]

    return [
        {
            "start": round(float(time[start]), 2),
            "end": round(float(time[end - 1]), 2),
            "duration": round(float(time[end - 1] - time[start]), 2),
        }
        for start, end in zip(starts, ends)
        if time[end - 1] - time[start] >= min_rest_seconds
    ]

'''
MACHINE LEARNING MODEL FOR ATYPICAL REP CLASSIFICATION
'''
def classifyrep(
    rep_features,
    model_path="/Users/jadechng/Desktop/HomeStretch/HomeStretchRepo/mbientcode-cloud/isolation_forest.pkl",
    scaler_path="/Users/jadechng/Desktop/HomeStretch/HomeStretchRepo/mbientcode-cloud/scaler.pkl",
    threshold=-0.19,
):
    """
    Classify one repetition as Typical or Atypical.

    rep_features must be the dictionary returned by
    extract_rep_features().
    """

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    feature_columns = [
        "duration",
        "norm_amp",
        "dom_freq",
        "log_tremor",
    ]

    feature_values = pd.DataFrame(
        [[rep_features[column] for column in feature_columns]],
        columns=feature_columns,
    )

    feature_values = feature_values.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    if feature_values.isna().any().any():
        return "Unknown"

    scaled_features = scaler.transform(feature_values)

    anomaly_score = model.decision_function(
        scaled_features
    )[0]

    if anomaly_score > threshold:
        classification = "Typical"
    else:
        classification = "Atypical"

    return classification


def classify_repetitions(reps, sample_rate, model_path, scaler_path,
                         threshold=-0.19):
    if not reps:
        return pd.DataFrame()

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    amplitudes = [
        np.max(rep["signal"]) - np.min(rep["signal"])
        for rep in reps
    ]

    records = []

    for number, rep in enumerate(reps, start=1):
        features = extract_rep_features(
            rep["signal"], rep["time"], sample_rate, amplitudes
        )

        features["rep_number"] = number
        features["start_time"] = rep["t_start"]
        features["end_time"] = rep["t_end"]
        records.append(features)

    results = pd.DataFrame(records)
    feature_columns = ["duration", "norm_amp", "dom_freq", "log_tremor"]

    valid = results[feature_columns].replace(
        [np.inf, -np.inf], np.nan
    ).notna().all(axis=1)

    results["classification"] = "Unknown"

    if valid.any():
        scaled = scaler.transform(results.loc[valid, feature_columns])
        scores = model.decision_function(scaled)

        results.loc[valid, "classification"] = np.where(
            scores > threshold, "Typical", "Atypical"
        )

        results.loc[valid, "anomaly_score"] = scores

    return results