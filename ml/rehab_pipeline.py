"""Shared offline preprocessing and features for REHAB orientation recordings."""
from itertools import combinations

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks

CHANNELS = ("pitch", "yaw", "roll")
EXERCISES = {
    "000": "bobath_handshake",
    "001": "bobath_flexion_extension",
    "002": "bobath_forward_flexion_extension",
    "003": "bobath_anterior_posterior_rotation",
    "004": "elbow_flexion_wrist_compression",
    "005": "wrist_flexion_extension",
    "008": "shoulder_internal_external_rotation",
    "009": "breast_expansion",
    "010": "flexion_pressure_rotation_forward_backward",
    "011": "elbow_joint_flexion_touch",
    "012": "shoulder_touch_training",
    "013": "ankle_extension_knee_internal_external_rotation",
    "014": "knee_flexion_extension",
    "015": "hip_flexion_extension",
}
FEATURE_COLUMNS = ["duration_seconds", "completion_error"] + [
    f"{channel}_{feature}" for channel in CHANNELS
    for feature in ("rom", "velocity_mean", "peak_velocity", "smoothness")
] + [f"{a}_{b}_correlation" for a, b in combinations(CHANNELS, 2)]


def clean_recording(recording, smoothing_window=5):
    """Trim all-channel zero padding, unwrap angles, and smooth time axis."""
    recording = np.asarray(recording, dtype=np.float64)
    if recording.ndim != 2 or recording.shape[1] != 6:
        raise ValueError("Expected a (time, 6) exercise _1 array.")
    if not np.isfinite(recording).all():
        raise ValueError("Nonfinite recording; do not silently interpolate it.")
    nonpadding = np.flatnonzero(np.any(recording != 0, axis=1))
    if not len(nonpadding) or nonpadding[-1] < 19:
        raise ValueError("Empty or too-short recording.")
    length = int(nonpadding[-1] + 1)
    if np.any(np.abs(np.diff(recording[:length, :3], axis=0)) > 180):
        raise ValueError("Ambiguous >180-degree adjacent angle jump; requires source review.")
    # S1 (forearm) for upper limb; S3 (lower leg) for lower limb.
    angles = np.rad2deg(np.unwrap(np.deg2rad(recording[:length, :3]), axis=0))
    return uniform_filter1d(angles, size=smoothing_window, axis=0, mode="nearest")


def estimate_period(signal, fs):
    """Exploratory autocorrelation period, restricted to 0.6-8 seconds."""
    centered = signal - np.mean(signal)
    ac = np.correlate(centered, centered, mode="full")[len(signal) - 1:]
    if ac[0] < 1e-8:
        return None
    ac /= ac[0]
    low, high = max(2, int(0.6 * fs)), min(len(signal) // 2, int(8 * fs))
    peaks, _ = find_peaks(ac)
    peaks = peaks[(peaks >= low) & (peaks <= high)]
    if not len(peaks):
        return None
    lag = int(peaks[np.argmax(ac[peaks])])
    if ac[lag] < 0.15:
        return None
    return lag / fs, float(ac[lag])


def fit_segmentation(recordings, fs):
    """Select channel and fixed exercise settings using training records only."""
    candidates = []
    for channel in range(3):
        amplitudes, periods, strengths = [], [], []
        for session in recordings:
            signal = session[:, channel]
            amplitude = float(np.ptp(np.percentile(signal, [5, 95])))
            estimate = estimate_period(signal, fs)
            if amplitude >= 5 and estimate is not None:
                amplitudes.append(amplitude)
                periods.append(estimate[0])
                strengths.append(estimate[1])
        if len(periods) >= 5:
            candidates.append({
                "channel_index": channel,
                "channel_name": CHANNELS[channel],
                "period_seconds": float(np.median(periods)),
                "prominence_degrees": max(3.0, float(np.median(amplitudes)) * 0.25),
                "periodic_training_records": len(periods),
                "selection_score": float(np.median(strengths) * np.median(amplitudes)
                                         * len(periods) / len(recordings)),
            })
    if not candidates:
        raise ValueError("No reliably moving periodic channel in training data.")
    selected = dict(max(candidates, key=lambda x: x["selection_score"]))
    selected["minimum_distance_samples"] = max(2, int(0.55 * selected["period_seconds"] * fs))
    selected["channel_candidates"] = candidates
    selected["boundary_type"] = "valley"
    return selected


def segment_repetitions(session, settings):
    """Keep all segments with explicit edge flags and inclusive sample bounds."""
    boundaries, _ = find_peaks(
        -session[:, settings["channel_index"]],
        distance=settings["minimum_distance_samples"],
        prominence=settings["prominence_degrees"],
    )
    cuts = np.unique(np.r_[0, boundaries, len(session) - 1])
    for index, (start, end) in enumerate(zip(cuts[:-1], cuts[1:])):
        yield {
            "repetition_index": index, "start_sample": int(start),
            "end_sample": int(end), "is_edge": bool(start == 0 or end == len(session) - 1),
            "detected_boundaries": len(boundaries),
        }, session[start:end + 1].copy()


def normalize_repetition(repetition):
    return repetition - np.mean(repetition[:5], axis=0, keepdims=True)


def calculate_completion_error(repetition):
    return float(np.sqrt(np.mean(np.mean(repetition[-5:, [0, 2]], axis=0) ** 2)))


def calculate_features(repetition, sampling_rate_hz=50.0):
    """17 ordered features from a smoothed, start-normalized repetition."""
    repetition = np.asarray(repetition, dtype=np.float64)
    if repetition.ndim != 2 or repetition.shape[1] != 3 or len(repetition) < 5:
        raise ValueError("Expected at least five time points and three channels.")
    if not np.isfinite(repetition).all() or sampling_rate_hz <= 0:
        raise ValueError("Finite angles and positive sampling rate required.")
    features = {"duration_seconds": (len(repetition) - 1) / sampling_rate_hz,
                "completion_error": calculate_completion_error(repetition)}
    for index, channel in enumerate(CHANNELS):
        angle = repetition[:, index]
        velocity = np.gradient(angle, 1 / sampling_rate_hz)
        acceleration = np.gradient(velocity, 1 / sampling_rate_hz)
        jerk = np.gradient(acceleration, 1 / sampling_rate_hz)
        features.update({
            f"{channel}_rom": float(np.ptp(angle)),
            f"{channel}_velocity_mean": float(np.mean(np.abs(velocity))),
            f"{channel}_peak_velocity": float(np.max(np.abs(velocity))),
            f"{channel}_smoothness": float(-np.log1p(np.sqrt(np.mean(jerk ** 2)))),
        })
    for a, b in combinations(range(3), 2):
        correlation = 0.0 if min(np.std(repetition[:, a]), np.std(repetition[:, b])) < 1e-8 else float(
            np.clip(np.corrcoef(repetition[:, a], repetition[:, b])[0, 1], -1, 1))
        features[f"{CHANNELS[a]}_{CHANNELS[b]}_correlation"] = correlation
    return features
