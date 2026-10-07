# Initial Run Review

This run produced 14 exploratory models from 3,971 source recordings:
12,440 retained training candidates and 3,216 retained held-out candidates.
These are algorithmic segments, not clinician-confirmed repetitions. 212 source
rows failed initial signal-quality checks; inspect each metadata.json for reasons.

Five preprocessing/feature tests passed. All 14 exported models passed verification
of feature schemas, split separation, exact-duplicate grouping, source/artifact
hashes, training-only completion quantiles, and saved-model inference parity.

## Observations from segmentation plots

The overview uses the first retained recording for each exercise, not a random or
representative validation sample. These observations are qualitative only.

- Bobath handshake shows plausible repeated cycles. The first and last attempts
  remain excluded by the conservative edge policy, even if a first attempt looks
  complete. The algorithm is allowed to miss useful data rather than infer an
  unobserved boundary.
- Bobath forward flexion/extension contains smaller intervening excursions, so
  cycle definitions need manual checking for double counting or merged cycles.
- Elbow flexion/wrist compression, wrist flexion/extension and flexion-pressure
  rotation show irregular or weak distal-forearm movement in the illustrated rows.
  A single forearm sensor may not observe the intended wrist/pressure task well.
  Their trained models should not be presented as validated per-repetition detectors.
- Shoulder internal/external rotation, flexion-pressure rotation, ankle-extension/
  knee-rotation and knee flexion have completion p95 thresholds above 45 degrees
  (65.41, 65.08, 50.27 and 57.66 respectively). 45 degrees is a review flag only,
  not an additional acceptance cap. Large thresholds may indicate poor cycle
  alignment, Euler-angle behavior, baseline change or genuine execution variation.
- Ankle-extension/knee-rotation lost 106 of 313 source rows at signal-quality
  screening, which is substantial. Investigate these exclusions with the authors;
  do not treat the remaining sample as an unbiased representation of the exercise.
- Knee-flexion traces include sharp transitions/plateaus. Hip-flexion examples
  show relatively small pitch changes. Both require sensor-placement and boundary
  confirmation before interpreting the features as clinical joint movement.

## Reporting

Describe the results as a reproducible baseline with automated candidate
segmentation. Do not report reference-outlier percentage as detection accuracy.
Do not claim 120 participants were used in each model, that recordings are unique
patients, or that ankle/wrist watch performance has been validated.

The nominal 50 Hz assumption, three orientation channels, 17 features, model size,
quality filters, session/participant uncertainty and planned watch validation
belong in the methodology. The saved model files are approximately 1.8-2.6 MB each;
phone export and runtime performance are separate work.
