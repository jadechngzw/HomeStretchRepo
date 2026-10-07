"""Selected existing HomeStretch functions; provenance in METHODS.md."""
import numpy as np
from scipy.signal import butter, filtfilt

def highpass(signal, sample_rate, cutoff_hz, order=2):
    nyquist = 0.5 * sample_rate
    b, a = butter(order, cutoff_hz / nyquist, btype="high")
    return filtfilt(b, a, signal)

def lowpass(signal, sample_rate, cutoff_hz, order=2):
    nyquist = 0.5 * sample_rate
    b, a = butter(order, cutoff_hz / nyquist, btype="low")
    return filtfilt(b, a, signal)

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
