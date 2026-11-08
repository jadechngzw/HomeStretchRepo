# HomeStretch connected app

This change is prepared for the merged repository at `~/Desktop/HomeStretch/HomeStretchRepo`.
The older `Documents/ChatGPT/HomeStretch/app_sync_work` copy is not the integrated app.
No Firebase users, invitations, messages, live records, or published rules were changed during implementation.

## What is connected

- Patient Firebase Authentication (sign in or create a patient account).
- One completed pre-survey and post-survey per patient per local day, with a persistent upload queue.
- One final document per recorded exercise set. Captured patient UID cannot be replaced by a typed name.
- Per-rep numeric metrics, the exact baseline used, quality flags, and analysis version.
- Counts-only manual sets have null metrics and null per-rep durations, never invented measurements.
- Local session uploads retry the same document ID. Raw session frames are not saved or uploaded by the exercise flow. Baseline setup retains its local calibration recording.
- Separate local catalogs for different signed-in patients. Older unassigned local records are left untouched; they are not automatically attributed to a patient. Record a new baseline under your test account.
- Clinician login, trusted clinician role, patient invitations, verified patient acceptance, linked-patient charts, and messages.
- Existing clinician prototype pages are retained on disk but are not exposed in the authenticated app.
- The new clinician app only queries records belonging to actively linked patients; no shared patient-data cache.
- Patient home and readiness placeholders have been removed. Connection status is not a clinical readiness score.

## 1. Server credentials

Keep the downloaded JSON outside the repository. In Terminal:

```sh
export GOOGLE_APPLICATION_CREDENTIALS="/Users/jadechng/Documents/VitalWaveSecrets/homestretch-pipeline-firebase-adminsdk-fbsvc-25d212effa.json"
cd ~/Desktop/HomeStretch/HomeStretchRepo
```

The server is pinned to Firebase project `homestretch-pipeline`. Its web API key is a public Firebase application identifier, not an Admin credential. It can be overridden with `FIREBASE_WEB_API_KEY`.
Never place the Admin credential in the mobile app, a commit, or a message.

## 2. Clinician account (user action)

In Firebase Console for `homestretch-pipeline`, open Authentication. Enable Email/Password if needed.
Create the clinician account `cindylou@health.com` with a password you choose privately, or use its existing account.
Do not share the password with Codex. Make sure this is the intended account before granting access.
Then run this explicit administrator operation:

```sh
.venv/bin/python streamlit-app/tools/grant_clinician.py --email 'cindylou@health.com' --name 'Clinician'
```

This writes `users/{the actual Auth UID}` with role `clinician`. Mobile clients cannot grant themselves this role.
The script does not create an account, choose a password, or send email.

## 3. Publish the rules and index together (user action)

From the repository root, using your signed-in Firebase CLI:

```sh
firebase deploy --only firestore:rules,firestore:indexes --project homestretch-pipeline
```

If Firebase CLI is not installed, use `npx firebase-tools login` and then
`npx firebase-tools deploy --only firestore:rules,firestore:indexes --project homestretch-pipeline`.
Wait for the sessions index to finish building in Firebase Console before querying sessions.
These rules accept the updated final-session uploader. Older app builds using the previous in-progress writer need to be updated alongside the rules.
No rule deployment has been performed by this task.

## 4. Launch the clinician app

```sh
cd ~/Desktop/HomeStretch/HomeStretchRepo/streamlit-app
../.venv/bin/python -m streamlit run clinician_app.py
```

Sign in with the clinician account. With no accepted invitations, an empty patient list is expected.
Login sessions use Firebase ID tokens and currently require signing in again when the token expires (about one hour); silent refresh is not implemented.
Use Refresh to retrieve new records or messages. Patient lists and session views are not automatically polled.

## 5. Launch the updated patient app

Use the merged project, not the old `app_sync_work` server:

```sh
cd ~/Desktop/HomeStretch/HomeStretchRepo/patient-mobile-app/HomeStretchMobile
npm install
npx expo start --dev-client --lan
```

The existing Firebase login imports AsyncStorage; its compatible dependency is now explicitly declared.
If the installed development client does not include that native module, rebuild the iOS development client before testing.
Use a separate patient account with an email you control. A new patient can use Create account; verify the email via the message Firebase sends.

## 6. End-to-end acceptance test

1. Clinician: open Invitations, enter the exact patient account email, send an invitation.
2. Patient: open Messages (screen title Care team), verify email, accept the invitation.
3. Clinician: Refresh. The patient should appear; no previous records are invented.
4. Patient: complete the daily pre-survey and create a baseline under this account. Record a set with the watch.
5. Patient: return to Exercises, choose Finish for today, complete the post-survey.
6. Clinician: Refresh and select the recording. Check rep count, graph values, stored baseline band, and both surveys.
7. Send a short test message each way. Only the linked conversation should show it.
8. Test upload retry by recording offline and reopening online. The document ID and total number of sessions must not duplicate.
9. Disconnect the patient from the clinician's Manage connection section. Records/messages must no longer be accessible through that connection.

This physical phone/watch and real Firebase test is still required. Local automated tests do not replace it.

## Data contract

`users/{authUid}`: trusted role and display_name. Passwords remain in Firebase Authentication.
`careInvites/{clinicianUid_patientUid}`: pending/accepted/declined, exact target UID, names, link ID, expiry, timestamps. Invitations expire after seven days.
`careLinks/{clinicianUid_patientUid}`: active/revoked, both UIDs, accepted invite ID, display names.
`sessions/{stableSessionId}`: schema_version 3, patient_id, patient, exercise, started_at/ended_at Firestore timestamps, local_date, timezone, completed/interrupted status, rep_assessments including metrics, baseline.reference.stats, counts, survey link, quality, analysis_version.
`dailySurveys/{patientUid_localDate_phase}`: once-daily answers, patient_id, local_date, phase, recorded_at. Sync metadata remains local.
`conversations/{careLinkId}/messages/{messageId}`: sender_id, text, created_at. Active links are required on every operation.

Session documents keep compatible existing field names instead of renaming every consumer. Daily surveys are authoritative; embedded session pain fields remain for older readers.
Manual and accelerometer-only legacy sets do not produce the nine baseline metrics. The clinician page explains missing metrics rather than drawing fabricated charts.
No grouping of multiple sets into a workout has been added in this version; each set appears as its own recording.

## Local validation

- Mobile: `node --test tests/*.test.mjs` and `npx tsc --noEmit` in the mobile folder.
- Clinician: `.venv/bin/python -m unittest discover -s streamlit-app -p test_connected_app.py`.
- Firestore: `tests/firestore-rules.cjs` uses `@firebase/rules-unit-testing` against a demo-project emulator on port 8088, never production. Requires Java 21+, Firebase CLI, Firebase JS SDK and rules-unit-testing. Tests load the repository's actual rules explicitly.
