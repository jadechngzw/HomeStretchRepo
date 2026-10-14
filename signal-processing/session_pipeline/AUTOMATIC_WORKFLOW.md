# Automatic watch → local results → Firestore

The updated v0 GUI retains the existing BLE/Start/Stop behavior. When HomeStretch
is enabled, it captures participant/exercise settings at Start, closes the raw CSV
and metadata after Stop, and queues processing followed by upload. Save as is
optional; the pipeline uses the closed recovery recording directly.

## On this Mac

Open `HomeStretchRepo/hardware/vitalwave_v0/Launch.command` (restart the GUI if already open).
There is now a **HomeStretch — automatic session results** panel.

1. Enter a patient or development ID. For your own test recordings, use a
   development code; keep Data use = development.
2. Choose right/left wrist and the analysis axis (Y for the inspected recording).
   All 15 exercise models are listed. Bicep curl has experimental raw-acceleration segmentation/scoring. The other 14 now use experimental fused pitch/roll/relative-yaw, then their own segmentation, 17 features, scaler and model. Confirm the placement shown after selecting an exercise; keep still for the first two seconds before moving.
3. Enable Accelerometer + Gyroscope, IMU 50 Hz. For pulse analysis enable PPG,
   Green, 50 Hz, and select `ppg_green` in the HomeStretch panel.
4. Leave Enable pipeline and Upload to homestretch-pipeline checked. The optional
   classifier is explicitly labelled experimental and can be unchecked.
5. Connect, Start, exercise, Stop. No terminal commands or separate Save action
   are needed. The HomeStretch panel reports pending or uploaded-and-verified.

Raw files remain in `<save folder>/.recovery/`. Results are saved to
`<save folder>/processed/<recording name>/results.json`. Invalid/missing data,
unavailable pulse estimates and experimental labels are included in cloud results.
A successful upload does not mean the physiological measurements are validated.

## Failure and retry behavior

Jobs are durable JSON files in the configured recordings folder's `homestretch-jobs/` subfolder.
Results are saved before any network request. Internet/authentication/service
failures leave a pending job and visible error. The open GUI retries every 30
seconds; **Retry pending uploads** wakes it immediately. Closing the GUI stops
new retry passes; reopening it resumes pending jobs. An in-flight worker can
finish its current attempt after close. Raw files/results are not deleted.

Each job locks while processing. Upload uses create-only Firestore writes and a
content hash. Identical retries recognize the existing document and read it back
without creating a duplicate; conflicting data at the same ID is not overwritten.
This also handles a connection failing after the cloud accepted the write.

Simulated (`--demo`) recordings are always local-only, even with Upload checked.
The demo job queue is separate. Enabling experimental classification never
turns the patient-state field into a clinical Good/Moderate assessment.

## Frontend

Documents are written to `sessions/{session_id}`. Raw CSVs are not uploaded by
this workflow. The adapter includes current frontend summary fields plus nested
metrics, repetitions, flags and provenance. `started_at`, `ended_at`, and
`uploaded_at` are native Firestore timestamps in the cloud (ISO strings locally).
Sort by timestamps, not filename patterns. Display null as unavailable and show
experimental/incomplete status. Filter sessions by authorized patient identity;
patient IDs alone do not implement access control. Frontend access rules and
patient/clinician messaging are separate from this collector/upload change.

## Reproduce setup on another checkout

Use Python 3.11, with the updated GUI bridge files and this package in the repo:

```sh
cd signal-processing
python3.11 -m venv session_pipeline/.venv
session_pipeline/.venv/bin/python -m pip install \
  -r session_pipeline/requirements-classifier.txt \
  -r session_pipeline/requirements-upload.txt
session_pipeline/.venv/bin/python -m session_pipeline.configure_gui \
  --gui-root ../hardware/vitalwave_v0 --project homestretch-pipeline
gcloud auth application-default login
```

Run the GUI setup separately if its own environment does not yet exist. The GUI
and processing run in separate Python environments so new ML/cloud dependencies
do not affect BLE or the plotting loop. Generated `homestretch_integration.json`
contains local paths/project ID only, is Git-ignored, and never contains credentials.

## Validation performed

