# Mobile → clinician session contract (version 2)

Completed mobile sets are saved locally before upload. Configure Patient & session sync in phone Settings with a stable patient ID and name. This profile labels data; it is not Firebase authentication. Unassigned sessions require explicit assignment before uploading.

Firestore document: `sessions/{session_id}`. Retries overwrite the same ID. ISO dates in local JSON become Firestore timestamps (`started_at`, `ended_at`, and legacy `timestamp`). The phone retries pending uploads on foreground, every minute while active, and from Settings. Upload errors remain visible there. Database rules and authentication still control whether writes succeed.

Shared fields:

- `schema_version: 2`, `source: homestretch-mobile`, `session_id`
- `patient: {id, name}`, plus `patient_id` and `patient_name` for compatibility
- `exercise: {id, name}`, `started_at`, `ended_at`, `duration_sec`, `protocol_session_id`, `complete`
- `num_reps`, `num_typical`, `num_atypical`, `num_unassessed`, `atypical_rep_ids`, `rep_durations`
- `rep_assessments`: each row has `rep`, `duration_sec`, `assessable`, `classification` (typical/atypical/unassessed), `features_outside_baseline`
- `pain.before` and `pain.after`: survey snapshots including score, symptoms, regions, notes, and time; absent surveys are null
- `pre_exercise_pain`; `pain_level` is the latest available rating (post if available, otherwise pre)
- `baseline`: reference ID, analysis version, placement and reference statistics; null for legacy counting
- `quality`: stillness result, unconfirmed final movement and placement warning
- `guidance.flags`: per-rep baseline differences
- `raw_file`: local filename only, never a cloud download URL

Local storage: app document directory `exercise-baselines/`. The catalog stores profiles, baselines, surveys and the upload queue; raw baseline recordings and live-set frames are separate JSON files. Raw waveforms are not uploaded to Firestore or Cloud Storage. Standalone baseline recordings remain local; a session embeds its reference statistics, not the full baseline waveform. Local catalog revisions currently remain on disk.

Use the live exercise screen's Post-exercise survey button to attach that survey to the most recent saved set. It updates the same cloud document on the next sync. Standalone surveys and surveys submitted elsewhere remain local. Legacy reps without baseline analysis are marked unassessed, not typical. Interrupted live sets are not uploaded. Recordings whose uploads failed before this queue was introduced cannot be recovered from the queue.

The Patients dashboard understands v2 and existing legacy fields. Stable IDs distinguish patients with the same name. Historical name-only records remain separate name-based profiles rather than being automatically assigned to a new patient ID.

Validation: Node unit tests cover schema, failed uploads, idempotent retries, queue persistence, and post-survey acknowledgement races. Python tests cover dashboard normalization. Production delivery must still be checked from phone Settings; no test records are written to production by the test suite.
