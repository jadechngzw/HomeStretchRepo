# VitalWave v0

A Mac recorder for the VitalWave nRF52840 watch. Connected BLE Start/Stop,
IMU acceleration/gyro, temperature/humidity, four-colour PPG, live plots,
configurable buttons, live charger status and local CSV recordings.
The firmware always includes the 240mA charger policy. No standalone recording.

## Launch on this Mac


```
cd /HomeStretchRepo/hardware/vitalwave_v0
./Launch.command
```

You can also double-click `Launch.command` in Finder. Allow Bluetooth access
for Terminal/Python/the launching app when macOS asks. Bluetooth must be on.
Use `./Launch.command --demo` to try the interface with clearly labelled
simulated data; it does not contact hardware. Demo metadata has `demo: true`.
Tkinter is available in /opt/homebrew/bin/python3.11 on this Mac; the current
python3.14 installation lacks Tkinter, so use this project's .venv.

For a new machine: install Python with Tkinter, then run `tools/setup_mac.sh`.
Application dependencies are pinned in requirements.txt. Tests additionally
require pytest (`.venv/bin/python -m pip install pytest`).

## Flash the new firmware

This firmware replaces the current application and includes Nordic S140.
Keep the magnetic charging input unplugged. Power the board from battery;
UART VCC disconnected. J-Link VTref/GND/SWD wired as before. PPG is shut down
at startup and enabled only during a selected recording. Never move its ribbon
with power attached. Close the old GUI before flashing; this update requires
both the new firmware and new app (protocol version 3).

In J-Link Commander select NRF52840_XXAA, SWD, 100kHz, then:

```
loadfile "/HomeStretchRepo/hardware/vitalwave_v0/firmware/build/vitalwave_v0.hex"
r
g
```

Flash **vitalwave_v0.hex**, not application.hex: the combined image includes the
required SoftDevice and MBR. Do not mass erase as a routine step. No automatic
flashing or physical charging has been performed by this project setup.
The old PPG firmware cannot respond to this app's connected BLE commands.

## First real recording

1. Launch the app and click Scan. Select `VitalWave-v0`, then Connect.
2. Verify no watch/charger fault. Choose recording name and folder.
3. Select sensors and rates. Start with PPG Off to check IMU/temperature, then
   try Red at 50 Hz, then the other colours or All colours in separate sessions.
   Start recording; UI waits for watch reply.
4. Keep the board still, then gently rotate it. Acceleration magnitude should
   be approximately 1g when stationary; gyro near zero and change on rotation.
   Temperature/humidity should be plausible, not necessarily equal to skin or
   ambient temperature because of sensor placement and board heating.
5. Click Stop, then Save as to export. Inspect the CSV and JSON. `complete: true` requires a normal
   acknowledged stop, no missing/invalid/unexpected samples, and matching counts.
6. Test disconnect during a separate recording. Metadata must say incomplete.
   The watch stops on detected BLE disconnect, unsubscribe, or after five seconds
   without an app heartbeat. No reconnect automatically resumes recording.

One phone or computer controls the watch at a time. All recordings save on the
connected Mac. Keep the app open; sleep/background suspension can end recording.
An unexpected process kill leaves metadata `complete: false`; the CSV flushes
roughly once a second, so the final fraction may be lost in an abrupt crash.
Bluetooth disconnection is detected after link supervision; the requested
supervision timeout is 2s but actual connection parameters can differ.

## Files and units

