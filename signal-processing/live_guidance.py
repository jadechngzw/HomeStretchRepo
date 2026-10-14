# Live Session Guidance - V0

# Thresholds
rep_goal = 10
min_rep_duration = 0.8      # sec — faster than this is too quick
max_rep_duration = 3.0      # sec — slower than this is too slow
hr_active_max = 160         # bpm — exertion ceiling
hr_valid_min = 50           # bpm — below this the pulse reading is suspect
ppg_coverage_min = 70.0     # % — below this pause the set
majority_threshold = 0.5    # 50% of reps must cross threshold to trigger feedback

def check_rep_timing(rep_durations):
    """
    Evaluate rep timing across the whole set.
    Only flags if the majority of reps cross the threshold.
    """
    if not rep_durations:
        return ["No reps detected"]

    total = len(rep_durations)
    too_fast = sum(1 for d in rep_durations if d < min_rep_duration)
    too_slow = sum(1 for d in rep_durations if d > max_rep_duration)

    if too_fast / total > majority_threshold:
        return [f"Most reps were too fast — try to slow down and control each rep"]
    elif too_slow / total > majority_threshold:
        return [f"Most reps were too slow — try to maintain a steady pace"]
    else:
        return [f"Rep timing looks good across the set"]


def check_pulse_rate(hr):
    """
    Flag if HR at any point exceeded the active max or dropped below valid min.
    """
    feedback = []

    if hr["bpm"] < hr_valid_min:
        feedback.append(f"Pulse rate too low ({hr['bpm']} bpm) — reading may be invalid")

    if hr["peak_hr_bpm"] > hr_active_max:
        feedback.append(f"HR exceeded exertion limit at some point during the set (peak: {hr['peak_hr_bpm']} bpm) — consider a lower intensity")

    if not feedback:
        feedback.append(f"HR stayed within safe range (avg: {hr['bpm']} bpm, peak: {hr['peak_hr_bpm']} bpm)")

    return feedback


def check_ppg_signal(hr):
    """
    Continuously monitor PPG signal quality.
    If coverage drops below threshold, pause the set.
    """
    coverage = hr.get("valid_signal_coverage_pct", 100.0)

    if coverage < ppg_coverage_min:
        return [f"SET PAUSED — PPG signal too low ({coverage}% coverage). Adjust sensor and resume when ready."]
    else:
        return [f"PPG signal stable ({coverage}% coverage)"]


def check_session_complete(imu):
    """
    Check if prescribed rep goal has been met.
    """
    completed = imu["accepted_reps"]

    if completed >= rep_goal:
        return [f"Session complete! {completed}/{rep_goal} reps done — great work!"]
    else:
        remaining = rep_goal - completed
        return [f"  {completed}/{rep_goal} reps done — {remaining} remaining"]


def run_live_guidance(imu, hr):
    print("\nLive Session Guidance")

    print("\n  Rep Timing:")
    for line in check_rep_timing(imu["rep_durations"]):
        print(line)

    print("\n  Pulse Rate:")
    for line in check_pulse_rate(hr):
        print(line)

    print("\n  PPG Signal:")
    for line in check_ppg_signal(hr):
        print(line)

    print("\n  Session Progress:")
    for line in check_session_complete(imu):
        print(line)