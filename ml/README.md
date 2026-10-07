# REHAB Exercise Anomaly Baselines

Fourteen exercise-specific Isolation Forests, with reproducible preprocessing,
17 features, saved scalers and training-only 95th-percentile completion limits.
Models describe similarity to the retained REHAB recordings. They do not establish
clinical correctness or safety. Read [METHODOLOGY.md](METHODOLOGY.md) before reporting results.

## Run

From the repository's `ml` directory, using Python 3.14 (the training environment):

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest -v test_pipeline
python train_models.py --data-root /path/to/REHAB --output models_new_run
```

An existing nonempty output directory is refused to preserve prior results.
The raw dataset stays outside this repository. No patient-level data is copied here.

## Files

- `rehab_pipeline.py`: clean, segment, normalize, extract features.
- `train_models.py`: split, calibrate, fit, evaluate, export and plot.
- `predict.py`: matching offline inference on source-format recordings.
- `models/TRAINING_RESULTS.md`: counts and thresholds for every exercise.
- `models/training_summary.json`: machine-readable results.
- `REVIEW_NOTES.md`: visual review findings and exercises needing extra scrutiny.
- `CALIBRATION_PLAN.md`: target-watch calibration, collection, adaptation and validation plan.
- `verify_models.py`: audit exported models against source data.
- `plot_overview.py`: regenerate the all-exercise segmentation review sheet.
- Each exercise folder contains its named model `.pkl`, `scaler.pkl`,
  `feature_config.json`, `metadata.json`, `segment_audit.json` and two plots.

```python
from pathlib import Path
import numpy as np
from predict import score_recording

data = np.load(Path('/path/to/REHAB/Rehab_exercise/d01_raw_data/000_1.npy'))
results = score_recording(data[0], 'models/bobath_handshake')
```

Load only trusted pickle files. The pickle exports require compatible Python/sklearn;
they do not run directly in a native phone application. The feature configuration
records scaling constants and signal conventions for a subsequent mobile port.
No phone latency, battery use or placement-transfer performance has been measured.
