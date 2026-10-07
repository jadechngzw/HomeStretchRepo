"""Read v0 CSV v2 / BLE protocol v3 without modifying or filling raw samples."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def load_recording(csv_path, metadata_path=None):
    path = Path(csv_path)
    meta_path = Path(metadata_path) if metadata_path else path.with_suffix('.json')
    meta = json.loads(meta_path.read_text())
    if meta.get('format_version') != 2 or meta.get('protocol_version') != 3:
        raise ValueError('Expected v0 CSV format 2 with protocol version 3 metadata.')
    if not meta.get('ended_utc'):
        raise ValueError('Stop the recording before processing it.')
    streams = {}
    last_ms, elapsed = {}, {}
    sequence_gaps, invalid, count = 0, 0, 0
    last_seq = None
    anchor = None
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'sensor', 'session_id', 'watch_ms', 'sequence', 'valid', 'x', 'y', 'z'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV is missing required v0 columns.')
        for row in reader:
            if int(row['session_id']) != int(meta['session_id']):
                raise ValueError('CSV and metadata session IDs do not match.')
            ms, seq, name = int(row['watch_ms']), int(row['sequence']), row['sensor']
            if not 0 <= ms < 2**32 or not 0 <= seq < 2**16:
                raise ValueError('Timestamp or sequence is outside the protocol range.')
            if last_seq is not None:
                step = (seq-last_seq) % 65536
                if step == 0 or step >= 32768:
                    raise ValueError('Duplicate or out-of-order sample sequence.')
                sequence_gaps += step-1
            last_seq = seq
            if anchor is None:
                anchor = ms
            delta = (ms-last_ms[name]) % 2**32 if name in last_ms else (ms-anchor) % 2**32
            if delta >= 2**31 or (name in last_ms and delta == 0):
                raise ValueError(f'Invalid or out-of-order timestamps for {name}.')
            elapsed[name] = elapsed.get(name, 0) + delta
            last_ms[name] = ms
            if row['valid'] not in ('0', '1'):
                raise ValueError('Invalid validity flag.')
            values = [float(row[c]) if row[c] else float('nan') for c in ('x','y','z')]
            n_axes = 3 if name in ('acceleration','gyroscope') else 1
            valid = row['valid'] == '1' and all(np.isfinite(values[:n_axes]))
            streams.setdefault(name, []).append([elapsed[name]/1000, *values, valid])
            invalid += not valid
            count += 1
    if not count:
        raise ValueError('The recording is empty.')
    streams = {name: np.asarray(rows, float) for name, rows in streams.items()}
    duration = max(a[-1,0] for a in streams.values())
    if duration <= 0:
        raise ValueError('Recording must span a positive duration.')
    status = meta.get('final_status') or {}
    complete = (meta.get('complete') is True and invalid == 0 and sequence_gaps == 0
                and meta.get('received') == count and status.get('generated') == count
                and status.get('dropped') == 0 and status.get('state') == 0
                and status.get('reason') == 0 and status.get('session') == meta['session_id'])
    return {'streams': streams, 'metadata': meta, 'duration': duration,
            'complete': complete, 'samples': count, 'invalid_samples': invalid,
            'sequence_gaps': sequence_gaps, 'csv_path': str(path.resolve()),
            'metadata_path': str(meta_path.resolve()),
            'csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'metadata_sha256': hashlib.sha256(meta_path.read_bytes()).hexdigest()}
