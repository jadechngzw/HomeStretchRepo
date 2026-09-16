# Version 0 - Rule Based Logic (Skeleton)
import random

# Thresholds
rep_goal = 10
snr_threhold = 15
smoothness_threshold = 0.7
hr_rest_max = 100
hr_active_max = 160


# Reading IMU Data
def read_imu_data():
    return {
        "num_reps": random.randint(5, 15),
        "snr_db": round(random.uniform(10, 25), 2),
        "smoothness": round(random.uniform(0.4, 1.0), 2),
        "classification": random.choice(["Typical", "Atypical"]),
        "duration": random.randint(20, 90)
    }


# HR Data
def read_hr_data():
    return {
        "hr_rest": random.randint(55, 110),
        "hr_active": random.randint(90, 180)
    }


# Patient State
def infer_patient_state(imu, hr):
    flags = []
    score = 0

    if imu["num_reps"] >= rep_goal:
        flags.append("Rep Goal Met")
    else:
        flags.append("Rep Goal Not Met")
        score += 1

    if imu["snr_db"] < snr_threhold:
        flags.append("Low SNR")
        score += 1
    else:
        flags.append("Good Signal Quality")

    if imu["smoothness"] < smoothness_threshold or imu["classification"] == "Atypical":
        flags.append("Movement Quality Issue")
        score += 1
    else:
        flags.append("Good Movement Quality")

    if hr["hr_rest"] > hr_rest_max:
        flags.append("Elevated Resting HR")
        score += 1
    else:
        flags.append("Normal Resting HR")

    if hr["hr_active"] > hr_active_max:
        flags.append("Elevated Active HR")
        score += 1
    else:
        flags.append("Normal Active HR")

    # Final Scoring
    if score == 0:
        patient_state = "Good"
    elif score <= 2:
        patient_state = "Moderate"
    else:
        patient_state = "Concern - Flagging your caretaker for review"

    return patient_state, flags

# Main
if __name__ == "__main__":
    imu = read_imu_data()
    hr = read_hr_data()
    patient_state, flags = infer_patient_state(imu, hr)

    print("\n── Patient Session Summary ──────────────────")
    print(f"  Reps:         {imu['num_reps']}")
    print(f"  Duration:     {imu['duration']} sec")
    print(f"  SNR:          {imu['snr_db']} dB")
    print(f"  Smoothness:   {imu['smoothness']}")
    print(f"  Motion:       {imu['classification']}")
    print(f"  Resting HR:   {hr['hr_rest']} bpm")
    print(f"  Active HR:    {hr['hr_active']} bpm")
    print(f"\n── Patient State: {patient_state}")
    print("\n── Flags:")
    for f in flags:
        print(f"   {f}")
    print("─────────────────────────────────────────────\n")