Files use `<name>_<date-time>_<session-id>.csv` and `.json`, with exclusive
creation to avoid overwrite. CSV includes host UTC receipt time, watch millisecond
timestamp, sequence, sensor type, raw XYZ and scaled values, and validity.
Acceleration = raw*0.000061 g; gyro = raw*0.00875 degrees/s; temperature raw/100 C;
humidity raw/100 percent. For temperature frames X=temperature, Y=humidity.
All received raw data are stored; display history is bounded and redrawn at at most 2Hz.
IMU stream choices: 10/25/50 Hz (internal ODR 104 Hz). Temperature and humidity:
0.5/1/2 Hz, shared measurement. These are target polling rates; timestamps expose
jitter. This is not precision anti-aliased acquisition. PPG: 50/100 Hz for one
colour, 50 Hz per colour for any combination. PPG uses the sensor FIFO, 220 us pulses,
8 uA ADC range and nominal 2 mA LED currents. Full 19-bit counts are retained in
CSV x; raw_x/raw_y contain the split low/high words. Colours are sampled in
sequence within each sensor frame, not at precisely the same instant.
PPG timestamps are reconstructed from the configured sensor rate and session
start (not hardware-synchronised to the IMU). FIFO overflow/optical faults stop
the recording as incomplete. This update does not calibrate independent sensor
clocks, accelerometer offsets or gyroscope bias. Acceleration includes gravity.
Slow optical baseline drift is removed only in the filtered display/analysis;
raw recordings preserve it. Poor skin contact, saturation and motion still matter.

Button 1 (SW1/P0.13) defaults to Start/Stop. Button 2 (SW2/P0.03) defaults to Add
marker. Both can instead be Disabled or assigned either action in the GUI.
Buttons are active-low with 40 ms debounce; release before pressing again.
Mapping is handled by the connected app and saved on this Mac with rate choices
in desktop_preferences.json. Markers are in the recording's JSON metadata with
watch/host times. Buttons do not start standalone recordings. Rapid presses
while the app is busy are ignored; queued bursts are not replayed.

Live charger telemetry refreshes every 0.5 seconds, including while idle.
The UI distinguishes external power absent, plugged in/not charging, pre-charge,
charging, charge complete, and fault. Status comes from BQ25601 REG08; it is not
an actual-current measurement. Battery percentage is unavailable: the schematic
has no VBAT-to-MCU sensing circuit or fuel gauge. The 3.3 V rail is regulated and
cannot be used to infer battery charge.

For first optical checks use battery power with charging disconnected, as in the
previous PPG tests. Board LED supply voltage can limit optical performance,
particularly green/blue; selecting a colour does not establish a valid pulse.
BLE pairing, phone UI and updates over BLE remain future work.

## Recording and plot controls

Select accelerometer, gyroscope, temperature/humidity and PPG independently.
Disable PPG with **PPG enabled** unchecked. PPG colour checkboxes accept any
combination; **Red + IR**, **All** and **None** are shortcuts. Multiple colours
run at 50 Hz each; a single colour allows 50 or 100 Hz. Rates apply at Start.
Temperature and humidity share one sensor measurement/rate.

**Show these plots** controls display only: hide any graph without changing the
recording. Temperature and humidity have separate display toggles. Scroll down to
see the rest of the plots; each has its own axes and height. PPG display choices
are Raw, Centred (mean removed), and Filtered (0.5–4 Hz causal bandpass).
The first 3 seconds of each valid segment in the live rolling window are hidden
to suppress filter settling; offline plots omit the first 5 seconds and final
1 second of each segment. Raw view still shows all readings. Filtering is not
motion compensation.

**Stop** acknowledges sensor shutdown and waits up to 3 seconds for the final
counted samples. It retains CSV/JSON automatically in the selected folder's hidden
`.recovery` directory. **Save as** exports a copy with a chosen filename, refusing
to overwrite existing files. Recovery remains even if you start another recording
without exporting. Finder: press Command+Shift+Period to show hidden folders.
An incomplete recording remains available; inspect its JSON counts/reason.

Live heart rate is a **preliminary estimate**, updated every 2 seconds after a
13-second warm-up, using the recent 8-second window. This introduces several
seconds of lag; it is not beat-by-beat instantaneous heart rate. Flat, clipped,
gapped or inconsistent windows return no estimate. Regular movement can still
look like a pulse: quality checks are heuristic, not validated exercise accuracy.

After Stop, **Process PPG** creates an HTML report, PNG plots and JSON beside the
recording. **Analyse existing CSV** works on earlier recordings too. Reports show
raw and offline-filtered PPG, a heart-rate trend with rejected windows left blank,
and mean HR across accepted overlapping windows with coverage counts. Offline
filtering uses future samples within each segment and differs from live display.
Raw source files are never altered. The first 5 seconds are excluded from HR;
8-second windows advance every 2 seconds (roughly 40–200 bpm search range).

