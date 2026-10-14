import time
import numpy as np
import pandas as pd
import streamlit as st
from numpy.random import default_rng

rng = default_rng()

st.title("Readiness")

# -----------------------------------------------------------
# Session state
# -----------------------------------------------------------
if "calibration_done" not in st.session_state:
    st.session_state.calibration_done = False

if "pre_hr" not in st.session_state:
    st.session_state.pre_hr = None

if "signal_quality" not in st.session_state:
    st.session_state.signal_quality = None


# -----------------------------------------------------------
# Fake data generators
# (swap these out for real wearable / DB pulls later)
# -----------------------------------------------------------
def generate_hr_trend(days=7):
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days)
    resting_hr = rng.integers(58, 72, days)
    return pd.DataFrame({"Date": dates, "Resting HR": resting_hr}).set_index("Date")


def generate_session_hr_zones():
    return {
        "Warmup": int(rng.integers(60, 90)),
        "Aerobic": int(rng.integers(90, 130)),
        "Max": int(rng.integers(130, 165)),
    }


def generate_previous_day_workload():
    return {
        "Total Active Reps": int(rng.integers(20, 80)),
        "Section Duration (min)": int(rng.integers(10, 35)),
        "Atypical Rep %": round(float(rng.uniform(0, 20)), 1),
    }


def generate_post_exercise_survey():
    soreness = int(rng.integers(1, 6))
    sleep_quality = int(rng.integers(1, 6))
    fatigue = int(rng.integers(1, 6))
    return soreness, sleep_quality, fatigue


# -----------------------------------------------------------
# Readiness scoring logic
# -----------------------------------------------------------
def compute_readiness(hr_deviation, atypical_pct, fatigue_score):
    """
    Simple rule-based traffic light.
    Red    -> clear signs of overload / fatigue
    Yellow -> borderline, proceed with caution
    Green  -> normal, cleared for today's session
    """
    if hr_deviation >= 7 or atypical_pct > 15 or fatigue_score >= 4:
        return "red"
    elif hr_deviation >= 5 or atypical_pct > 8 or fatigue_score == 3:
        return "yellow"
    else:
        return "green"


def render_light(status):
    colors = {"green": "#b7e4c7", "yellow": "#ffe066", "red": "#ff6b6b"}
    labels = {
        "green": "✅ Good to go! Please exercise as planned",
        "yellow": "⚠️ Please proceed with caution — consider a lighter session",
        "red": "🛑 Rest recommended today",
    }
    st.markdown(
        f"""
        <div style="
            background-color:{colors[status]};
            padding:18px;
            border-radius:12px;
            text-align:center;
            font-size:18px;
            font-weight:600;">
            {labels[status]}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------
# Tabs
# -----------------------------------------------------------
tab1, tab2 = st.tabs(["Biometrics & Heart Rate", "Readiness & Recommendation"])

# =============================================================
# TAB 1 — Biometrics & Heart Rate
# =============================================================
with tab1:
    st.markdown("### Pre-Exercise Calibration")
    st.caption(
        "Sit comfortably and stay still for 1–2 minutes while your wearable syncs. "
        "This captures your pre-exercise baseline heart rate and signal quality."
    )

    if not st.session_state.calibration_done:
        if st.button("Start Calibration", type="primary"):
            with st.spinner("Syncing device and capturing baseline heart rate..."):
                time.sleep(1.5)
            st.session_state.pre_hr = int(rng.integers(58, 78))
            st.session_state.signal_quality = str(
                rng.choice(["Excellent", "Good", "Fair"], p=[0.5, 0.35, 0.15])
            )
            st.session_state.calibration_done = True
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        c1.metric("Pre-Exercise Baseline HR", f"{st.session_state.pre_hr} bpm")
        c2.metric("Signal Quality", st.session_state.signal_quality)

        if st.button("Recalibrate"):
            st.session_state.calibration_done = False
            st.rerun()

    st.divider()

    st.markdown("### Resting HR Trend (7-day)")
    hr_df = generate_hr_trend()
    st.line_chart(hr_df)

    st.markdown("### Session HR Zone Breakdown")
    zones = generate_session_hr_zones()
    z1, z2, z3 = st.columns(3)
    z1.metric("Warmup", f"{zones['Warmup']} bpm")
    z2.metric("Aerobic", f"{zones['Aerobic']} bpm")
    z3.metric("Max", f"{zones['Max']} bpm")

# =============================================================
# TAB 2 — Readiness & Recommendation
# =============================================================
with tab2:
    st.markdown("### Daily Readiness Diagnostic")

    hr_df = generate_hr_trend()
    rolling_avg = float(hr_df["Resting HR"].mean())
    pre_hr = st.session_state.pre_hr if st.session_state.pre_hr else int(rng.integers(58, 78))
    deviation = pre_hr - rolling_avg

    if not st.session_state.calibration_done:
        st.info("Complete the pre-exercise calibration in the first tab for the most accurate reading.")

    c1, c2 = st.columns(2)
    c1.metric("Pre-Exercise Baseline HR", f"{pre_hr} bpm")
    c2.metric("7-Day Rolling Avg", f"{rolling_avg:.1f} bpm", delta=f"{deviation:+.1f} bpm")

    if deviation >= 5:
        st.warning(
            f"Elevated heart rate detected ({deviation:+.1f} bpm vs. baseline) — "
            "possible fatigue or stress."
        )
    else:
        st.success("Heart rate is within your normal range.")

    st.divider()

    st.markdown("### Previous Day Workload")
    workload = generate_previous_day_workload()
    w1, w2, w3 = st.columns(3)
    w1.metric("Total Active Reps", workload["Total Active Reps"])
    w2.metric("Section Duration", f"{workload['Section Duration (min)']} min")
    w3.metric("Atypical Rep %", f"{workload['Atypical Rep %']}%")

    st.divider()

    st.markdown("### Post-Exercise Survey (Yesterday)")
    soreness, sleep_quality, fatigue = generate_post_exercise_survey()
    s1, s2, s3 = st.columns(3)
    s1.metric("Soreness", f"{soreness}/5")
    s2.metric("Sleep Quality", f"{sleep_quality}/5")
    s3.metric("Fatigue", f"{fatigue}/5")

    st.divider()

    st.markdown("### Today's Recommendation")
    status = compute_readiness(deviation, workload["Atypical Rep %"], fatigue)
    render_light(status)
