# Wearable Calibration and Domain-Adaptation Plan

## Purpose

This plan connects the exploratory REHAB orientation models to the intended
wearable. It separates three different activities:

1. **Device calibration** corrects sensor bias, scale, timing, and axis direction.
2. **Placement calibration** expresses movement relative to a repeatable wrist or
   shin starting pose.
3. **Model calibration** adapts feature distributions and the anomaly threshold
   using recordings from the target wearable.

The first two produce consistent signals. The third determines whether an
exercise repetition is reference-like or unusual. A model cannot be empirically
calibrated to a watch before watch recordings exist; the software contract,
protocol, replay tests, and acceptance criteria can be prepared in advance.

## Target placement

Use one wearable on the affected limb.

| Exercise group | Target placement | REHAB source sensor |
|---|---|---|
| Upper limb | Forearm near the wrist, about 10 cm above the dorsal wrist crease | S1 |
| Lower limb | Shin/lower leg, approximately 10-20 cm below the patella | S3 |

Record side (left/right), exact distance from the landmark, strap orientation,
watch face direction, and whether the device was removed and replaced. Use a
placement photograph or diagram in the study protocol, without patient-identifying
content. Mark the strap/device so staff can reproduce its orientation.

## Phase 0: prepare before hardware data exists

Freeze a wearable signal contract:

- timestamps in monotonic seconds or integer microseconds;
- accelerometer in m/s² or g, explicitly identified;
- gyroscope in degrees/s or radians/s, explicitly identified;
- optional magnetometer units and calibration status;
- sensor-frame axis diagram and handedness;
- actual sampling timestamps, not only a nominal frequency;
- orientation output as a normalized quaternion;
- Euler output in degrees with a declared rotation order and wrapping convention;
- device/firmware/fusion version and calibration identifier.

Implement a replay path that can feed stored samples through the same sensor
fusion, segmentation, feature extraction, scaling, and scoring code used on the
phone. Preserve raw streams so fusion parameters can be changed later. Add checks
for missing samples, duplicate timestamps, nonfinite values, saturation, long
gaps, excessive stationary noise, and implausible angle jumps.

The current REHAB files can test the downstream orientation pipeline, but cannot
calibrate raw accelerometer/gyroscope conversion because those exercise files
contain pitch/yaw/roll rather than raw six-axis samples.

## Phase 1: per-device bench calibration

Run this after obtaining the actual wearable and repeat after firmware changes.

1. Warm the device for its normal operating period.
2. Hold it motionless for at least 10 seconds. Estimate gyro bias on each axis and
   verify that corrected stationary angular velocity is close to zero.
3. Place each sensor axis successively upward and downward in six static poses.
   Estimate accelerometer offset/scale and verify gravity magnitude and axis signs.
4. Rotate through known 90° and 180° orientations about each axis using a jig or
   measured reference. Check signs, scale, quaternion normalization, Euler order,
   wrapping, and repeatability.
5. Measure actual sample intervals, dropped samples, and timestamp jitter.
6. If a magnetometer is used, perform hard/soft-iron calibration in the expected
   environment and repeat near likely interference sources. If it is not used,
   quantify yaw drift during stationary and exercise-duration trials.

Provisional engineering checks, to be revised against hardware specifications:

- corrected stationary gyro mean below 0.5°/s per axis;
- stationary pitch/roll standard deviation below 2°;
- median sample rate within 2% of its configured value and fewer than 1% missing
  intervals in a clean recording;
- known-angle error below 5° over the range used by the exercises;
- yaw drift below 5° per minute if yaw remains a model feature.

Failure of a check blocks scoring and produces a data-quality result, not an
atypical movement label.

## Phase 2: placement and anatomical calibration

At the beginning of every wearing session:

1. Attach the device at the documented wrist/forearm or shin location.
2. Record limb side and placement metadata.
3. Ask the user to hold the exercise-specific neutral pose for 3-5 seconds.
4. Estimate stationary gyro bias and reject calibration if movement/noise is high.
5. Save the median neutral quaternion `q0`.
6. Express subsequent orientation relative to neutral:

   `q_relative(t) = inverse(q0) * q(t)`

7. Map sensor axes into one canonical anatomical frame. Apply a documented mirror
   transform for left/right limbs if required and verify it with known motions.
8. Ask for one slow calibration motion in each expected dominant direction. Check
   that channel signs and ranges match the exercise configuration.

Use quaternion processing internally. Convert to pitch/yaw/roll only at the
feature interface. This reduces wrap and rotation-order errors, although Euler
features still inherit singularities and convention sensitivity.

## Phase 3: select and validate sensor fusion

Use an established Madgwick, Mahony, or vendor fusion implementation. Record its
name, version, parameters, sampling behavior, and magnetometer use. Tune parameters
on calibration recordings only.

Compare fused orientation against a measured reference during static poses and
slow/fast rotations. Evaluate pitch, roll, yaw (when applicable), drift, latency,
and recovery after acceleration. A six-axis filter can stabilize pitch and roll;
yaw is gyro-integrated and normally drifts without an external heading reference.

