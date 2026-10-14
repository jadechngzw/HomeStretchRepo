# Processing methods and reuse decisions — 0.1.0

## Retained and adapted

| Component | Source | Decision |
|---|---|---|
| CSV fields, sensor names, units, validity | `hardware/vitalwave_v0/desktop/recording/session.py`, protocol v3 | Read scaled x/y/z; no second scaling. Keep raw file unchanged. |
| PPG `filtered`, `filtered_segments`, `estimate` | `hardware/vitalwave_v0/desktop/processing/ppg.py` | Copied as named reference functions, unchanged. NumPy/SciPy only. |
| IMU high/low-pass, SNR, tremor ratio | `signal-processing/imu_metrics.py` | Copied selected functions unchanged, avoiding unrelated pandas/joblib/model imports. |
| Smoothness heuristic | `signal-processing/scoring.py` | Preserve `1/(1+tremor_ratio)`; not an independent movement-quality measure. |
| Curl segmentation concept | Existing HomeStretch `segment_reps` | Retain peak-to-peak cycles; use low-pass acceleration in g, explicit exercise thresholds, gap limits and per-rep provenance. |
| Guidance | Existing HomeStretch scoring/flags | Keep structured flags, remove implicit clinical thresholds and reassuring patient-state guesses. |

Selected functions are snapshots, not a second independently maintained algorithm
suite. Source hashes are recorded in each result. When contributing back to
VitalWave, designate one authoritative shared package and replace snapshots with
a versioned dependency. Preserve original attribution/history when transferring.

## Input integrity

CSV format 2 and protocol 3 required; the recording must be stopped. Session IDs
must match metadata; duplicate/backward sequence numbers and per-sensor timestamps
are rejected. Unsigned clock and sequence rollover are supported. Missing samples
are counted from the shared sequence. Overall completeness requires both the
recorder's declaration and matching valid samples/final firmware counts. The
pipeline never upgrades an incomplete recording to complete.

Source CSV and metadata hashes are saved. Firmware version is null if absent in
metadata; protocol version is not misrepresented as the flashed firmware version.

## Bicep curl configuration

Right-wrist acceleration Y was selected by inspecting this session. This is not
an automatically learned or validated universal axis. Second-order offline
Butterworth low-pass at 1 Hz, prominence 0.6 g, positive peak-to-next-positive-peak
cycles lasting 0.8–6 seconds. The original whole-session normalization and 0.1 Hz
high-pass were removed to avoid thresholding in recording-dependent units and
boundary drift. Incomplete first/last cycles are not counted. Repositioning can
still resemble exercise; results are candidates requiring validation.

Analysis-only resampling to the median accelerometer cadence is used. Adjacent
valid observations more than 60 ms apart split the signal; no bridging of longer
gaps. Short gaps are linearly interpolated only in this copy. Reject candidate
cycles with estimated missing/invalid fraction above 10%; save the fraction for
every retained repetition. Original invalid readings remain in source files and
quality counts. These are development choices, not validated acceptance limits.

Time accounting uses matched accelerometer/gyro timestamps and adjacent valid
endpoints separated by at most 1.6 nominal periods. A bin is rest only when gyro
magnitude is below 10 degrees/s and acceleration-vector change below 0.5 g/s.
Other valid bins are active; remaining sensor-span time is unscorable. These are
exploratory whole-session motion/rest measures, not summed repetition time or a
clinical assessment. Invalid intervals are not silently treated as rest.

SNR uses the existing 0.1–2 Hz movement vs >3 Hz residual RMS ratio. Tremor score
uses existing 3–8 Hz to 0.1–2 Hz spectral energy ratio. Compute only for accepted
cycles without invalid/missing readings, then average the available cycle
features. Sampling jitter is resampled; features remain exploratory. Do not
estimate high-frequency movement features from short-gap repaired repetitions.
This recording therefore may have counts/timing but no SNR/tremor/smoothness.

No existing Isolation Forest is loaded automatically: suitability for the new
watch, selected axis and exercise has not been established. Unknown is distinct
from Typical or Atypical. Patient state remains Unknown.

## PPG

Retain v0's 0.5–4 Hz filter, clipping/gap checks, and agreement between
periodicity, spectral and peak-timing estimates. These heuristic checks do not
establish exercise accuracy and can accept rhythmic motion artifacts.

Unlike the overlapping GUI report windows, session summary uses disjoint 8 s
windows starting 5 s after the selected PPG stream begins. The estimator ignores
one second at each edge; coverage therefore credits only each central 6 s.
Mean HR is duration-weighted across those intervals; peak HR is the maximum
accepted window estimate, not an instantaneous beat-level maximum. Time above a
configured threshold credits accepted central intervals only. Missing/rejected
periods never become below-threshold time. Coverage denominator is the entire
sensor recording span, including warmup, gaps and unanalysed tail. It is thus
conservative and cannot reach 100% with this method. Interval timestamps explain
exactly what was credited.

