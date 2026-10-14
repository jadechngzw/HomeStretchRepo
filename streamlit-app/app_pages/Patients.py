import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

st.set_page_config(layout="wide")

# =====================================================================
# CONFIG - adjust these if your paths / Firestore field names differ
# =====================================================================

# Replace with the path to your HomeStretch.xlsx file.
DATA_FILE = Path("C:/Users/TCO9.DSONE/HomeStretchRepo/Data.xlsx")

# Firestore field on each session doc that links it to a patient.
# ASSUMPTION - update if your schema uses a different field name.
# This should match the "Participant ID" values in the Excel file.
SESSION_PATIENT_FIELD = "participant_id"

# Firestore field holding a patient's reported pain score (0-10) on a
# session. ASSUMPTION - there is no pain data in the Excel file, so this
# is expected to come from Firestore like your other session metrics
# (num_reps, tremor_level, etc.). Update the field name if yours differs.
SESSION_PAIN_FIELD = "pain_level"
PAIN_ALERT_THRESHOLD = 8

# -----------------------
# FIRESTORE SETUP
# -----------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("homestretch-pipeline-5f8f03e61254.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()


# =====================================================================
# PATIENT ROSTER (from Excel) - replaces the old randomly-generated list
# =====================================================================
@st.cache_data
def load_patient_roster(path):
    """
    Reads the Typical / Atypical / Participant Identification sheets and
    builds one row per patient with their typical & atypical recording
    counts, matched by Participant ID.
    """
    xl = pd.ExcelFile(path)
    typical = xl.parse("Typical")
    atypical = xl.parse("Atypical")
    ids = xl.parse("Participant Identification")

    # the source sheet has trailing-space column names ("Exercize ", etc.)
    for d in (typical, atypical, ids):
        d.columns = [c.strip() for c in d.columns]

    ids["Participant"] = ids["Participant"].astype(str).str.strip()
    typical["Exercize"] = typical["Exercize"].astype(str).str.strip()
    atypical["Exercize"] = atypical["Exercize"].astype(str).str.strip()

    typical_counts = typical.groupby("Participant ID").size().rename("Typical Count")
    atypical_counts = atypical.groupby("Participant ID").size().rename("Atypical Count")

    roster = ids.set_index("Participant ID").join([typical_counts, atypical_counts])
    roster[["Typical Count", "Atypical Count"]] = (
        roster[["Typical Count", "Atypical Count"]].fillna(0).astype(int)
    )
    roster["Total Recordings"] = roster["Typical Count"] + roster["Atypical Count"]
    roster["Atypical %"] = np.where(
        roster["Total Recordings"] > 0,
        (roster["Atypical Count"] / roster["Total Recordings"] * 100).round(1),
        0.0,
    )
    roster["Typical %"] = (100 - roster["Atypical %"]).round(1)

    # which exercises each patient has recordings for
    all_rows = pd.concat(
        [typical[["Participant ID", "Exercize"]], atypical[["Participant ID", "Exercize"]]]
    )
    exercises = all_rows.groupby("Participant ID")["Exercize"].apply(
        lambda s: ", ".join(sorted(set(s)))
    )
    roster["Exercises"] = exercises

    # free-text notes attached to atypical recordings (e.g. "only the
    # last rep is atypical")
    if "Notes" in atypical.columns:
        notes_src = atypical.dropna(subset=["Notes"])
        notes = notes_src.groupby("Participant ID")["Notes"].apply(
            lambda s: "; ".join(s.astype(str))
        )
        roster["Notes"] = notes

    roster["Notes"] = roster.get("Notes", pd.Series(dtype=str)).fillna("")
    roster = roster.reset_index()  # Participant ID back to a column

    return roster, typical, atypical


def derive_status(row):
    """
    Placeholder status heuristic since the Excel file has no
    activity/adherence data: flags patients whose recorded reps were
    mostly atypical for review. Replace with real adherence logic once
    that data source is wired in.
    """
    if row["Total Recordings"] == 0:
        return "Inactive"
    elif row["Atypical %"] >= 30:
        return "Needs Review"
    else:
        return "Active"


try:
    roster_df, typical_df, atypical_df = load_patient_roster(DATA_FILE)
    roster_load_error = None
except Exception as e:
    roster_df = pd.DataFrame()
    typical_df = pd.DataFrame()
    atypical_df = pd.DataFrame()
    roster_load_error = str(e)


# =====================================================================
# SESSION DATA (Firestore) - now filterable per patient
# =====================================================================
def get_all_sessions(patient_id=None):
    query = db.collection("sessions")
    if patient_id is not None:
        query = query.where(SESSION_PATIENT_FIELD, "==", patient_id)
    docs = query.stream()

    sessions = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        d["session_time"] = doc.create_time if hasattr(doc, "create_time") else None
        sessions.append(d)

    # oldest first for numbering
    sessions = sorted(
        sessions,
        key=lambda x: x["session_time"] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    )

    for idx, s in enumerate(sessions, start=1):
        s["session_label"] = f"S{idx}"

    return sessions


