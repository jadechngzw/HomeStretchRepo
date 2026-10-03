# VitalWave v0 protocol, version 3

Device name: VitalWave-v0. One BLE peripheral link; no bonding, no standalone
recording. Protocol v1/v2 apps/firmware are deliberately incompatible. This is a nearby-device development prototype;
commands/data are not authenticated/encrypted. Pairing is a later milestone.

UUID base: 7bfa0000-6e4d-4b9d-923b-5d234081a100
- Service: 7bfa0001-6e4d-4b9d-923b-5d234081a100
- Control (write with response): ...0002...
- Status (read + notify): ...0003...
- Samples (notify): ...0004...
- Telemetry (read + notify): ...0005...

All values little endian. Status and telemetry are fixed 20 bytes. Samples contain 1–12 consecutive
20-byte frames per notification, limited by negotiated ATT MTU. MTU 23 uses
one frame; maximum server MTU 247 permits 12 (240 bytes). Decode every frame
in order; notification boundaries are not sensor-frame boundaries.
Subscribe to BOTH status and samples before START. No automatic resumption.

Control, 12 bytes, Python <BBHII:
version=3, opcode (1 START / 2 STOP / 3 KEEPALIVE / 4 CONFIGURE), request_id uint16,
argument uint32 (START sensor mask: 1=accelerometer, 2=temperature/humidity, 4=PPG, 8=gyroscope), session_id uint32.
Session ID is nonzero and allocated by app. START only from idle, one active
session. STOP/KEEPALIVE must match current session. GUI sends KEEPALIVE every 1s.
No keepalive for 5 seconds, unsubscribe, or BLE disconnect stops sensors.
Link-loss detection also depends on BLE supervision timeout (requested 2s).

Status, 20 bytes, Python <BBBBIHHII:
version, state (0 idle /1 recording /2 fault), reason (0 success,1 command invalid,
2 busy,3 charger fault,4 keepalive expired,5 disconnected/unsubscribed,6 sensor failure),
mask, session_id, last_request_id, charger (0 off,1 enabled,2 fault),
frames_generated uint32, frames_not_queued uint32.
BLE write success is not application acknowledgement. Wait for matching
last_request_id, session and expected state/reason. Status is also readable.
STOP status reports generated/drop totals. Recording is complete only after
STOP acknowledgement and consistency checks. Missing/invalid data remain explicit.

Sample, 20 bytes, Python <BBIHIhhhh:
version, type (1 acceleration /2 gyro /3 temperature+humidity /4 IR /5 red /6 green /7 blue), session_id,
sequence uint16 (one sequence shared across all streams, wraps), watch_ms uint32
(since boot, wraps after ~49.7d), x,y,z int16, validity int16 (1 valid,0 invalid).
Accel raw *0.000061 = g. Gyro raw *0.00875 = degrees/s.
Temperature x/100=degrees C; humidity y/100=percent; z unused.
PPG: count = (uint16(x)) | (uint16(y) << 16), y 0..7, z=0. Full 19 bits.
IMU configured at 104Hz, read/stream nominally 10/25/50Hz (not anti-aliased
for precision spectral analysis). Temperature single shot 0.5/1/2Hz.
PPG 50/100Hz single colour, 50Hz multi-colour. Reconstructed PPG watch_ms starts
at acquisition setup plus n*1000/rate, subject to the sensor oscillator tolerance;
not exact cross-sensor timing. All colours in one FIFO frame share a timestamp.
CONFIGURE is idle-only: argument bytes [imu_hz, temp_period_100ms, ppg_hz, leds].
Valid IMU values 10/25/50; temp 5/10/20; PPG 50/100; LEDs bits 0 IR,1 red,2 green,
3 blue (0..15). More than one LED requires 50 Hz. No charge settings are writable.
Settings validated and acknowledged before START; no changes during recording.
No averaging/filtering/repair of stored raw values. Invalid values saved as invalid,
not presented as valid zero measurements. Sequence advances even on notification
backpressure; generated and dropped counters reveal missing tail packets.

File policy: local CSV plus metadata JSON, unique session ID. Never overwrite.
On disconnect/app failure timeout mark incomplete; manual STOP acknowledges
sensor shutdown and validates completeness. GUI uses bounded display history;
all received raw samples are written incrementally by a separate worker.

Telemetry (20 bytes): [version=3, REG08_valid (0/1), BQ25601_REG08, policy (0/1/2)],
button1_presses uint16, button2_presses uint16, watch_ms uint32, reserved 8 zero bytes.
Buttons increment on debounced presses only while connected and subscribed.
App takes the first counters as baseline, handles a delta of one, ignores bursts;
no press replay across disconnect. Actions are host-configurable, not persisted
in watch flash. Marker time is telemetry snapshot time after button debounce.
The telemetry characteristic updates every 500ms and upon button events. It
reads only REG08, not clear-on-read fault registers. No battery percentage exists.

An application FIFO holds 128 sample frames; SoftDevice notification queue 32.
The readable status updates immediately after commands even under sample queue
backpressure. Pending status then telemetry take priority over new sample batches.
After the write completes, the host waits 1s for a matching status notification;
if absent it reads status (1s timeout). GATT writes have a 1.5s timeout.

STOP acknowledgement may precede queued samples. The host waits up to 3 seconds
for received >= generated - dropped before closing the recovery file. Completeness
still requires zero drops, gaps, invalid and unexpected samples and exact counts.
Disconnect discards queued frames, accounts drops and marks the recording incomplete.
Requested connection interval is 15–30 ms, supervision 2s; the central decides the
negotiated parameters. No automatic retry/restart of an interrupted recording.

Protocol-v3 mask changes require upgrading BOTH app and firmware. CSV format
remains version 2, with protocol_version=3 in new session metadata. Recovery files
are incremental and closed on Stop; explicit Save exports a copy. Display filtering
and HR/ratio analysis never modify the raw CSV.
