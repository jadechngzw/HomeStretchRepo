# Methodology: Exploratory REHAB Anomaly Detection

## Objective and source

Fit one reference-distribution model for each requested exercise using
`Rehab_exercise/d01_raw_data/<movementID>_1.npy`. Each source file contains
recordings by time by six orientation channels, not six raw acceleration/gyro axes.
Exercise IDs 000-005 and 008-015 are included; finger-to-finger and ball gripping
(006, 007) are excluded. The article reports 120 participants overall and 60 in
the training-data cohort. Unique participants per exercise cannot be counted from
these files because no participant mapping is available. Source rows are called
recordings here, not patients or verified sessions.

Source: [Lv et al., Scientific Data (2026)](https://doi.org/10.1038/s41597-026-07802-2),
especially the exercise data records, preprocessing description and sensor figure.
Author code: [REHAB](https://github.com/zzzzz-123/REHAB).

## Placement and representation

Columns 0,1,2 are pitch,yaw,roll for S1 (upper limb) or S3 (lower limb).
Columns 3,4,5 describe a different sensor and are excluded from model features.
S1 is a forearm sensor about 10 cm above the wrist crease; S3 is a lower-leg
sensor approximately 10-20 cm below the patella. A wrist watch or ankle watch
does not exactly reproduce those placements. In particular an ankle/foot sensor
may move differently from S3. These are provisional forearm/lower-leg models,
requiring new watch recordings at the intended sites before deployment claims.
Forearm orientation alone cannot reliably measure isolated wrist joint motion,
grip/compression force, shoulder joint angles, or distinguish all compensations.

Source orientation must not be confused with raw gyro rate. A watch needs matched
sensor fusion, axis conventions, degrees, placement and calibration. Yaw transfer
from the source nine-axis system to a six-axis watch remains unvalidated.

## Preprocessing and split

1. Split original rows approximately 80/20 with seed 42 before fitting anything.
   Exact duplicate row hashes share a split. All segments of a row remain together.
   This is a recording-level holdout, not a patient-independent split; multiple
   rows may belong to one patient. Near duplicates are not guaranteed separated.
2. Reject nonfinite/empty/very short rows; record reasons. Remove trailing rows
   that are zero across all six source channels before selecting S1/S3.
3. Reject rows with any adjacent selected-channel jump over 180 degrees: source
   wraps and corrupt discontinuities cannot reliably be distinguished here.
   This conservative policy can exclude legitimate wraps; counts are recorded.
   Unwrap each retained angle in degrees across time at 360-degree discontinuities.
   Apply a centered five-point moving average with nearest-edge extension.
4. Use nominal 50 Hz from the acquisition description. No per-row timestamps are
   supplied here. The paper describes 880-point truncation/zero-padding; observed
   cycle counts differ across recordings. Seconds and derivatives are conditional
   on the nominal timebase and must be verified with authors or original timestamps.

## Exercise-specific segmentation

For each channel and each training recording, estimate the strongest local
autocorrelation maximum between 0.6 and 8 nominal seconds (at most half a row).
Require normalized autocorrelation >=0.15 and 5th-to-95th-percentile amplitude >=5
degrees. Rank channels by median autocorrelation times median amplitude times
fraction of valid training rows. Choose the highest-ranked channel once per exercise.
Use its median period to set minimum valley spacing at 0.55 times that period.
Valley prominence is max(3 degrees, 0.25 times median robust amplitude).
These are exploratory engineering heuristics, not optimized clinical thresholds.
Selection inputs, alternative channel scores, and settings are saved.

Consecutive valleys define candidate cycles. Recording start/end are also cuts
so edge attempts remain in the audit, but edge segments are excluded from fitting
and reported evaluation because completeness is uncertain. This is deliberately
more conservative than the initial notebook's acceptance of some edge attempts.
No detections therefore produce only an excluded edge segment, not a presumed rep.
Figures show algorithmic proposals, not ground-truth repetition annotations.

## Completion calibration and quality gates

Normalize each candidate by subtracting the mean of its first five samples per
channel. Do not divide its angles by their standard deviation; amplitude is retained.
Completion error is sqrt((mean_final_pitch^2 + mean_final_roll^2)/2), using the
last five normalized samples. It measures return toward the starting orientation,
not clinical correctness, and does not check return in yaw.

Derive duration limits at the 1st and 99th percentiles of training interior
candidates. Compute maximum completion error as the exact **95th percentile**
of training interior candidates within those duration limits, using NumPy's linear
quantile interpolation. No rounding to 30 degrees and no test-set calibration.
Apply those same fixed gates to training and held-out candidates. All excluded
candidates and overlapping rejection reasons are retained in the audit.
Thresholds are descriptive filters; high completion values can reflect movement,
segmentation, sensor drift or missing data, not necessarily recording truncation.
These gates narrow the reference population, bias retained samples toward regular
cycles, and can suppress meaningful impairment. Quality failures are unscorable,
not automatically atypical or typical. Held-out rates are conditional on passing.

## Seventeen features

| Features | Definition | Units |
|---|---|---|
| duration_seconds | (sample count - 1) / nominal frequency | s |
| completion_error | RMS of final mean normalized pitch and roll | degrees |
| pitch/yaw/roll_rom | maximum minus minimum angle | degrees |
| pitch/yaw/roll_velocity_mean | mean absolute first derivative | degrees/s |
| pitch/yaw/roll_peak_velocity | maximum absolute first derivative | degrees/s |
| pitch/yaw/roll_smoothness | -log1p(RMS(third angle derivative)) | heuristic index |
| pitch_yaw/pitch_roll/yaw_roll_correlation | Pearson correlation; 0 for flat channels | unitless |

Derivatives use successive numpy.gradient calls with dt=1/fs. The smoothness
index is an unvalidated jerk proxy, dependent on amplitude, duration, sampling,
filtering and boundary derivatives; it is not a standardized clinical smoothness
metric. Euler angle rates are not identical to body-frame gyroscope rates.
Feature order is explicit in feature_config.json. No frequency or template features
are included. No resampling to a fixed repetition length is needed.

## Model and evaluation

Fit StandardScaler only on accepted training candidates. Fit 200-tree
IsolationForest, max_samples=256 (or available rows if fewer), contamination=0.05,
seed=42, one worker. Scaling is preserved for compatibility with the notebook;
positive affine scaling is generally unnecessary for Isolation Forest itself.
The model is retained as fitted on the training split; it is not refitted on test rows.

Anomaly score = -decision_function = offset_ - score_samples. Positive scores
are reference outliers; zero/negative scores are reference-like. Five percent
contamination specifies a training score quantile, not an observed incorrect rate.
Scores are not probabilities or calibrated between exercises. Saved reports show
training and held-out outlier rates, not accuracy, sensitivity, or specificity.
Those metrics cannot be measured without independent typical/atypical labels.

Every folder saves exact split indices, counts, parameters, versions, source and
artifact hashes, nominal timebase, quality settings, plots and an audit of all
candidate boundaries, feature values, exclusions and scores. Serialization is
verified by reloading model/scaler and reproducing held-out scores.

## Before phone deployment or stronger research claims

Confirm timebase, sensor axes and patient/session mapping. Manually annotate
representative recordings to measure cycle-boundary errors. Evaluate sensitivity
to segmentation and completion thresholds using training/validation data, leaving
an independent final test set untouched. Collect watch data at the exact intended
wrist and ankle locations, with clinician-reviewed typical and atypical examples,
and evaluate on unseen people. Recalibrate anomaly cutoffs using these labels.
The centered filter requires buffering/delay and online cycle detection must be
implemented and checked against this offline reference. Port trees and features
to the phone runtime and test numerical parity, model size, latency and power.
Pickle exports alone are not a mobile deployment format.

No source signals are redistributed. Confirm dataset/model redistribution terms
before a public release; the article license and dataset license are not assumed
interchangeable. No publication or git push is performed by this training script.
