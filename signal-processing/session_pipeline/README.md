# HomeStretch local session pipeline

**Automatic GUI workflow:** see [AUTOMATIC_WORKFLOW.md](AUTOMATIC_WORKFLOW.md).
Stop now queues local processing and cloud upload when the GUI integration is enabled.

Record with the existing v0 GUI, stop and save the CSV plus matching JSON, then
run this pipeline. Firmware and raw recordings are unchanged; only the HomeStretch GUI has the integration. No Firebase
connection is needed for processing. All 15 exercises are available; see the automatic workflow for orientation-model limitations.

## Run

From the repository's `signal-processing` directory, using Python 3.11:

```sh
python -m pip install -r session_pipeline/requirements.txt
python -m session_pipeline /absolute/path/session.csv \
  --patient-id P001 --exercise bicep_curl --side right \
  --output session_pipeline/outputs/session-results.json
```

Use your actual participant code; `P001` is an example. Metadata defaults to the
same stem with `.json`; override with `--metadata`. The default acceleration Y
axis was chosen for the inspected right-wrist recording; use `--axis x|y|z`
when mounting differs. Automatic exercise/axis recognition is not implemented.
`--ppg-channel` defaults to `ppg_green`; there is no silent channel substitution.
`--rep-goal` and `--max-hr-bpm` are optional; no clinical defaults are assigned.
Existing output files are never overwritten: select a new filename to rerun.

## What is saved

- Session and exercise identity, side, UTC start/end times.
- Recording hashes, validity counts and independently checked completeness.
- `imu`: estimated peak-to-peak curl cycles, durations, activity/rest/unscorable
  time, available exploratory motion features, per-rep provenance.
- `hr`: preliminary pulse mean/peak, accepted time intervals, quality rejection
  reasons, valid-time coverage, optional time above a configured threshold.
- `guidance`: structured flags and `patient_state: Unknown`. A validated
  exercise classifier/patient-state model is not configured.
- `processing`: method versions, source hashes, exercise configuration and warnings.

Unavailable values are `null`, not zero. Counts of typical/atypical reps remain
null until a model is configured; accepted reps are currently all Unknown.
A zero accepted-rep count means no qualifying cycles were found, not proof the
participant performed no exercise. `recording.duration_sec` and `imu.duration`
are the sensor timestamp span, which can differ from host Start/Stop wall time.
The schema keeps your requested metric names; all durations are seconds.

## Firestore: separate and explicit

Preview without credentials or a network call:

```sh
python -m session_pipeline.upload session_pipeline/outputs/session-results.json \
  --project homestretch-pipeline
```

After confirming authorized access to the intended project, install optional
upload requirements and configure Google Application Default Credentials (ADC)
using your organization's normal development setup. Then add `--upload`:

```sh
python -m pip install -r session_pipeline/requirements-upload.txt
python -m session_pipeline.upload session_pipeline/outputs/session-results.json \
  --project homestretch-pipeline --upload
```

Upload creates `sessions/{session_id}`, verifies it by readback, and accepts
identical retries. It refuses to overwrite a conflicting existing session. The project must be explicitly supplied. Credentials are not stored
in this module, the result JSON, the phone app, or Git. The standalone command uploads only with `--upload`; the configured GUI can upload automatically.
Permission/service errors from Google are surfaced; preview does not test access.
Only summaries are uploaded here; raw files remain local. Document-size checks
reject large summaries; long time series should go in Cloud Storage separately.

The adapter adds existing frontend fields (`num_reps`, `duration_sec`,
`num_typical`, `num_atypical`, `classification`, `file_name`) and `uploaded_at`.
The frontend still needs to display nulls as unavailable, respect `guidance`
and quality flags, and filter by the authenticated patient. Including a
`patient_id` field is not a substitute for Firestore access rules. Filename-based
sorting in the current Progress screen should migrate to `started_at`.

## Organization

| File | Responsibility |
|---|---|
| `reader.py` | Decode saved v0 recordings and check integrity |
| `ppg_reference.py` | Existing v0 PPG routines, preserved as a reference |
| `ppg.py` | Time-weighted session summaries and quality accounting |
| `imu_reference.py` | Selected existing HomeStretch feature routines |
| `motion.py`, `exercises.json` | Experimental exercise segmentation/configuration |
| `pipeline.py` | Results schema and structured guidance flags |
| `upload.py` | Optional Firestore adapter |
| `METHODS.md` | Source provenance, decisions and limitations |
| `tests/` | Synthetic integrity and processing checks |
| `outputs/` | Ignored local results and diagnostic plots |

The old `process_session.py`, `scoring.py` and firmware remain untouched. The standalone Documents/VITALWAVE GUI is separate from the HomeStretch GUI.
To support another exercise, add and validate a configuration/segmentation
strategy rather than assuming the curl thresholds generalize. Python local/cloud
processing can be shared with VitalWave. On-phone live processing will require a
separate implementation and equivalence tests; the current filters are offline.

## Tests

```sh
python -m unittest discover -s session_pipeline/tests -p test_pipeline.py -v
```

Tests use synthetic recordings, not committed participant data. Passing tests
establishes software behavior, not clinical or exercise-classifier validity.

## Optional experimental rep classification (0.2.0)

The existing `mbientcode/isolation_forest.pkl` and `scaler.pkl` are supported.
The notebook `mbientcode/mbientimplenetation.ipynb` trains on Apple Watch gravityX
and later tunes a -0.19 decision threshold for Mbient. Transfer to v0 is unvalidated.
Enable only as a development comparison, not as verified correct/incorrect form.
The earlier descriptions of Unknown classification apply to the default run;
this opt-in mode fills experimental labels, counts, four features and anomaly
scores per rep. Patient state remains Unknown and an experimental flag is added.
The standard SNR/tremor/smoothness summaries remain conservative; interpolated
classifier features are separately identified in each rep's provenance.

```sh
python -m pip install -r session_pipeline/requirements-classifier.txt
python -m session_pipeline /absolute/path/session.csv \
  --patient-id P001 --side right \
  --experimental-model ../mbientcode/isolation_forest.pkl \
  --experimental-scaler ../mbientcode/scaler.pkl \
  --output session_pipeline/outputs/session-classified.json
```

Only load trusted local model files: pickle/joblib loading can execute code.
The observed saved artifacts load without version warnings under scikit-learn
1.8.0; other estimator versions are rejected when sklearn reports a mismatch.
Feature names/order and estimator types are checked. Explicit paths prevent
silently selecting a different exercise model. Both paths are required.
For a model trained for another exercise, a new adapter/feature contract is needed.

With classifier dependencies installed, run all tests:

```sh
python -m unittest discover -s session_pipeline/tests -v
```

## PPG/motion diagnostics

With matplotlib installed, this optional report compares raw/filtered PPG with
motion during curls (14–22 s) and afterward (50–58 s), plus 8-second windows every
one second to inspect window sensitivity. These fixed plot ranges are specific
to the supplied development session. No session HR values are overwritten.

```sh
python -m session_pipeline.diagnose_ppg /absolute/path/session.csv \
  --output-dir session_pipeline/outputs/ppg-diagnostics
```

Motion harmonic overlap is only a diagnostic hint. This is not a motion-artifact
cancellation algorithm. A synchronized reference pulse measurement and a usable
resting optical signal are needed to evaluate the next motion-aware estimator.
