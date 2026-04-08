import streamlit as st
import pandas as pd
import numpy as np
from numpy.random import default_rng
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

st.set_page_config(layout="wide")

# -----------------------
# FIRESTORE SETUP
# -----------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("homestretch-pipeline-5f8f03e61254.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -----------------------
# GET SESSION DATA
# -----------------------
def get_all_sessions():
    docs = db.collection("sessions").stream()

    sessions = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id

        # Real Firestore timestamp
        d["session_time"] = doc.create_time if hasattr(doc, "create_time") else None

        sessions.append(d)

    # newest first
    sessions = sorted(
        sessions,
        key=lambda x: x["session_time"] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True
    )

    return sessions


def get_latest_session():
    sessions = get_all_sessions()
    return sessions[0] if sessions else None


def format_session_time(ts):
    if ts is None:
        return "Time unavailable"
    return ts.astimezone().strftime("%b %d, %I:%M %p")


def render_session_metrics(session):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reps", session.get("num_reps", "N/A"))
    m2.metric("Duration", f"{round(session.get('duration_sec', 0), 1)} sec")
    m3.metric("SNR", f"{round(session.get('snr_db', 0), 1)} dB")
    m4.metric("Tremor", session.get("tremor_level", "N/A"))

    if session.get("classification") == "Very Smooth":
        st.success("Movement Quality: Very Smooth")
    elif session.get("classification") == "Good Control":
        st.success("Movement Quality: Good Control")
    else:
        st.warning(f"Movement Quality: {session.get('classification', 'Unknown')}")

    st.markdown("### Tremor Ratio")
    st.progress(float(session.get("tremor_ratio", 0.0)))
    st.caption(f"{round(session.get('tremor_ratio', 0.0), 4)}")

    st.markdown("### Session Details")
    st.write(f"Duration: {round(session.get('duration_sec', 0), 1)} seconds")
    st.write(f"Reps: {session.get('num_reps', 'N/A')}")
    st.write(f"Signal Quality: {round(session.get('snr_db', 0), 1)} dB")
    st.write(f"Classification: {session.get('classification', 'Unknown')}")
    st.write(f"Tremor Level: {session.get('tremor_level', 'Unknown')}")

    # New ML fields - only show if present
    if "num_typical" in session or "num_atypical" in session:
        st.markdown("### Repetition Quality")
        c1, c2, c3 = st.columns(3)
        c1.metric("Typical Reps", session.get("num_typical", "N/A"))
        c2.metric("Atypical Reps", session.get("num_atypical", "N/A"))

        atypical_ids = session.get("atypical_rep_ids", [])
        if atypical_ids is None:
            atypical_ids = []
        c3.metric("Atypical IDs Count", len(atypical_ids))

        st.write(f"Atypical Rep IDs: {atypical_ids if atypical_ids else 'None'}")

    # Placeholder signal until real waveform is connected
    signal = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    st.markdown("### Movement Signal")
    st.line_chart(signal)


# -----------------------
# SESSION STATE
# -----------------------
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

if "selected_session_data" not in st.session_state:
    st.session_state.selected_session_data = None

if "selected_session_time" not in st.session_state:
    st.session_state.selected_session_time = None

if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

if "page" not in st.session_state:
    st.session_state.page = "patients"

if "program" not in st.session_state:
    st.session_state.program = []

rng = default_rng()

st.title("Patients")

# -----------------------
# FAKE PATIENT TABLE DATA
# -----------------------
n = 20

ages = rng.integers(35, 80, n)
statuses = rng.choice(
    ["Active", "Needs Review", "Inactive"],
    size=n,
    p=[0.6, 0.3, 0.1]
)
last_activity = rng.choice(
    ["Today", "1 day ago", "3 days ago", "5 days ago", "10 days ago"],
    size=n
)
compliance = rng.integers(30, 100, n)
notes_options = [
    "Reported difficulty, decrease in activity",
    "Fatigue reported",
    "Improving steadily",
    "",
    "Balance issues noted"
]
notes = rng.choice(notes_options, size=n)

