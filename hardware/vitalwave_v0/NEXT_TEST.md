# Test the September 25 update

The code is built and tested with a simulated watch. These are the remaining
physical checks; flashing has not been performed automatically.

1. Close the old app. Keep charging disconnected for this initial sensor test.
2. Connect J-Link as before: NRF52840_XXAA, SWD, 100 kHz. Run:

```
loadfile "/Users/jadechng/Documents/ChatGPT/VITALWAVE/vitalwave_v0/firmware/build/vitalwave_v0.hex"
r
g
```

3. Launch `Launch.command`, Scan and Connect. Both app and watch must use the
   new protocol version 3. If connection reports incompatible firmware, verify
   the HEX path and restart the watch and app.
4. Choose accelerometer, gyro and temperature/humidity; uncheck PPG enabled.
   Record for 30 seconds, then Stop, then Save as. Check complete metadata.
5. Select Red + IR (50 Hz each), then test all four colours + IMU 50 Hz + Temp/RH
   2 Hz. Keep contact steady for 60 seconds. Scroll to the optical plots. Toggle
   individual display plots; this must not change recorded streams.
6. Stop, Save as, Process PPG. Expect raw/filtered plots and preliminary HR only
   where quality passes. No calibrated SpO₂ percentage is available.
7. Test Button 1 Start/Stop and Button 2 marker. Confirm marker metadata.
8. Test an intentional disconnect in a separate recording; expect incomplete
   recovery data and acquisition to stop. Reconnect must not resume automatically.
9. After normal boot, check charger plug/unplug status while idle. The 240 mA
   policy remains unchanged. No battery percentage sensing exists on this PCB.

If it stops unexpectedly, retain the CSV/JSON and logs/app.log (logs/crash.log
for a process crash). Check reason, invalid_by_sensor, generated/dropped counts
and sequence gaps. Filtering removes slow baseline variation, not physical
motion corruption or sensor clock drift. Hardware stability is not yet verified
for this firmware build.