def get_latest_session(patient_id=None):
    sessions = get_all_sessions(patient_id)
    return sessions[-1] if sessions else None


@st.cache_data(ttl=60)
def get_latest_pain(patient_id):
    """Most recent reported pain score (0-10) for this patient, or None
    if no sessions / no pain field recorded yet."""
    sessions = get_all_sessions(patient_id)
    if not sessions:
        return None
    latest = sessions[-1]  # get_all_sessions returns oldest -> newest
    return latest.get(SESSION_PAIN_FIELD)


def format_session_time(ts):
    if ts is None:
        return "Time unavailable"
    return ts.astimezone().strftime("%b %d, %I:%M %p")


def render_pain_flag(pain_value, inline=False):
    """Red flag shown when the latest reported pain is at/above threshold."""
    if pain_value is None:
        return
    if pain_value >= PAIN_ALERT_THRESHOLD:
        msg = f"🚩 Pain reported at {pain_value}/10 — contact patient"
        if inline:
            st.markdown(
                f"<span style='background:#ff6b6b;color:white;padding:3px 10px;"
                f"border-radius:10px;font-size:12px;'>{msg}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.error(msg)


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

    pain_value = session.get(SESSION_PAIN_FIELD)
    if pain_value is not None:
        st.markdown("### Pain")
        p1, p2 = st.columns([1, 3])
        p1.metric("Reported Pain", f"{pain_value}/10")
        with p2:
            render_pain_flag(pain_value)

    st.markdown("### Tremor Ratio")
    st.progress(float(session.get("tremor_ratio", 0.0)))
    st.caption(f"{round(session.get('tremor_ratio', 0.0), 4)}")

    st.markdown("### Session Details")
    st.write(f"Duration: {round(session.get('duration_sec', 0), 1)} seconds")
    st.write(f"Reps: {session.get('num_reps', 'N/A')}")
    st.write(f"Signal Quality: {round(session.get('snr_db', 0), 1)} dB")
    st.write(f"Classification: {session.get('classification', 'Unknown')}")
    st.write(f"Tremor Level: {session.get('tremor_level', 'Unknown')}")

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

    signal = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    st.markdown("### Movement Signal")
    st.line_chart(signal)


# -----------------------
# SESSION STATE
# -----------------------
for key, default in {
    "selected_session": None,
    "selected_session_data": None,
    "selected_session_time": None,
    "selected_patient": None,     # display name shown in the UI
    "selected_patient_id": None,  # real Participant ID from the Excel roster
    "page": "patients",
    "program": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("Patients")

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

        if roster_load_error:
            st.error(
                f"Couldn't load the patient roster from {DATA_FILE}:\n\n{roster_load_error}\n\n"
                "Check that DATA_FILE at the top of this script points to your HomeStretch.xlsx."
            )
        elif roster_df.empty:
            st.info("No patients found in the Excel roster.")
        else:
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1.5, 2, 1, 1])
            col1.write("**Patient**")
            col2.write("**Status**")
            col3.write("**Recordings**")
            col4.write("**Typical %**")
            col5.write("**Notes**")
            col7.write("**Pain**")

            st.divider()

            for _, row in roster_df.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1.5, 2, 1, 1])

                pid = int(row["Participant ID"])
                display_name = f"{row['Participant']} (ID {pid})"

                col1.write(display_name)

                with col2:
                    render_status(derive_status(row))

                col3.write(f"{int(row['Total Recordings'])} ({int(row['Typical Count'])}T / {int(row['Atypical Count'])}A)")

                with col4:
                    st.progress(row["Typical %"] / 100)
                    st.caption(f"{row['Typical %']}%")

                col5.write(row["Notes"] if row["Notes"] else "—")

                with col7:
                    latest_pain = get_latest_pain(pid)
                    if latest_pain is not None and latest_pain >= PAIN_ALERT_THRESHOLD:
                        st.markdown(
                            "<span style='background:#ff6b6b;color:white;padding:3px 8px;"
                            "border-radius:10px;font-size:12px;'>🚩 Pain</span>",
                            unsafe_allow_html=True,
                        )

                if col6.button("View", key=f"btn_{pid}"):
                    st.session_state.selected_patient = row["Participant"]
                    st.session_state.selected_patient_id = pid

    else:
        patient = st.session_state.selected_patient
        pid = st.session_state.selected_patient_id

        patient_row = None
        if not roster_df.empty and pid is not None:
            matches = roster_df[roster_df["Participant ID"] == pid]
            if not matches.empty:
                patient_row = matches.iloc[0]

        col1, col2 = st.columns([1, 5])

        with col1:
            st.image("person.jpg", width="content")

        with col2:
            st.subheader(f"{patient} (ID {pid})")
            st.caption("Left-side weakness")
            st.caption("Started HomeStretch: Jan 2026")
            st.markdown("""
            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;margin-right:5px;'>Stroke</span>
            <span style='background:#ffe066;padding:5px 10px;border-radius:10px;margin-right:5px;'>High Fall Risk</span>
            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;'>Uses Cane</span>
            """, unsafe_allow_html=True)

        latest_pain = get_latest_pain(pid)
        render_pain_flag(latest_pain)

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

            # ---- Recorded Calibration Data (from the Excel roster) ----
            st.markdown("### Recorded Calibration Data")
            st.caption("From HomeStretch.xlsx — Typical / Atypical recordings used to build this patient's movement profile.")

            if patient_row is None:
                st.info("No recordings found for this patient in the Excel file.")
            else:
                r1, r2, r3 = st.columns(3)
                r1.metric("Typical Recordings", int(patient_row["Typical Count"]))
                r2.metric("Atypical Recordings", int(patient_row["Atypical Count"]))
                r3.metric("Typical %", f"{patient_row['Typical %']}%")
                st.write(f"**Exercises recorded:** {patient_row['Exercises'] or '—'}")
                if patient_row["Notes"]:
                    st.caption(f"Notes: {patient_row['Notes']}")

                with st.expander("View recording files for this patient"):
                    pt_typical = typical_df[typical_df["Participant ID"] == pid]
                    pt_atypical = atypical_df[atypical_df["Participant ID"] == pid]
                    if not pt_typical.empty:
                        st.markdown("**Typical**")
                        st.dataframe(pt_typical[["Exercize", "Left or Right", "Filename"]], hide_index=True)
                    if not pt_atypical.empty:
                        st.markdown("**Atypical**")
                        st.dataframe(pt_atypical[["Exercize", "Left or Right", "Filename"]], hide_index=True)

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

                sessions = get_all_sessions(pid)

                if len(sessions) == 0:
                    st.info("No session data available yet")
                else:
                    reps = [float(s.get("num_reps", 0)) for s in sessions]
                    duration = [float(s.get("duration_sec", 0)) for s in sessions]
                    labels = [s["session_label"] for s in sessions]

                    chart_df = pd.DataFrame({
                        "Session": labels,
                        "Reps": reps,
                        "Duration": duration
                    })

                    avg_reps = sum(reps) / len(reps)
                    avg_duration = sum(duration) / len(duration)

                    best_idx = int(np.argmax(reps))
                    best_session_label = labels[best_idx]

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Avg Reps", round(avg_reps, 1))
                    m2.metric("Avg Duration", f"{round(avg_duration, 1)} sec")
                    m3.metric("Best Session", best_session_label)

                    st.divider()

                    st.markdown("#### Reps per Session")
                    st.bar_chart(chart_df.set_index("Session")["Reps"])

                    st.markdown("#### Duration Trend")
                    st.line_chart(chart_df.set_index("Session")["Duration"])

            with col2:
                sessions = get_all_sessions(pid)
                display_sessions = list(reversed(sessions))

                st.markdown("### Timeline")

                for i, s in enumerate(display_sessions):
                    time_str = format_session_time(s.get("session_time"))

                    label = (
                        f"{s['session_label']} | {time_str} | "
                        f"{s.get('num_reps', 'N/A')} reps | "
                        f"{round(s.get('duration_sec', 0), 1)} sec"
                    )

                    if st.button(label, key=f"session_{s['id']}"):
                        st.session_state.selected_session = s["id"]
                        st.session_state.selected_session_data = s
                        st.session_state.selected_session_time = time_str
                        st.session_state.selected_session_label = s["session_label"]
                        st.session_state.page = "session_detail"

                    pain_val = s.get(SESSION_PAIN_FIELD)
                    caption = f"{s.get('classification', 'Unknown')} • Tremor: {s.get('tremor_level', 'Unknown')}"
                    if pain_val is not None:
                        caption += f" • Pain: {pain_val}/10"
                    st.caption(caption)
        st.divider()

        with tab3:
            latest = get_latest_session(pid)

            if latest is None:
                st.info("No session data available yet")
            else:
                st.markdown("### Latest Session")
                st.caption(format_session_time(latest.get("session_time")))
                render_session_metrics(latest)

        if st.button("⬅ Back to Patients"):
            st.session_state.selected_patient = None
            st.session_state.selected_patient_id = None

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

    session_label = st.session_state.get("selected_session_label", "Session")
    session_time = st.session_state.get("selected_session_time")

    st.header("Session Details")
    st.subheader(session_label)

    if session_time:
        st.caption(session_time)

    if st.button("⬅ Back to Patient Profile"):
        st.session_state.page = "patients"

    if session_data is None:
        st.info("No session selected.")
    else:
        render_session_metrics(session_data)