# Bicep curl counting — first phone integration

This milestone runs on the iPhone development build, using the selected VitalWave-v0 watch.
It does not upload to Firebase, run the Python classifier, process PPG, or implement the
separate live-guidance state machine. A set's count and timing stay in memory until the
next set or app reload. Durable session storage and Firestore upload are follow-up work.

## Try it

1. Connect the watch in Settings. Open Bicep Curls and select the exercising arm.
2. Wear the watch consistently on that wrist, on the back of the wrist with the same
   strap orientation for each trial. Start with the arm relaxed down at your side.
3. Tap Start Exercise. Keep the arm still until “Counting your reps” appears (about two seconds).
4. Do controlled full curls and return to the starting position after each curl.
   The counter updates after the filtered signal confirms that return, not on every peak.
5. Count manually alongside it, including the first and last curl. Test both wrists,
   small movements, pauses, more than ten curls, and standing still.
6. Tap End Exercise. The counter remains visible; Start Next Set resets it to zero.
   End the current set before changing arms. Each Start/End pair is one set.

Leaving the exercise screen, backgrounding the app, a fault, or lost Bluetooth interrupts
the set. No auto-resume. Keep the app visible for this first version. Isolated missing or invalid samples may be bridged when valid readings remain no more
than 60 ms apart and missing samples are at most 10% of the movement window. Longer
gaps require a still starting position again. Invalid/drop totals remain visible in
the acquisition-completeness flag even when a rep can be estimated. Reps
already confirmed remain counted. Raw drop/invalid counts determine whether the ended
set is marked complete. This is acquisition completeness, not a judgment of exercise form.

## Algorithm and limits

Reference: `signal-processing/session_pipeline/motion.py` and `exercises.json`.
The phone requests 50 Hz accelerometer data (mask 1), scales raw values by 0.000061 g,
and processes the Y axis. It uses a 2 Hz causal second-order Butterworth low-pass to reduce live delay,
the original 0.6 g excursion threshold and 60 ms gap limit. The movement window
(from crossing the start threshold to returning) accepts 0.5–6 s, with at least
0.8 s between counted reps. This window excludes the initial/final portions of a
full curl, so the original 0.8 s window rejected some otherwise complete 1 s curls.
There is no fixed post-rep pause; excursion/return hysteresis re-arms the detector. It replaces offline forward/backward filtering with a causal filter and
peak-to-peak segmentation with baseline → excursion → return. The first full curl can
therefore count, but this is an adaptation, not numerically identical Python output.
The baseline comes from about two seconds of still data (Y range below 0.12 g).
Movement begins at 0.18 g from baseline and returns within 0.14 g; the detector handles
both signs. Filter delay is expected. Arm selection labels the set; it does not provide
anatomical calibration. Watch rotation, technique, or limited excursion can cause missed
or extra counts. Verify against observed curls on both wrists before treating counts as
accurate. No machine learning or form-quality labels are produced.

`CurlSession.onRep` emits completed-rep events with count, duration, and sensor-relative
end time for future guidance integration. The rep goal never stops acquisition or caps count.

## Transport

Protocol v3; subscribe to status and samples before CONFIGURE/START. CONFIGURE's ACK
retains the previous firmware session ID, unlike START/STOP/KEEPALIVE. Commands are
serialized, use nonzero request/session IDs, and require matching application ACKs;
status-read fallback handles missing notifications. Heartbeats run each second. STOP
waits up to three seconds for queued samples and checks generated/drop/received totals.
Every 20-byte frame in a notification is decoded. Sequence/timestamp wraps, invalid data,
foreign sessions and duplicate/out-of-order samples are handled explicitly. Unsubscribing
on interruption stops the firmware; five-second heartbeat expiry provides a fallback.

## Verification

Run `node --test tests/*.test.mjs` on Node 22.18+ (or the project's Node 26).
Tests cover the packet format, counter polarity and first/full reps, >10 reps, stillness,
partial cycles, gaps, firmware acknowledgements, heartbeat lifetime and post-STOP tails.
Hardware accuracy and left/right mounting remain physical checks.
