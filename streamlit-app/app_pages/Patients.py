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

REPO_ROOT = next((parent for parent in Path(__file__).resolve().parents if (parent / "Data.xlsx").is_file()), Path(__file__).resolve().parent)



DATA_FILE = REPO_ROOT / "Data.xlsx"

# Firestore field on each session doc that links it to a patient.

# ASSUMPTION - update if your schema uses a different field name.

# This should match the "Participant ID" values in the Excel file.

SESSION_PATIENT_FIELD = "participant_id"
FIRESTORE_DEMO_ID = "__firestore_sessions__"  # Virtual profile; not a real patient



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

    credential_file = next((p / "homestretch-pipeline-5f8f03e61254.json" for p in [Path(__file__).resolve().parent, REPO_ROOT, REPO_ROOT / "streamlit-app"] if (p / "homestretch-pipeline-5f8f03e61254.json").is_file()), None)
    if credential_file is None:
        raise FileNotFoundError("Firestore service account JSON not found. Keep it outside Git and configure GOOGLE_APPLICATION_CREDENTIALS, or place it in a local private location.")
    cred = credentials.Certificate(str(credential_file))

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

@st.cache_data(ttl=20, show_spinner=False)
def load_all_firestore_sessions():
    """Read recording metadata and (when present) processed exercise fields."""
    sessions = []
    for snapshot in db.collection("sessions").stream():
        data = snapshot.to_dict() or {}
        data["id"] = snapshot.id
        data["session_time"] = (data.get("started_at") or data.get("startedAt")
                                or data.get("timestamp") or snapshot.create_time)
        sessions.append(data)

    def sort_key(record):
        t = record.get("session_time")
        if isinstance(t, datetime.datetime):
            return t.timestamp()
        return 0

    sessions.sort(key=sort_key)
    for i, session in enumerate(sessions, 1):
        session["session_label"] = f"S{i}"
    return sessions