Before retaining yaw in a deployed model, show that yaw drift over one exercise
session is small relative to meaningful movement and that indoor magnetic
disturbance does not produce larger errors. Otherwise retrain a pitch/roll and
gyro-feature variant without yaw.

## Phase 4: pilot watch-data collection

For an engineering pilot, target at least:

- 5-10 participants;
- 10 usable repetitions per exercise per participant;
- two independent don/doff placements on different runs or days;
- all 14 selected exercises at the intended placement;
- therapist confirmation of exercise identity and intended execution;
- raw IMU, fused quaternion, calculated Euler angles, timestamps, repetition
  boundaries, device metadata, placement metadata, and quality flags.

This is approximately 1,400-2,800 candidate repetitions before exclusions. It is
enough to reveal large domain and placement problems, not to establish clinical
performance. Do not instruct participants to perform unsafe errors to manufacture
atypical data. Clinician-defined deviations require an approved protocol.

Assign pseudonymous participant IDs and session IDs. Split all data by participant,
never by repetition. Keep one final participant-level test set untouched until
the pipeline, thresholds, and feature choices are frozen.

## Phase 5: quantify the REHAB-to-watch domain shift

Run the same segmentation and 17-feature extraction on watch data. For every
exercise and feature, compare:

- median, interquartile range, and 5th/95th percentiles;
- standardized mean difference between REHAB and watch data;
- distributions by participant, side, and don/doff placement;
- missing/quality-rejection rates;
- repetition duration and segmentation-boundary review;
- score distributions under the existing REHAB model.

Visually review raw and normalized pitch/yaw/roll traces for a stratified sample.
Large or systematic shifts indicate a sensor-fusion, axis, placement, population,
or segmentation mismatch. Do not hide those shifts by fitting a scaler on all
data before measuring them.

Decision rule:

- If signals and features align and held-out watch behavior is stable, use REHAB
  as pretraining/reference data and add verified watch repetitions.
- If an affine feature shift dominates, fit the scaler on watch training data and
  re-evaluate feature distributions and scores.
- If movement shapes, axis relationships, or feature rankings differ materially,
  train the Isolation Forest on verified watch data only. Keep REHAB as a design
  and external-comparison dataset.

Isolation Forest has no neural layers to fine-tune. Here, "transfer" means reusing
the preprocessing/features and refitting the scaler, forest, and decision threshold
on the target-device domain.

## Phase 6: model and threshold calibration

For each exercise:

1. Fit preprocessing and segmentation settings on participant-level training data.
2. Derive quality thresholds from training data only and retain quality failures as
   unscorable outcomes.
3. Fit StandardScaler on verified reference-like watch repetitions from training
   participants.
4. Fit an exercise-specific Isolation Forest. Compare target-only training against
   combined REHAB-plus-watch training.
5. Use clinician-reviewed validation repetitions to choose the anomaly threshold
   for the intended operating point. Do not assume 5% contamination is the desired
   clinical false-positive rate.
6. Freeze the entire pipeline and evaluate once on unseen test participants.

Report participant counts, sessions, candidate and accepted repetitions, exclusions,
class definitions, inter-rater agreement, participant-level split, threshold choice,
confidence intervals, sensitivity, specificity, balanced accuracy, ROC/PR curves,
and unscorable rate. Report results per exercise and by relevant participant groups.

## Phase 7: phone parity and usability validation

Export the model into a phone-compatible representation; Python pickle files do
not run natively on the phone. For a fixed set of recorded repetitions, compare
every intermediate output between the research and mobile implementations:

- fused quaternion and relative orientation;
- smoothed pitch/yaw/roll;
- repetition boundaries;
- all 17 unscaled features;
- all 17 scaled features;
- anomaly score and final status.

Set numerical tolerances before testing. Require identical quality-gate decisions
and clinically immaterial score differences. Measure latency, memory, package size,
battery use, dropped samples, buffering delay, and behavior when calibration fails.

## Versioning and saved artifacts

For every released model, save:

- raw-data schema and sensor-axis diagram;
- hardware, firmware, fusion, app, and pipeline versions;
- placement and calibration protocol;
- feature order, scaler constants, quality thresholds, and model;
- participant-level split identifiers and dataset hashes;
- training/validation/test counts and evaluation report;
- known limitations, intended use, and invalid-use conditions.

Changing device hardware, placement, sample rate, fusion algorithm/parameters,
Euler convention, preprocessing, segmentation, or feature definitions triggers at
least a parity and domain-shift review. Material changes require recalibration and
possibly retraining.

## What can be completed now

Before watch recordings are available, the team can finalize the placement guide,
signal schema, calibration user flow, quaternion/Euler conventions, raw logger,
replay harness, quality checks, version metadata, and participant/session data
model. The current REHAB models can exercise the downstream software. Claims about
watch accuracy, typical/atypical detection, thresholds, and clinical performance
must wait for target-device recordings and independent labels.
