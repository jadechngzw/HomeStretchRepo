# Patient State Machine V0
# States: IDLE_PRE, EXERCISING, PAUSED, IDLE_POST

from live_guidance import (
    check_ppg_signal,
    check_pulse_rate,
    check_session_complete,
    check_rep_timing,
    rep_goal,
    hr_active_max,
    ppg_coverage_min,
)

# States
IDLE_PRE   = "IDLE_PRE"
EXERCISING = "EXERCISING"
PAUSED     = "PAUSED"
IDLE_POST  = "IDLE_POST"

ATYPICAL_THRESHOLD = 0.4  # pause if > 40% of reps are atypical

# State Machine Class
class PatientStateMachine:
    def __init__(self):
        self.state = IDLE_PRE
        self.pause_reason = None
        self.atypical_flags = []

    def transition(self, new_state, reason=None):
        print(f"\n  [STATE] {self.state} → {new_state}" + (f" ({reason})" if reason else ""))
        self.state = new_state
        if reason:
            self.pause_reason = reason

    def update(self, imu, hr):
        accepted_reps = imu.get("accepted_reps", 0)
        atypical_reps = imu.get("atypical_reps", 0)
        coverage = hr.get("valid_signal_coverage_pct", 100.0)
        peak_hr = hr.get("peak_hr_bpm", 0)

        atypical_ratio = atypical_reps / accepted_reps if accepted_reps > 0 else 0

        # IDLE_PRE → EXERCISING
        if self.state == IDLE_PRE:
            if accepted_reps > 0:
                self.transition(EXERCISING, "First rep detected")

        # EXERCISING
        elif self.state == EXERCISING:
            if coverage < ppg_coverage_min:
                self.transition(PAUSED, f"PPG signal too low ({coverage}%)")
            elif peak_hr > hr_active_max:
                self.transition(PAUSED, f"HR too high ({peak_hr} bpm)")
            elif atypical_ratio > ATYPICAL_THRESHOLD:
                self.atypical_flags.append(f"Atypical ratio exceeded threshold ({atypical_reps}/{accepted_reps} reps)")
                self.transition(PAUSED, f"Atypical rep ratio too high ({atypical_reps}/{accepted_reps})")
            elif accepted_reps >= rep_goal:
                self.transition(IDLE_POST, "Rep goal met")

        # PAUSED
        elif self.state == PAUSED:
            atypical_ok = atypical_ratio <= ATYPICAL_THRESHOLD
            hr_ok = peak_hr <= hr_active_max
            ppg_ok = coverage >= ppg_coverage_min

            if atypical_ok and hr_ok and ppg_ok:
                self.transition(EXERCISING, "All conditions cleared")
            else:
                print(f"  [PAUSED] Waiting: {self.pause_reason}")

        # IDLE_POST
        elif self.state == IDLE_POST:
            print("\n  [SESSION COMPLETE]")
            for line in check_session_complete(imu):
                print(f"  {line}")
            for line in check_rep_timing(imu["rep_durations"]):
                print(f"  {line}")
            for line in check_pulse_rate(hr):
                print(f"  {line}")
            for line in check_ppg_signal(hr):
                print(f"  {line}")
            if self.atypical_flags:
                print("\n  Atypical Rep Flags:")
                for flag in self.atypical_flags:
                    print(f"  ⚠️  {flag}")

    def print_state(self):
        print(f"\n Current Patient State: {self.state}")
        if self.atypical_flags:
            print("Atypical Flags:")
            for flag in self.atypical_flags:
                print(f"  {flag}")


# Main
if __name__ == "__main__":
    from scoring import read_imu_data, read_hr_data, FILEPATH, PPG_FILE

    imu = read_imu_data(FILEPATH)
    hr = read_hr_data(PPG_FILE)

    sm = PatientStateMachine()

    print("\n Running State Machine")

    sm.update(imu, hr)
    sm.update(imu, hr)
    sm.update(imu, hr)

    sm.print_state()


def run_tests():
    print("\n TESTING STATE MACHINE\n")

    # Test 1: Normal session — IDLE_PRE → EXERCISING → IDLE_POST
    print("Test 1: Normal session")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 0, "atypical_reps": 0, "rep_durations": []}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 5, "atypical_reps": 0, "rep_durations": [1.2, 1.5]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 10, "atypical_reps": 0, "rep_durations": [1.2, 1.5]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.print_state()

    # Test 2: PPG drops — EXERCISING → PAUSED → EXERCISING
    print("\nTest 2: PPG signal drop and recovery")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 3, "atypical_reps": 0, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 60.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 3, "atypical_reps": 0, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 60.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 3, "atypical_reps": 0, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.print_state()

    # Test 3: HR spike — EXERCISING → PAUSED
    print("\nTest 3: HR spike")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 3, "atypical_reps": 0, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 180, "bpm": 100})
    sm.update({"accepted_reps": 3, "atypical_reps": 0, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 180, "bpm": 100})
    sm.print_state()

    # Test 4: Atypical ratio > 40% — EXERCISING → PAUSED
    print("\nTest 4: High atypical ratio")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 5, "atypical_reps": 3, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 5, "atypical_reps": 1, "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.print_state()
