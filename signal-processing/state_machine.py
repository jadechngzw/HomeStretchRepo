# Patient State Machine V0
# States: IDLE_PRE, EXERCISING, PAUSED, ERROR, IDLE_POST

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
IDLE_PRE    = "IDLE_PRE"
EXERCISING  = "EXERCISING"
PAUSED      = "PAUSED"
ERROR       = "ERROR"
IDLE_POST   = "IDLE_POST"

# State Machine Class
class PatientStateMachine:
    def __init__(self):
        self.state = IDLE_PRE
        self.rep_count = 0
        self.error_log = []
        self.pause_reason = None

    def transition(self, new_state, reason=None):
        print(f"\n  [STATE] {self.state} → {new_state}" + (f" ({reason})" if reason else ""))
        self.state = new_state
        if reason:
            self.pause_reason = reason

    # Evaluate current state given imu and hr snapshots
    def update(self, imu, hr):
        classification = imu.get("classification", "Unknown")
        accepted_reps = imu.get("accepted_reps", 0)
        coverage = hr.get("valid_signal_coverage_pct", 100.0)
        peak_hr = hr.get("peak_hr_bpm", 0)

        # IDLE_PRE → EXERCISING
        if self.state == IDLE_PRE:
            if accepted_reps > 0:
                self.transition(EXERCISING, "First rep detected")

        # EXERCISING
        elif self.state == EXERCISING:

            # Check pause conditions first
            if coverage < ppg_coverage_min:
                self.transition(PAUSED, f"PPG signal too low ({coverage}%)")
            elif peak_hr > hr_active_max:
                self.transition(PAUSED, f"HR too high ({peak_hr} bpm)")

            # Check for atypical rep
            elif classification == "Atypical":
                self.error_log.append(f"Atypical rep detected at rep {accepted_reps}")
                self.transition(ERROR, "Atypical rep detected")

            # Check session complete
            elif accepted_reps >= rep_goal:
                self.transition(IDLE_POST, "Rep goal met")

        # PAUSED
        elif self.state == PAUSED:
            if coverage >= ppg_coverage_min and peak_hr <= hr_active_max:
                self.transition(EXERCISING, "Signal and HR recovered")
            else:
                print(f"  [PAUSED] Waiting: {self.pause_reason}")

        # ERROR
        elif self.state == ERROR:
            if accepted_reps >= rep_goal:
                self.transition(IDLE_POST, "Rep goal met despite Atypical rep")
            elif classification == "Typical":
                self.transition(EXERCISING, "Typical rep resumed")
            else:
                print(f"  [ERROR] Logged: {self.error_log[-1]}")

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

    def print_state(self):
        print(f"\n Current Patient State: {self.state}")
        if self.error_log:
            print("Error Log:")
            for entry in self.error_log:
                print(f"  {entry}")


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

# Example test cases
"""
def run_tests():
    print("\n TESTING STATE MACHINE\n")

    # Test 1: Normal session — should go IDLE_PRE → EXERCISING → IDLE_POST
    print("Test 1: Normal session")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 0, "classification": "Typical", "rep_durations": []}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 5, "classification": "Typical", "rep_durations": [1.2, 1.5]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 10, "classification": "Typical", "rep_durations": [1.2, 1.5]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.print_state()

    # Test 2: PPG drops — should go EXERCISING → PAUSED → EXERCISING
    print("\nTest 2: PPG signal drop and recovery")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 3, "classification": "Typical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 60.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 3, "classification": "Typical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 60.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 3, "classification": "Typical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.print_state()

    # Test 3: HR spike — should go EXERCISING → PAUSED
    print("\nTest 3: HR spike")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 3, "classification": "Typical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 180, "bpm": 100})
    sm.update({"accepted_reps": 3, "classification": "Typical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 180, "bpm": 100})
    sm.print_state()

    # Test 4: Atypical rep — should go EXERCISING → ERROR → EXERCISING
    print("\nTest 4: Atypical rep recovery")
    sm = PatientStateMachine()
    sm.update({"accepted_reps": 3, "classification": "Atypical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.update({"accepted_reps": 4, "classification": "Typical", "rep_durations": [1.2]}, {"valid_signal_coverage_pct": 80.0, "peak_hr_bpm": 120, "bpm": 100})
    sm.print_state()

if __name__ == "__main__":
    run_tests()
"""