def normalized_patient_id(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return str(int(float(text)))
    except (ValueError, TypeError):
        return text


def get_all_sessions(patient_id=None):
    sessions = load_all_firestore_sessions()
    if patient_id is None or patient_id == FIRESTORE_DEMO_ID:
        return sessions
    target = normalized_patient_id(patient_id)
    # Only verified participant identifiers count as a match.
    return [s for s in sessions if any(
        normalized_patient_id(s.get(field)) == target
        for field in ("participant_id", "patient_id", "participantId", "patientId")
        if s.get(field) is not None
    )]


def get_latest_session(patient_id=None):
    sessions = get_all_sessions(patient_id)
    return sessions[-1] if sessions else None


@st.cache_data(ttl=20)
def get_latest_pain(patient_id):
    sessions = get_all_sessions(patient_id)
    return sessions[-1].get(SESSION_PAIN_FIELD) if sessions else None


def format_session_time(ts):

    if ts is None:

        return "Time unavailable"

    if isinstance(ts, datetime.datetime):
        return ts.astimezone().strftime("%b %d, %I:%M %p")
    return str(ts)





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
    """Keep the original session details, showing unavailable data honestly."""
    section_heading("Session Details")
    st.caption(format_session_time(session.get("session_time")))
    st.write("**Recording:**", session.get("raw_file", "Not recorded"))
    st.write("**Session ID:**", session.get("session_id", session.get("id", "Unknown")))
    st.write("**Source session ID:**", session.get("source_session_id", "Not available"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reps", session.get("num_reps", "Not available"))
    duration = session.get("duration_sec")
    c2.metric("Duration", f"{float(duration):.1f} sec" if duration is not None else "Not available")
    snr = session.get("snr_db")
    c3.metric("SNR", f"{float(snr):.1f} dB" if snr is not None else "Not available")
    c4.metric("Tremor", session.get("tremor_level", "Not available"))

    classification = session.get("classification")
    if classification:
        if classification in ("Very Smooth", "Good Control"):
            st.success(f"Movement Quality: {classification}")
        else:
            st.warning(f"Movement Quality: {classification}")
    else:
        st.info("Movement classification is not included in this Firestore document.")

    pain = session.get(SESSION_PAIN_FIELD)
    if pain is not None:
        st.metric("Reported Pain", f"{pain}/10")
        render_pain_flag(pain)

    if "tremor_ratio" in session:
        st.markdown("### Tremor Ratio")
        ratio = float(session["tremor_ratio"])
        st.progress(max(0.0, min(1.0, ratio)))
        st.caption(f"{ratio:.4f}")

    if "num_typical" in session or "num_atypical" in session:
        section_heading("Repetition Quality")
        r1, r2, r3 = st.columns(3)
        r1.metric("Typical Reps", session.get("num_typical", "N/A"))
        r2.metric("Atypical Reps", session.get("num_atypical", "N/A"))
        atypical_ids = session.get("atypical_rep_ids") or []
        r3.metric("Atypical IDs Count", len(atypical_ids))
        st.write("Atypical Rep IDs:", atypical_ids if atypical_ids else "None reported")
    else:
        st.caption("Typical/atypical repetition results have not been stored in this document.")

    section_heading("Sensor Recording Quality")
    sensors = session.get("sensors") or {}
    if sensors:
        for name, details in sensors.items():
            if not isinstance(details, dict):
                continue
            samples = details.get("samples")
            invalid = details.get("invalid_samples")
            valid = (samples - invalid) if isinstance(samples, (int, float)) and isinstance(invalid, (int, float)) else None
            st.write(f"**{name.replace('_', ' ').title()}** — samples: {samples if samples is not None else 'N/A'}, invalid: {invalid if invalid is not None else 'N/A'}, valid: {valid if valid is not None else 'N/A'}")
    else:
        st.caption("No sensor sample summary stored for this session.")
    for field, label in (("received", "Received packets"), ("missing_by_sequence", "Missing packets"), ("schema_version", "Schema version")):
        if field in session:
            st.write(f"**{label}:** {session[field]}")

    signal = session.get("movement_signal")
    if isinstance(signal, list) and signal:
        st.markdown("### Movement Signal")
        st.line_chart(signal)
    else:
        st.caption("Movement signal graph unavailable: no waveform is stored in this document.")


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




# HomeStretch iOS-inspired clinician styling (visual changes only).
st.markdown("""
<style>
:root { --hs-blue:#3c82bd; --hs-light:#d5e7f5; --hs-pale:#edf6fc; --hs-border:#c1d9eb; }
[data-testid="stAppViewContainer"] { background: #f9fcff; }
.block-container { max-width: 1480px; padding-top: 1.35rem; padding-bottom: 3rem; }
h1,h2,h3 { color:#347fbd !important; letter-spacing:-0.02em; }
h1 { font-weight:650 !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div[data-testid="stVerticalBlock"]),
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px !important; }
[data-testid="stMetric"] { background:#e5f1f9; border:1px solid #d1e5f3; padding:15px 17px; border-radius:15px; }
[data-testid="stMetricLabel"] { color:#4d7290; }
[data-testid="stMetricValue"] { color:#327ab4; }
.stButton > button { border-radius:11px; border:1px solid #b3d4ea; color:#367db7; font-weight:600; }
.stButton > button:hover { border-color:#3c82bd; background:#e2f1fb; color:#236ca7; }
button[kind="primary"] { background:#438cc4 !important; color:white !important; }
.stTabs [data-baseweb="tab-list"] { background:#e6f2fb; padding:6px; border-radius:14px; gap:7px; }
.stTabs [data-baseweb="tab"] { color:#467eaa; border-radius:10px; font-weight:600; }
.stTabs [aria-selected="true"] { background:white; color:#2677b4; }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
[data-testid="stAlert"] { border-radius:12px; }
[data-testid="stExpander"] { border-radius:13px; border-color:#d2e4f1; }
.hs-banner { background:#cde3f3; padding:23px 27px; border-radius:20px; margin-bottom:20px; border:1px solid #b8d5e9; }
.hs-banner h1 { margin:0; font-size:2rem; color:#347fbd; }
.hs-banner p { margin:5px 0 0; color:#507b9d; font-size:.93rem; }
.hs-section { background:#d6e9f7; padding:11px 17px; border-radius:12px; font-weight:650; color:#347fbd; margin:15px 0 11px; }
.hs-note { color:#607e95; font-size:.85rem; }
/* Light-blue row panels without HTML inside Streamlit columns. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-row-marker) { background:#e6f2fb; border:1px solid #c9e0f0 !important; border-radius:15px !important; padding:7px 12px; }
.hs-row-marker { display:none; }
</style>
""", unsafe_allow_html=True)


def section_heading(title):
    st.markdown(f'<div class="hs-section">{title}</div>', unsafe_allow_html=True)


def roster_entry(name, status, recordings, typical_pct, notes, pain, button_key, on_view):
    """Compact blue row with the same data and View action as the original roster."""
    with st.container(border=True):
        st.markdown('<span class="hs-row-marker"></span>', unsafe_allow_html=True)
        cols = st.columns([2.3, 1.25, 1.25, 1.2, 2.2, .85], vertical_alignment="center")
        cols[0].markdown(f'**{name}**')
        with cols[1]:
            render_status(status)
        cols[2].write(recordings)
        with cols[3]:
            if typical_pct is None:
                st.caption('—')
            else:
                st.progress(max(0., min(1., float(typical_pct)/100)))
                st.caption(f'{float(typical_pct):.1f}%')
        cols[4].caption(str(notes) if notes else '—')
        with cols[5]:
            if st.button('View →', key=button_key, use_container_width=True):
                on_view()
        if pain is not None:
            st.caption(f'Pain alert: {pain}/10')


def select_patient(name, pid):
    st.session_state.selected_patient = name
    st.session_state.selected_patient_id = pid
    st.rerun()

st.markdown('<div class="hs-banner"><h1>Patients</h1><p>HomeStretch · Clinician Dashboard</p></div>', unsafe_allow_html=True)

# -----------------------

# HELPER: STATUS COLORS

# -----------------------

def render_status(status):
    """Use native Streamlit text, avoiding raw HTML/CSS shown as code."""
    icons = {"Active": "🟢", "Needs Review": "🟡", "Inactive": "🔴", "Unlinked Sessions": "🔵"}
    st.write(f"{icons.get(status, '⚪')} {status}")


# -----------------------

# MAIN LOGIC

# -----------------------

if st.session_state.page == "patients":



    if st.session_state.selected_patient is None:



        section_heading("Patient Roster")
        demo_sessions = get_all_sessions(FIRESTORE_DEMO_ID)
        if roster_load_error:
            st.error(f"Could not load Excel patient roster from {DATA_FILE}: {roster_load_error}")
        active_count = 0 if roster_df.empty else sum(derive_status(row) == "Active" for _, row in roster_df.iterrows())
        review_count = 0 if roster_df.empty else sum(derive_status(row) == "Needs Review" for _, row in roster_df.iterrows())
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Excel participants", len(roster_df))
        k2.metric("Active · prototype", active_count)
        k3.metric("Needs Review · prototype", review_count)
        k4.metric("Firestore recordings", len(demo_sessions))
        st.caption("Patient statuses are provisional classifications from Excel calibration recordings, not clinical assessments or measured adherence.")
        search_term = st.text_input("Search participants", placeholder="Name or participant ID", key="patient_roster_search")
        status_filter = st.selectbox("Filter status", ["All", "Active", "Needs Review", "Inactive", "Unlinked Sessions"], key="patient_roster_filter")
        headers = st.columns([2.3, 1.25, 1.25, 1.2, 2.2, .85])
        for col, label in zip(headers, ["Patient", "Status", "Recordings", "Typical %", "Notes", "Profile"]):
            col.markdown(f"**{label}**")
        if status_filter in ("All", "Unlinked Sessions") and (not search_term or search_term.lower() in "firestore sessions unlinked demo"):
            roster_entry(
                "Firestore Sessions (Unlinked / Demo)", "Unlinked Sessions",
                f"{len(demo_sessions)} sessions", None,
                "Unlinked recording collection · not a verified patient", None,
                "view_firestore_demo",
                lambda: select_patient("Firestore Sessions (Unlinked / Demo)", FIRESTORE_DEMO_ID),
            )
        if not roster_df.empty:
            for _, row in roster_df.iterrows():
                pid = int(row["Participant ID"])
                status = derive_status(row)
                display_name = f"{row['Participant']} (ID {pid})"
                if status_filter not in ("All", status):
                    continue
                if search_term and search_term.lower() not in display_name.lower():
                    continue
                pain = get_latest_pain(pid)
                pain_alert = pain if isinstance(pain, (int, float)) and pain >= PAIN_ALERT_THRESHOLD else None
                roster_entry(
                    display_name, status,
                    f"{int(row['Total Recordings'])} ({int(row['Typical Count'])}T / {int(row['Atypical Count'])}A)",
                    row["Typical %"], row["Notes"], pain_alert,
                    f"btn_{pid}",
                    lambda n=row["Participant"], p=pid: select_patient(n, p),
                )
        elif not roster_load_error:
            st.info("No Excel participants found. The Firestore demo profile remains available.")

    else:

        patient = st.session_state.selected_patient

        pid = st.session_state.selected_patient_id



        patient_row = None

        if not roster_df.empty and pid is not None:

            matches = roster_df[roster_df["Participant ID"] == pid]

            if not matches.empty:

                patient_row = matches.iloc[0]



        if st.button("← Back to Patients", key="profile_top_back"):
            st.session_state.selected_patient = None
            st.session_state.selected_patient_id = None
            st.rerun()
        section_heading("Patient Profile")
        col1, col2 = st.columns([1, 5])



        with col1:

            if pid == FIRESTORE_DEMO_ID:
                st.info("Firestore recording collection")
            elif Path("person.jpg").is_file():
                st.image("person.jpg", width="content")



        with col2:

            st.subheader(patient if pid == FIRESTORE_DEMO_ID else f"{patient} (ID {pid})")

            if pid == FIRESTORE_DEMO_ID:
                st.info("Virtual testing profile: all Firestore sessions are grouped here for review. They are NOT verified as belonging to the same person.")
            else:
                st.caption("Demo clinical detail (not verified for this participant): Left-side weakness")

            if pid != FIRESTORE_DEMO_ID:
                st.caption("Demo start date (not verified): Jan 2026")

            if pid != FIRESTORE_DEMO_ID:
                st.markdown("""

            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;margin-right:5px;'>Stroke</span>

            <span style='background:#ffe066;padding:5px 10px;border-radius:10px;margin-right:5px;'>High Fall Risk</span>

            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;'>Uses Cane</span>

            """, unsafe_allow_html=True)



        latest_pain = get_latest_pain(pid)

        render_pain_flag(latest_pain)



        st.info("Home activity and adherence have not been verified. See Firestore session timeline below.")

        st.divider()



        tab1, tab2, tab3 = st.tabs(["Information", "Sessions", "Latest Session"])



        # -----------------------

        # INFORMATION TAB

        # -----------------------

        with tab1:

            if pid == FIRESTORE_DEMO_ID:
                st.warning("Clinical overview, functional baseline, and program details below are DEMO placeholders, not facts about the Firestore recordings or a patient.")

            colA, colB = st.columns(2)



            with colA:

                section_heading("Clinical Overview")
                st.caption("Illustrative clinical information — not linked to this participant record")

                st.markdown("""

                Stroke Type  

                Ischemic Stroke  



                Assistive Devices  

                Cane, Walker, AFO  



                Date of Stroke  

                Aug 20, 2025  



                Living Situation  

                With caregiver  

                Stairs at home  

                """)



            with colB:

                section_heading("Current Program")
                st.caption("Illustrative program — not a saved prescription")

                st.markdown("""

                Frequency  

                3 sessions / week  



                Session Duration  

                ~28 min  



                Exercises  

                6  



                Last Update  

                Jan 18, 2026  

                """)



                if st.button("Program Builder"):

                    st.session_state.page = "builder"



            colC, colD = st.columns(2)



            with colC:

                section_heading("Functional Baseline")
                st.caption("Illustrative baseline — not verified patient data")

                st.markdown("""

                Gait  

                Independent (Supervision outdoors)  



                Upper Limb  

                Limited (fine motor control)  

                """)



            with colD:

                st.markdown("### ")

                st.markdown("""

                Sit to Stand  

                8 reps, Unassisted  



                Balance Confidence  

                Moderate  

                """)



            # ---- Recorded Calibration Data (from the Excel roster) ----

            section_heading("Recorded Calibration Data")

            st.caption("From Data.xlsx — Typical / Atypical calibration recordings; not completed exercise sessions.")



            if patient_row is None:

                st.info("No recordings found for this patient in the Excel file.")

            else:

                r1, r2, r3 = st.columns(3)

                r1.metric("Typical Recordings", int(patient_row["Typical Count"]))

                r2.metric("Atypical Recordings", int(patient_row["Atypical Count"]))

                r3.metric("Typical %", f"{patient_row['Typical %']}%")

                st.write(f"Exercises recorded: {patient_row['Exercises'] or '—'}")

                if patient_row["Notes"]:

                    st.caption(f"Notes: {patient_row['Notes']}")



                with st.expander("View recording files for this patient"):

                    pt_typical = typical_df[typical_df["Participant ID"] == pid]

                    pt_atypical = atypical_df[atypical_df["Participant ID"] == pid]

                    if not pt_typical.empty:

                        st.markdown("Typical")

                        st.dataframe(pt_typical[["Exercize", "Left or Right", "Filename"]], hide_index=True)

                    if not pt_atypical.empty:

                        st.markdown("Atypical")

                        st.dataframe(pt_atypical[["Exercize", "Left or Right", "Filename"]], hide_index=True)



            section_heading("Notes")
            st.caption("Illustrative note — not a clinical record")

            st.info("""

            Last entry – Feb 7  

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

                section_heading("Engagement Insights")
                st.caption("Illustrative insights — not derived from Firestore. Do not use for clinical decisions.")

                st.markdown("""

                • Tends to skip weekends  

                • Completes better in mornings  

                • Increased difficulty this week  

                """)



                section_heading("Session Overview")



                sessions = get_all_sessions(pid)



                if len(sessions) == 0:

                    st.info("No Firestore sessions linked to this Excel participant ID. Open the Firestore Sessions (Unlinked / Demo) row in the Patient List to review unlinked recordings.")

                else:

                    st.metric("Firestore recordings", len(sessions))
                    session_rows = []
                    for item in reversed(sessions):
                        sensor_map = item.get("sensors") or {}
                        session_rows.append({
                            "Session": item.get("session_label", "—"),
                            "Started": format_session_time(item.get("session_time")),
                            "Recording": item.get("raw_file", "—"),
                            "Reps": item.get("num_reps", "Not available"),
                            "Received packets": item.get("received", "—"),
                            "Missing packets": item.get("missing_by_sequence", "—"),
                            "Accelerometer samples": (sensor_map.get("acceleration") or {}).get("samples", "—"),
                            "Gyroscope samples": (sensor_map.get("gyroscope") or {}).get("samples", "—"),
                            "PPG samples": (sensor_map.get("ppg_green") or {}).get("samples", "—"),
                        })
                    st.dataframe(pd.DataFrame(session_rows), hide_index=True, use_container_width=True)
                    st.caption("Rep counts appear only when processed analysis is present; sensor sample counts are not repetition counts.")

                    analyzed_sessions = [s for s in sessions if s.get("num_reps") is not None and s.get("duration_sec") is not None]
                    if not analyzed_sessions:
                        st.info("Linked recordings have no processed rep/duration metrics yet. Sensor metadata is available in Latest Session.")
                    reps = [float(s.get("num_reps") or 0) for s in analyzed_sessions]

                    duration = [float(s.get("duration_sec") or 0) for s in analyzed_sessions]

                    labels = [s["session_label"] for s in analyzed_sessions]



                    chart_df = pd.DataFrame({

                        "Session": labels,

                        "Reps": reps,

                        "Duration": duration

                    })



                    avg_reps = sum(reps) / len(reps) if reps else 0

                    avg_duration = sum(duration) / len(duration) if duration else 0



                    best_idx = int(np.argmax(reps)) if reps else None

                    best_session_label = labels[best_idx] if best_idx is not None else "N/A"



                    m1, m2, m3 = st.columns(3)

                    m1.metric("Avg Reps", round(avg_reps, 1) if reps else "N/A")

                    m2.metric("Avg Duration", f"{round(avg_duration, 1)} sec" if duration else "N/A")

                    m3.metric("Best Session", best_session_label)



                    st.divider()



                    st.markdown("#### Reps per Session")

                    if not chart_df.empty:
                        st.bar_chart(chart_df.set_index("Session")["Reps"])



                    st.markdown("#### Duration Trend")

                    if not chart_df.empty:
                        st.line_chart(chart_df.set_index("Session")["Duration"])



            with col2:

                sessions = get_all_sessions(pid)

                display_sessions = list(reversed(sessions))



                section_heading("Timeline")



                for i, s in enumerate(display_sessions):

                    time_str = format_session_time(s.get("session_time"))



                    label = (

                        f"{s['session_label']} | {time_str} | "

                        f"{s.get('raw_file', 'Recording')} | "

                        f"{str(s.get('num_reps')) + ' reps' if s.get('num_reps') is not None else 'Reps N/A'}"

                    )



                    if st.button(label, key=f"session_{s['id']}"):

                        st.session_state.selected_session = s["id"]

                        st.session_state.selected_session_data = s

                        st.session_state.selected_session_time = time_str

                        st.session_state.selected_session_label = s["session_label"]

                        st.session_state.page = "session_detail"



                    pain_val = s.get(SESSION_PAIN_FIELD)

                    caption = (f"Received: {s.get('received', 'N/A')} packets • "
                               f"Missing: {s.get('missing_by_sequence', 'N/A')} • "
                               f"Movement: {s.get('classification', 'Not analyzed')}")

                    if pain_val is not None:

                        caption += f" • Pain: {pain_val}/10"

                    st.caption(caption)

        st.divider()



        with tab3:

            latest = get_latest_session(pid)



            if latest is None:

                st.info("No Firestore sessions linked to this Excel participant ID. Open the Firestore Sessions (Unlinked / Demo) row in the Patient List to review unlinked recordings.")

            else:

                section_heading("Latest Session")

                st.caption(format_session_time(latest.get("session_time")))

                render_session_metrics(latest)



        if st.button("⬅ Back to Patients"):

            st.session_state.selected_patient = None

            st.session_state.selected_patient_id = None



# -----------------------

# PROGRAM BUILDER

# -----------------------

elif st.session_state.page == "builder":



    section_heading("Program Builder")



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



    section_heading("Session Details")

    st.subheader(session_label)



    if session_time:

        st.caption(session_time)



    if st.button("⬅ Back to Patient Profile"):

        st.session_state.page = "patients"



    if session_data is None:

        st.info("No session selected.")

    else:

        render_session_metrics(session_data)