import streamlit as st
import numpy as np
import pandas as pd

st.title("Weekly Progress")

# -----------------------
# SAMPLE DATA
# -----------------------
days = ["Sun", "Mon", "Tues", "Wed", "Thurs", "Fri", "Sat"]

completion_percent = [23, 78, 62, 56, 66, 42, 62]

session_completion = [0.7, 0.5, 0.6, 0.7, 0.55, 0.4, 0.45]

active_patients = 8
inactive_patients = 4

avg_difficulty = 3.8
difficulty_change = -0.4

# -----------------------
# LAYOUT
# -----------------------
col_left, col_right = st.columns([2, 1])

# =======================
# LEFT: BAR CHART
# =======================
with col_left:

    st.markdown("### % of Active Patients Completing Sessions per Day")

    df_bar = pd.DataFrame({
        "Day": days,
        "Completion %": completion_percent
    })

    st.bar_chart(df_bar.set_index("Day"))

# =======================
# RIGHT SIDE
# =======================
with col_right:

    # ---- Activity Card ----
    st.markdown("### Activity This Week")

    c1, c2 = st.columns(2)
    c1.metric("Active Patients", active_patients)
    c2.metric("Non-Active Patients", inactive_patients)

    st.divider()

    # ---- Difficulty Card ----
    st.markdown("### Average Reported Difficulty")

    st.metric(
        label="",
        value=f"{avg_difficulty} / 10",
        delta=f"{difficulty_change} from last week"
    )

# -----------------------
# FULL WIDTH: LINE CHART
# -----------------------
st.markdown("### Average Session Completion Rate")

df_line = pd.DataFrame({
    "Day": days,
    "Rate": session_completion
})

st.line_chart(df_line.set_index("Day"))