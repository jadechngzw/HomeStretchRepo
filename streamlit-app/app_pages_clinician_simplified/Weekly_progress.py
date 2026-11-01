import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _data import get_data


st.title("Weekly Progress")

# Existing weekly demo data and charts are kept as they were.
days = ["Sun", "Mon", "Tues", "Wed", "Thurs", "Fri", "Sat"]
completion_percent = [23, 78, 62, 56, 66, 42, 62]
session_completion = [0.7, 0.5, 0.6, 0.7, 0.55, 0.4, 0.45]
active_patients = 8
inactive_patients = 4
avg_difficulty = 3.8
difficulty_change = -0.4

col_left, col_right = st.columns([2, 1])
with col_left:
    st.markdown("### % of Active Patients Completing Sessions per Day")
    df_bar = pd.DataFrame({"Day": days, "Completion %": completion_percent})
    st.bar_chart(df_bar.set_index("Day"))

with col_right:
    st.markdown("### Activity This Week")
    c1, c2 = st.columns(2)
    c1.metric("Active Patients", active_patients)
    c2.metric("Non-Active Patients", inactive_patients)
    st.divider()
    st.markdown("### Average Reported Difficulty")
    st.metric(
        label="",
        value=f"{avg_difficulty} / 10",
        delta=f"{difficulty_change} from last week",
    )

st.markdown("### Average Session Completion Rate")
df_line = pd.DataFrame({"Day": days, "Rate": session_completion})
st.line_chart(df_line.set_index("Day"))

# Use the patient names already shown on the Patients tab, and make a sample
# daily split that follows the completion percentages in the chart above.
st.divider()
st.markdown("### Active and non-active patients by day")
st.caption("Sample patient assignments follow the daily completion percentages shown above.")

roster_data = get_data()
if roster_data is None:
    st.info("Upload the HomeStretch workbook to display patient names in this table.")
else:
    roster, _ = roster_data
    patients = [
        (int(row["Participant ID"]), str(row["Participant"]))
        for _, row in roster.sort_values("Participant ID").iterrows()
    ]
    if not patients:
        st.info("No patients are listed in the HomeStretch workbook.")
    else:
        patient_count = len(patients)
        table_rows = []
        for day_index, (day, completion_rate) in enumerate(zip(days, completion_percent)):
            active_count = round(patient_count * completion_rate / 100)
            # Rotate the active group by day so the mock schedule varies through the week.
            start = (day_index * max(1, active_count // 2)) % patient_count
            active_indices = {
                (start + offset) % patient_count for offset in range(active_count)
            }
            active_names = [
                f"{patients[index][1]} (ID {patients[index][0]})"
                for index in sorted(active_indices)
            ]
            inactive_names = [
                f"{name} (ID {patient_id})"
                for index, (patient_id, name) in enumerate(patients)
                if index not in active_indices
            ]
            table_rows.append({
                "Day": day,
                "Completion %": f"{completion_rate}%",
                "Active patients": ", ".join(active_names) or "None",
                "Non-active patients": ", ".join(inactive_names) or "None",
            })

        st.dataframe(
            pd.DataFrame(table_rows),
            hide_index=True,
            use_container_width=True,
        )
