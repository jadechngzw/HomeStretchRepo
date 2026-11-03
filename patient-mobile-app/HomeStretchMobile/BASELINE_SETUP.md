# Baseline recording and pre-exercise survey

The exercise list and Settings link to a four-step baseline setup flow. Existing and custom exercises are supported. Each recording captures exercise/side, wrist, watch-face position, notes, a pre-exercise survey, raw acceleration and gyro samples, detected repetition boundaries, selection, and nine-feature reference statistics. Surveys require an explicit 0–10 pain response; zero is valid, unanswered is not zero. The existing post-exercise survey is also saved locally.

## Current review policy and live guidance

Temporary prototype policy: new saved baselines are automatically approved. On loading, existing compatible pending recordings are also auto-approved and persisted in a new catalog revision. This is labeled automatic prototype approval, not clinician review. The latest valid baseline for each exercise + side + wrist + face position is active; earlier records are retained. Incompatible references are not activated.

Opening an exercise with an active baseline shows the live guidance screen. Choose the baseline/placement, explicitly confirm placement, complete the pre-exercise survey, and start. The set freezes its reference and survey so later catalog changes cannot alter comparisons mid-set. It records both sensors at 25 Hz and compares confirmed repetitions against all nine feature bands. Any feature outside its fixed range is labeled “Atypical vs your baseline,” with reasons; unassessable or gapped data is never labeled within range. This is experimental feedback, not a clinical correctness score.

Live assessment runs every 750 ms with a one-second trailing buffer because the notebook filter is noncausal. A repetition must first be segmented/confirmed; feedback therefore has a short delay and can change at final full-recording processing. Stopping includes a two-second return/hold window, acknowledged STOP and tail drain. Pace uses the latest three completed reps: a majority below 0.8 s prompts slowing down; a majority above 3 s prompts a quicker steady pace. These prompts recover as pace changes. The rep target is advisory and does not stop recording. Counts, flags, and timing reset on every new set. Leaving/backgrounding/disconnecting interrupts the set and prevents a normal complete assessment.

Completed baseline-guided session summaries are sent to the existing Firestore sessions collection with baseline ID/version, placement, per-rep feature flags and durations, and pre-exercise pain/survey ID. Baselines and full surveys remain local. No clinician sync or sign-in is added. Exercises without compatible baselines retain the prior manual/legacy curl flow; its pace prompts now also recover and reset correctly.

## Storage

On iOS, raw recordings and immutable catalog revisions live in the app Documents/exercise-baselines directory. NSUserDefaults stores only the pointer to the latest successfully written catalog revision. Catalog revisions contain custom exercises, surveys, placement metadata, analysis and selection. A failed write leaves the previous committed catalog intact. Do not delete app data if recordings need to be retained. This is device-local research storage, not patient-account isolation. Web preview uses browser localStorage; real watch capture is supported by the existing iPhone development build only. Android baseline storage is not enabled.

Each saved baseline contains the exact selected repetition IDs and versioned statistics; raw frames are stored separately. Notes can be edited without altering movement statistics. Old catalog revisions are retained for recovery and are not automatically pruned in this first version.

## Recording and processing

The new recorder uses protocol v3, sensor mask 9 (acceleration + gyro), 25 Hz, PPG off. Both monitors are subscribed before configuration/start. Application-level acknowledgments, shared sequence numbers, per-sensor timestamps, stream stalls, STOP-tail drain and generated/dropped counts are checked. Missing/invalid/unexpected data make the recording incomplete and prevent saving it as a baseline. Backgrounding/navigation/disconnection interrupt recording. Capture is bounded to approximately three minutes. Stop prompts a two-second return-and-hold window before the acknowledged stop. Unconfirmed final movements are excluded.

`src/baseline/analysis.ts` ports the nine-feature patient-baseline notebook to TypeScript for native 25 Hz capture: alignment, optional initial two-second gyro-bias correction, fourth-order 4 Hz zero-phase Butterworth filtering, quaternion orientation tracking, trough-to-trough segmentation and final-rest confirmation, per-rep moments, baseline-axis estimation, nine features and mean ±3 sample-SD bands. This path deliberately requests 25 Hz rather than accepting arbitrary offline 50 Hz files. It does not change the existing bicep rep counter. The live baseline count is provisional; complete capture is processed again before review.

Failed initial stillness is disclosed, with no bias correction. At least three unique eligible repetitions are required. This is a computational minimum, not a clinical recommendation. Very low baseline SD is shown for reviewer attention. Watch positioning and initial pose must be consistent; there is no automatic frame alignment across recordings. The detector is exploratory and is not validated for every exercise. Durations are segmentation checks, not one of the nine features. Unassessable reps are distinct from feature-level departures. No global clinical correctness score is generated.

## Verification

- `node --test tests/*.test.mjs`: legacy connection/curl tests plus baseline analysis, capture and persistence tests.
- Synthetic single-axis and varying-axis datasets reproduce the original Python notebook's boundaries and nine-feature means/sample SD within 1e-6. Fixtures are synthetic, not patient recordings.
- Recorder tests cover paired timestamps/shared sequences, actual requested configuration, acknowledgment failure, missing sensor, gaps/invalid frames and STOP-tail delivery.
- Storage tests cover persistence after reopening, zero pain vs missing pain, failed saves and retained replacements.
- `npx tsc --noEmit`: checks app types. CSS declarations also resolve two pre-existing type errors.
- Browser smoke test checks setup, required survey response, return navigation and disconnected-watch gating. Browser preview cannot validate native BLE or iPhone filesystem behavior.

## Physical acceptance check still required

Use the installed iPhone development build with a compatible watch. Connect it in Settings, open Add exercise / Set up baseline, choose placement, complete the pre-survey, hold still initially, then record at least three complete repetitions and return/hold before stopping. Review/exclude reps, save, relaunch the app and verify the automatically active baseline. Record a replacement and verify both remain and the latest matching placement is active. In a separate disposable test, disconnect or background during capture and verify saving is unavailable. Open that exercise, confirm placement, and verify live rep flags, pace recovery and next-set reset. Also verify the legacy flow for exercises without a baseline.