## Deliberately not adopted

- HomeStretch's separate example PPG .npy file and hardcoded 64 Hz assumption.
- Old VitalWave cloud `ppg.py` as a wholesale replacement: needs channel/rate and
  aggregation review before a controlled comparison against the v0 reference.
- Old VitalWave SpO2 calculation: uses optical amplitude as a resampling rate,
  fixed calibration and output truncation. SpO2 is outside the agreed metric scope.
- Existing model files, fixed heart-rate limits, and patient Good/Moderate/Concern
  labels without an established model/rule validation and missing-data policy.
- Cloud calls inside signal processing or raw participant data committed to Git.

## Current real-recording check

The supplied right-wrist session is a development recording with no remembered
manual rep count. Its 406 invalid IMU samples and failed PPG quality windows are
reported rather than hidden. Use a future labelled recording for accuracy checks.
The development participant ID in the generated example is a placeholder, not a
confirmed clinical identity. The development result was uploaded to HomeStretch
Firestore and read back successfully; an identical retry was also verified.


## 0.2.0 — explicit legacy classifier and PPG diagnostics

Source reviewed: `mbientcode/mbient_pipeline.py` and code cells 11–18 of
`mbientcode/mbientimplenetation.ipynb`. Saved model/scaler copies in `mbientcode`
and `mbientcode-cloud` have identical SHA-256 hashes. No model is retrained.

Retain feature order [duration, norm_amp, dom_freq, log_tremor], the saved
StandardScaler, IsolationForest.decision_function and `score > -0.19` rule.
Do not substitute `predict()` because its built-in cutoff is different. Extract
features from session-normalized, resampled acceleration over the configured
v0 rep intervals. Relative amplitude uses mean accepted-rep amplitude. Dominant
frequency retains the legacy FFT definition (including its DC bin). Log tremor
uses log10(1 + power_3_to_8Hz/power_0.1_to_2Hz).

This is an adaptation, not exact legacy-pipeline equivalence: the notebook uses
Apple Watch gravityX and positive-peak segmentation; mbient_pipeline.py uses
trimmed Mbient ay and trough segmentation. v0 supplies total acceleration and
our explicit curl boundaries. Linear short-gap interpolation can suppress the
high-frequency feature. Every output declares experimental_transfer and stores
model/scaler hashes, threshold, features, score, and interpolation fraction.
Reps with long gaps remain Unknown; majority summary is Unknown with any missing
labels or a tie. The command-line default remains classifier disabled; the GUI exposes an
explicit experimental-classifier checkbox, initially enabled. Patient state always
remains Unknown. No caretaker is notified by a flag.

The diagnostic PPG sweep uses all 8-second windows at a 1-second step after
warmup. Candidate values are diagnostic only and are not selected to replace
rejected summary estimates. Motion spectrum sums the three centered acceleration
axis spectra; nearby first-through-fourth harmonics are flagged with a 0.12 Hz
tolerance solely as an exploratory hint. Independent sensor-clock alignment,
contact quality, and reference-HR validation are still unresolved.


## 0.3.0 — automatic desktop workflow

Stop closes the recording before queuing local processing in an isolated Python
environment. Raw files and saved results survive upload failures. Durable jobs
retry while the GUI is open and resume after restart. Firestore writes are
create-only, recognize identical retries by a content hash, and verify readback.
Simulated recordings never upload. See AUTOMATIC_WORKFLOW.md for operation.


## 0.4.0 — exercise-specific orientation transfer

All 15 exercises are selectable. Bicep uses the byte-identical ml/models copy of
the original four-feature model with its Mbient scaler. The other 14 use a new
experimental six-axis quaternion gravity-feedback adapter, relative yaw, then
the existing ml/rehab_pipeline.py segmentation/normalization/17 features unchanged.
Each model retains its duration, completion, segmentation and anomaly thresholds.
No models are retrained. Version-matched scoring checks artifact hashes.
See AUTOMATIC_WORKFLOW.md for calibration, placement, gap/singularity handling,
validation and remaining frame/yaw limitations. Original IMU SNR/tremor formulas
remain unchanged and are not substituted for orientation-model features.


## 0.4.1 — overlap coverage and detector comparison

PPG quality thresholds remain unchanged. Eight-second windows now step by one
second; only central six-second intervals count. Coverage is the union of accepted
intervals divided by full session duration. Median BPM among overlapping windows
provides a non-overlapping timeline for mean, peak and time-above-threshold metrics.
Outputs separately report evaluated duration/coverage and accepted-of-evaluated
percentage. The detector comparison script uses NeuroKit Elgendi without replacing
the production estimator. See recordings/analysis/ppg-detector-comparison-20261003
for the supplied still/curl comparison and explicit limitations.
