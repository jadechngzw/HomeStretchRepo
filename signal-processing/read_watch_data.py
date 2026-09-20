import numpy as np
import pandas as pd
from ppg_metrics import analyze_ppg, extract_metrics, load_ppg_data

def load_watch_data(file_path, signal_column=None):
    data = pd.read_csv(file_path)

    # Apple Watch format
    if {"seconds_elapsed", "gravityX"}.issubset(data.columns):
        time_column = "seconds_elapsed"
        signal_column = signal_column or "gravityX"

    # Mbient format
    elif len(data.columns) == 6:
        data.columns = ["epoc_ms", "timestamp", "elapsed_s", "ax", "ay", "az"]
        time_column = "elapsed_s"
        signal_column = signal_column or "ay"

    else:
        raise ValueError(
            f"Unsupported CSV format. Found {len(data.columns)} columns:\n"
            f"{data.columns.tolist()}"
        )

    if signal_column not in data.columns:
        raise ValueError(
            f"Signal column '{signal_column}' not found. "
            f"Available columns: {data.columns.tolist()}"
        )

    time = data[time_column].to_numpy(dtype=float)
    signal = data[signal_column].to_numpy(dtype=float)
    sample_rate = 1 / np.median(np.diff(time))
    signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)

    return {"signal": signal, "time": time, "sample_rate": sample_rate}


def load_ppg_metrics(ppg_file):
    data = load_ppg_data(ppg_file)
    wd, m = analyze_ppg(data)
    return extract_metrics(wd, m)