Red + infrared reports include a diagnostic ratio R = (ACred/DCred)/(ACir/DCir)
only when paired windows pass the checks. AC here is filtered RMS. **No SpO₂
percentage is produced**: this board requires calibration of the optical setup,
LED wavelengths and algorithm against a suitable reference. A generic equation
would give an unjustified oxygen-saturation number.

Errors are logged in `logs/app.log`; native Python crash traces go to
`logs/crash.log`. If the all-sensor hardware test fails, keep these and the
recording CSV/JSON. A watch sensor/charger fault, BLE loss and UI exception are
different failure paths; the app retains the data rather than claiming success.

## Mandatory charging module

`firmware/src/power/charger_policy.c` is the tested plugfix policy, copied without
logic changes: nominal charge current 240mA, regulation 4.080V, input limit 500mA
reapplied after source detection, precharge/termination 60mA, watchdog disabled,
5h safety timer, IC thermal regulation 90C. App commands cannot modify it.
It initializes before BLE and is polled at >=100ms intervals while advertising,
connected, recording and idle. Faults latch charging off, stop acquisition, and
prevent Start. If I2C fails, firmware cannot guarantee physical shutdown;
reported fault requires disconnecting charging power and checking the board.

The hardware /CE pull-down means firmware cannot guarantee charging OFF before
MCU startup or independent charger resets. Continue booting before connecting
charging input. TS is a fixed divider: no real battery-temperature monitoring.
Register verification is not measurement of actual battery current. This version
needs an on-board charging regression test before you resume charging with it.

## Organization

- firmware/src/board.* — shared I2C and timing; pin mapping P0.19 SDA/P0.20 SCL
- firmware/src/sensors.* — LSM6DS3TR-C and SHT3x access
- firmware/src/ppg.* — optical configuration, FIFO reads and LED shutdown
- firmware/src/config.* — validated sampling settings
- firmware/src/session.* — commands, acquisition state and heartbeat timeout
- firmware/src/main.c — S140 GATT transport and scheduling
- firmware/src/power/ — mandatory charger policy
- desktop/ui/ — Tk window and Matplotlib display
- desktop/bluetooth/ — Bleak transport and explicit demo transport
- desktop/recording/ — recovery CSV/metadata, completeness checks and exports
- desktop/processing/ — live HR estimates and offline PPG reports
- desktop/protocol.py and protocol/specification.md — wire format
- tools/ — setup, build/test support, GUI smoke test
- tests/ — protocol, storage, acknowledgements and firmware policy tests

The earlier diagnostics remain in sibling directories, not duplicated here.
See ../RUN_TESTS.md for previous bring-up history. Source files here use relative
project paths; the absolute examples above are conveniences for this Mac.

## Build and tests

```
python3 tools/setup_sdk.py
python3 firmware/build.py
./tools/run_tests.sh
.venv/bin/python tools/smoke_gui.py
```

Requires Arm GNU tools on PATH. SDK download is checksum pinned, vendor files
and generated builds excluded from Git. The build unconditionally links charger
policy. `firmware/build/manifest.json` records firmware hash and power settings.
Inherited Nordic libc syscall linker warnings concern unused OS stubs.

For this v0 the firmware uses the older nRF5 SDK17.1.0 / S1407.2.0 to reuse the
available Arm toolchain and bare-metal drivers. This is a conscious departure
from the earlier Zephyr recommendation; porting to nRF Connect SDK is a future
maintenance choice. Desktop protocol and recording code are independent of it.
Do not mistake successful compilation for RF, timing, sensor or power validation.

## GitHub preparation

Commit source/docs/tests/setup scripts. Do not commit .venv, vendor SDK copies,
real recordings, caches or intermediate object files. Publish tested HEX files
and manifest as versioned release artifacts. Choose your own source license
before public distribution; preserve Nordic's terms for Nordic components.
See THIRD_PARTY.md. No remote repository or release has been created.