- Real supplied recording processed, uploaded, and read back from Firestore.
- Synthetic tests for local persistence, offline retry, no duplicate job execution,
  processing failure retention and demo upload suppression.
- Existing recorder tests for session/Stop/recording behavior.
- GUI integration test: simulated BLE Start/Stop → closed CSV + metadata → local
  results through the background worker, with demo upload suppressed.

No firmware flash or new physical-watch acquisition is performed by these checks.
PPG during motion remains an unresolved measurement task, not fixed by upload.

## Project separation and model inputs

Launch only `HomeStretchRepo/hardware/vitalwave_v0/Launch.command` for HomeStretch.
Its default recordings folder on this Mac is `/Users/jadechng/Desktop/HomeStretch/recordings`.
The Documents/ChatGPT/VITALWAVE GUI is restored to the standalone recorder with
no HomeStretch bridge or cloud configuration. Existing recordings are preserved.

`model_registry.json` associates all 15 choices with their actual artifacts.
Fourteen models require 17 orientation features in degrees, using ml/predict.py
and ml/rehab_pipeline.py. Acceleration g and gyroscope degrees/s are not angles.
The six-axis adapter estimates orientation from actual acceleration and angular velocity. It does not use the curl segmenter for these 14 exercises. Absolute yaw and anatomical-axis equivalence are not established.
The bicep model in ml/models is byte-identical to the existing Mbient four-feature
model and uses the original Mbient scaler. Its alternate unpaired model is not used.

Shared compute_snr_db and compute_tremor_energy_ratio formulas remain unchanged;
they are summarized over uninterrupted accepted curl repetitions. Generic active/rest
time remains experimental. Other exercises use their own 17 orientation features per accepted rep; acceleration SNR/tremor/smoothness remain null rather than being replaced by different formulas.

## Orientation models (0.4.0)

Install the separately version-matched scoring environment once:

```sh
cd HomeStretchRepo
python3.14 -m venv ml/.venv
ml/.venv/bin/python -m pip install -r ml/requirements.txt
```

The pipeline calls that environment locally for the REHAB models; the original
four-feature bicep model stays in the Python 3.11/scikit-learn 1.8 environment.
Model hashes and training/runtime scikit-learn versions are checked before scoring.

For the 14 orientation exercises, `orientation.csv` is saved beside `results.json`.
Columns are time, estimated pitch, relative yaw, roll, block, interpolation and
singularity flags. These are derived angles, not raw sensor measurements or joint angles.
Raw CSVs retain the measured acceleration and angular velocity. Only summaries,
rep features and provenance go to Firestore; orientation time series stay local.

The filter initializes tilt from gravity and yaw at zero. If the first two seconds
are stationary, it estimates gyro bias. It integrates body angular velocity using
quaternions and applies gravity feedback when acceleration magnitude is 0.85–1.15 g.
At most 60 ms between valid readings may be bridged and flagged. Longer gaps reset
orientation. No rep crosses a reset, and more than 10% interpolation rejects a rep.
Euler singularities, discontinuities, incomplete edge cycles, training duration
limits and return-to-start checks also reject candidates. Rejected candidates are
retained with reasons and are not automatically called atypical.

Yaw has no absolute heading correction, sensor axes do not establish anatomical
axes, and forearm/lower-leg training placements differ from a wrist. Wrist is an
explicit exploratory transfer for upper-limb models. Lower-limb models require
lower_leg placement; do not label wrist data as lower-leg data. A stationary start
is recommended for bias estimation, but missing it is reported rather than hidden.
The software route works; accuracy for all 15 real exercises remains unvalidated.

Validation: known static/dynamic rotations, bias, gaps; all 14 saved orientation
models scored synthetic raw-IMU repetitions; GUI demo Stop-to-results passed.
The supplied still/curl PPG comparison is saved under the recording folder's
`analysis/still-vs-curls-20261003/`. It was not uploaded as a clinical session.

## PPG coverage update (0.4.1)

The same pulse estimator now evaluates overlapping 8-second windows every second.
Accepted central intervals count only once, using median BPM where windows overlap.
Coverage still uses full session duration, while evaluated coverage and accepted
fraction of evaluated time are separate fields. Thresholds are unchanged. The
Elgendi comparison is available in the local analysis folder and is not enabled
as the production detector. Existing uploaded results are unchanged.