df = pd.DataFrame({
    "Patient": [f"Patient {i+1}, {ages[i]}" for i in range(n)],
    "Status": statuses,
    "Last Activity": last_activity,
    "Compliance": compliance,
    "Notes": notes
})

# -----------------------
# HELPER: STATUS COLORS
# -----------------------
def render_status(status):
    if status == "Active":
        color = "#b7e4c7"
    elif status == "Needs Review":
        color = "#ffe066"
    else:
        color = "#ff6b6b"

    st.markdown(
        f"""
        <div style="
            background-color: {color};
            padding: 5px 10px;
            border-radius: 10px;
            text-align: center;
            font-size: 12px;
            width: fit-content;">
            {status}
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------
# MAIN LOGIC
# -----------------------
if st.session_state.page == "patients":

    if st.session_state.selected_patient is None:

        st.subheader("Patient List")

        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 2, 2, 1])
        col1.write("**Patient**")
        col2.write("**Status**")
        col3.write("**Last Activity**")
        col4.write("**Compliance**")
        col5.write("**Notes**")

        st.divider()

        for i, row in df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 2, 2, 1])

            col1.write(row["Patient"])

            with col2:
                render_status(row["Status"])

            col3.write(row["Last Activity"])

            with col4:
                st.progress(row["Compliance"] / 100)
                st.caption(f"{row['Compliance']}%")

            col5.write(row["Notes"])

            if col6.button("View", key=f"btn_{i}"):
                st.session_state.selected_patient = row["Patient"]

    else:
        patient = st.session_state.selected_patient

        col1, col2 = st.columns([1, 5])

        with col1:
            st.image("person.jpg", width="content")

        with col2:
            st.subheader(patient)
            st.caption("Left-side weakness")
            st.caption("Started HomeStretch: Jan 2026")
            st.markdown("""
            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;margin-right:5px;'>Stroke</span>
            <span style='background:#ffe066;padding:5px 10px;border-radius:10px;margin-right:5px;'>High Fall Risk</span>
            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;'>Uses Cane</span>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background:#e9f2fb;padding:10px;border-radius:10px;margin-top:10px;'>
            Home Activity: Stable &nbsp;&nbsp; • &nbsp;&nbsp; Adherence: Moderate &nbsp;&nbsp; • &nbsp;&nbsp; Last Active: Today
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        tab1, tab2, tab3 = st.tabs(["Information", "Session", "Latest Session"])

        # -----------------------
        # INFORMATION TAB
        # -----------------------
        with tab1:
            colA, colB = st.columns(2)

            with colA:
                st.markdown("### Clinical Overview")
                st.markdown("""
                **Stroke Type**  
                Ischemic Stroke  

                **Assistive Devices**  
                Cane, Walker, AFO  

                **Date of Stroke**  
                Aug 20, 2025  

                **Living Situation**  
                With caregiver  
                Stairs at home  
                """)

            with colB:
                st.markdown("### Current Program")
                st.markdown("""
                **Frequency**  
                3 sessions / week  

                **Session Duration**  
                ~28 min  

                **Exercises**  
                6  

                **Last Update**  
                Jan 18, 2026  
                """)

                if st.button("Program Builder"):
                    st.session_state.page = "builder"

            colC, colD = st.columns(2)

            with colC:
                st.markdown("### Functional Baseline")
                st.markdown("""
                **Gait**  
                Independent (Supervision outdoors)  

                **Upper Limb**  
                Limited (fine motor control)  
                """)

            with colD:
                st.markdown("### ")
                st.markdown("""
                **Sit to Stand**  
                8 reps, Unassisted  

                **Balance Confidence**  
                Moderate  
                """)

            st.markdown("### Notes")
            st.info("""
            **Last entry – Feb 7**  
            Improved weight shifting.  
            Still fatigues quickly.
            """)

            colN1, colN2 = st.columns(2)
            colN1.button("View All Notes")
            colN2.button("Add Note")

        # -----------------------
        # SESSION TAB
        # -----------------------
        with tab2:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Engagement Insights")
                st.markdown("""
                • Tends to skip weekends  
                • Completes better in mornings  
                • Increased difficulty this week  
                """)

                st.markdown("### Session Overview")

                sessions = get_all_sessions()

                if len(sessions) == 0:
                    st.info("No session data available yet")
                else:
                    reps = [s.get("num_reps", 0) for s in sessions]
                    duration = [s.get("duration_sec", 0) for s in sessions]

                    chart_df = pd.DataFrame({
                        "Session": [f"S{i+1}" for i in range(len(sessions))],
                        "Reps": reps,
                        "Duration": duration
                    })

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Avg Reps", round(np.mean(reps), 1))
                    m2.metric("Avg Duration", f"{round(np.mean(duration),1)} sec")
                    m3.metric("Best Session", max(reps))

                    st.divider()

                    a, b = st.columns(2)

                    with a:
                        st.markdown("#### Reps per Session")
                        st.bar_chart(chart_df.set_index("Session")["Reps"])

                    with b:
                        st.markdown("#### Duration Trend")
                        st.line_chart(chart_df.set_index("Session")["Duration"])

            with col2:
                sessions = get_all_sessions()

                st.markdown("### Timeline")

                for i, s in enumerate(sessions):
                    time_str = format_session_time(s.get("session_time"))

                    label = (
                        f"{time_str} | "
                        f"{s.get('num_reps', 'N/A')} reps | "
                        f"{round(s.get('duration_sec', 0), 1)} sec | "
                        f"{s.get('classification', 'Unknown')} | "
                        f"Tremor: {s.get('tremor_level', 'Unknown')}"
                    )

                    if st.button(label, key=f"session_{i}"):
                        st.session_state.selected_session = s["id"]
                        st.session_state.selected_session_data = s
                        st.session_state.selected_session_time = time_str
                        st.session_state.page = "session_detail"

        st.divider()

        with tab3:
            latest = get_latest_session()

            if latest is None:
                st.info("No session data available yet")
            else:
                st.markdown("### Latest Session")
                st.caption(format_session_time(latest.get("session_time")))
                render_session_metrics(latest)

        if st.button("⬅ Back to Patients"):
            st.session_state.selected_patient = None

# -----------------------
# PROGRAM BUILDER
# -----------------------
elif st.session_state.page == "builder":

    st.title("Program Builder")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.subheader("Exercise Library")

        exercises = [
            "Shoulder Rolls",
            "Sit-to-Stand",
            "Heel Raises",
            "Weight Shifts"
        ]

        for ex in exercises:
            if st.button(f"➕ {ex}"):
                st.session_state.program.append({
                    "name": ex,
                    "sets": 3,
                    "reps": "8-10"
                })

    with col2:
        st.subheader("My Exercise Plan")

        for i, ex in enumerate(st.session_state.program):
            st.write(f"### {ex['name']}")

            c1, c2, c3 = st.columns(3)

            ex["sets"] = c1.number_input("Sets", 1, 10, ex["sets"], key=f"s_{i}")
            ex["reps"] = c2.text_input("Reps", ex["reps"], key=f"r_{i}")

            if c3.button("❌", key=f"del_{i}"):
                st.session_state.program.pop(i)
                st.rerun()

            st.divider()

    with col3:
        st.subheader("Schedule")

        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
            st.checkbox(day)

        st.text_area("Notes")

    st.divider()

    if st.button("⬅ Back to Patient Profile"):
        st.session_state.page = "patients"

# -----------------------
# SESSION DETAIL PAGE
# -----------------------
elif st.session_state.page == "session_detail":

    session_data = st.session_state.selected_session_data

    st.header("Session Details")

    if st.session_state.selected_session_time:
        st.subheader(st.session_state.selected_session_time)

    if st.button("⬅ Back to Patient Profile"):
        st.session_state.page = "patients"

    if session_data is None:
        st.info("No session selected.")
    else:
        render_session_metrics(session_data)