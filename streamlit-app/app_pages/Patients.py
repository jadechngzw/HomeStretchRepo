import streamlit as st

import pandas as pd

import numpy as np

from pathlib import Path

import firebase_admin

from firebase_admin import credentials, firestore

import datetime
import os
import requests



st.set_page_config(layout="wide")



# =====================================================================

# CONFIG - adjust these if your paths / Firestore field names differ

# =====================================================================



# Only Firestore supplies patient names and session data.
REPO_ROOT = next((parent for parent in Path(__file__).resolve().parents
                  if parent.name == "HomeStretchRepo"), Path(__file__).resolve().parent)
FIRESTORE_DEMO_ID = "__firestore_sessions__"
FIRESTORE_NAMED_PREFIX = "__firestore_name__:"
FIRESTORE_COLLECTION = "sessions"
INACTIVE_AFTER_DAYS = 30  # Prototype activity threshold, not a clinical assessment.

# Firestore field holding a patient's reported pain score (0-10) on a

# session. ASSUMPTION - pain may not be stored in the current Firestore schema, so this

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

# SESSION DATA (Firestore) - now filterable per patient

# =====================================================================

@st.cache_data(ttl=20, show_spinner=False)
def load_all_firestore_sessions():
    """Read recording metadata and (when present) processed exercise fields."""
    sessions = []
    for snapshot in db.collection(FIRESTORE_COLLECTION).stream():
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


def normalized_patient_name(value):
    """Normalize only explicit Firestore patient names; never infer from filename."""
    if not isinstance(value, str):
        return None
    return " ".join(value.strip().split()).casefold() or None


def firestore_patient_name(session):
    for field in ("Patient", "patient_name", "patientName"):
        value = session.get(field)
        if normalized_patient_name(value):
            return " ".join(value.strip().split())
    return None


def get_all_sessions(patient_id=None, patient_name=None):
    """Each named patient gets their own sessions; unnamed sessions stay unlinked."""
    sessions = load_all_firestore_sessions()
    if patient_id is None and patient_name is None:
        return sessions
    if patient_id == FIRESTORE_DEMO_ID:
        return [s for s in sessions if not firestore_patient_name(s)]
    if isinstance(patient_id, str) and patient_id.startswith(FIRESTORE_NAMED_PREFIX):
        key = patient_id[len(FIRESTORE_NAMED_PREFIX):]
    else:
        key = normalized_patient_name(patient_name)
    return [s for s in sessions
            if normalized_patient_name(firestore_patient_name(s)) == key]


def get_named_firestore_patients():
    names = {}
    for session in load_all_firestore_sessions():
        name = firestore_patient_name(session)
        key = normalized_patient_name(name)
        if key:
            names.setdefault(key, name)
    return sorted(names.items(), key=lambda item: item[1].casefold())


def session_timestamp(session):
    value = session.get("session_time")
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    return None


def needs_review(session):
    """Conservative prototype flag; only explicitly reported movement concerns."""
    label = str(session.get("classification") or "").strip().casefold()
    if label in ("atypical", "poor control", "poor control / tremor dominant"):
        return True
    if isinstance(session.get("num_atypical"), (int, float)) and session["num_atypical"] > 0:
        return True
    guidance = session.get("guidance")
    if isinstance(guidance, dict):
        flags = guidance.get("flags")
        if isinstance(flags, list) and len(flags) > 0:
            return True
    return False


def derive_firestore_status(sessions):
    """Activity/review labels for a prototype; not clinician-approved statuses."""
    if not sessions:
        return "Inactive"
    dates = [t for s in sessions if (t := session_timestamp(s)) is not None]
    if not dates:
        return "Inactive"
    if dates:
        most_recent = max(dates)
        if datetime.datetime.now(datetime.timezone.utc) - most_recent > datetime.timedelta(days=INACTIVE_AFTER_DAYS):
            return "Inactive"
    if any(needs_review(s) for s in sessions):
        return "Needs Review"
    return "Active"


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
    st.write("**Recording:**", session.get("raw_file") or session.get("file_name") or ((session.get("exercise") or {}).get("name", "Not recorded") if isinstance(session.get("exercise"), dict) else "Not recorded"))
    st.write("**Session ID:**", session.get("session_id", session.get("id", "Unknown")))
    st.write("**Source session ID:**", session.get("source_session_id", "Not available"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reps", session.get("num_reps", session.get("rep_count", "Not available")))
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

    "selected_patient_id": None,  # Firestore profile identifier

    "page": "patients",
    "history_patient_id": None,
    "history_patient_name": None,
    "session_detail_return": "patients",

    "program": [],

}.items():

    if key not in st.session_state:

        st.session_state[key] = default




# HomeStretch clinician visual system: quiet surfaces and restrained blue accents.
st.markdown("""
<style>
:root {--hs-blue:#367FBD;--hs-border:#C8DCEB;--hs-muted:#61798C;}
[data-testid="stAppViewContainer"] {background:#FAFCFE;}
.block-container {max-width:1420px;padding-top:1.35rem;padding-bottom:3rem;}
h1,h2,h3 {color:#234F73!important;letter-spacing:-.015em;}
h1 {font-weight:650!important;}
h3 {font-size:1.15rem!important;}
[data-testid="stMetric"] {background:#EDF5FB;border:1px solid #D7E7F2;padding:14px 16px;border-radius:13px;}
[data-testid="stMetricLabel"] {color:#5A768C;}
[data-testid="stMetricValue"] {color:#2F719F;}
.stButton>button {border-radius:10px;border:1px solid #BDD6E9;color:#367FBD;font-weight:600;background:white;}
.stButton>button:hover {border-color:#367FBD;background:#F0F7FC;color:#245D8C;}
button[kind="primary"] {background:#367FBD!important;color:white!important;}
/* Prominent, accessible navigation for Information / Sessions / Latest Session. */
.stTabs [data-baseweb="tab-list"] {
    display:flex; gap:10px; padding:7px;
    background:#F1F7FC; border:1px solid #D6E6F2;
    border-radius:15px; margin:8px 0 20px;
}
.stTabs [data-baseweb="tab"] {
    flex:1 1 0; justify-content:center; min-height:56px;
    padding:12px 18px; background:#E5F1FA;
    border:1px solid #BDD8EB; border-radius:11px;
    color:#285F8B!important; font-size:1rem; font-weight:700;
    transition:background .15s ease, box-shadow .15s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background:#D6E9F7; border-color:#8DBAD9;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background:#367FBD!important; border-color:#367FBD!important;
    color:#FFFFFF!important; box-shadow:0 3px 9px rgba(39,103,156,.18);
}
.stTabs [data-baseweb="tab"]:focus-visible {
    outline:3px solid #184F7D; outline-offset:2px;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {display:none;}
@media(max-width:700px) {
    .stTabs [data-baseweb="tab-list"] {gap:5px;padding:5px;}
    .stTabs [data-baseweb="tab"] {min-height:49px;padding:8px 6px;font-size:.84rem;}
}
[data-testid="stDataFrame"] {border-radius:10px;overflow:hidden;}
[data-testid="stAlert"] {border-radius:10px;}
[data-testid="stExpander"] {border-radius:10px;border-color:#D3E2EE;}
.hs-banner {
    background: #C4DCEF;
    padding: 24px 30px;
    border-radius: 16px;
    margin-bottom: 24px;
}

.hs-banner h1 {
    margin: 0;
    color: #285F91 !important;
    font-size: 32px;
    font-weight: 600;
}

.hs-banner p {
    margin: 6px 0 0;
    color: #527D9F;
    font-size: 14px;
}
.hs-section {font-size:1.08rem;font-weight:650;color:#2D648F;margin:12px 0 10px;}
.hs-note {color:#61798C;font-size:.86rem;}
/* Keep the compact roster blue, while inner profile cards remain white. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-row-marker) {background:#E6F2FB;border:1px solid #C9E0F0!important;border-radius:13px!important;padding:6px 11px;}
.hs-row-marker {display:none;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card) {background:#FFFFFF;border:1px solid #C8DCEB!important;border-radius:14px!important;padding:12px 16px;box-shadow:0 2px 8px rgba(38,91,133,.035);}
.hs-white-card {display:none;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-soft-card) {background:#EDF5FB;border:1px solid #D7E7F2!important;border-radius:14px!important;padding:12px 16px;}
.hs-soft-card {display:none;}

/* HomeStretch patient-profile visual refresh: presentation only */
:root {--hs-navy:#163E67;--hs-blue:#246FAE;--hs-line:#AFCDE4;}
[data-testid="stAppViewContainer"] {background:linear-gradient(180deg,#F5F9FD 0%,#FFFFFF 55%);}
.block-container {max-width:1370px;}
.hs-section {font-size:1.18rem;font-weight:750;color:#174B78;margin:8px 0 13px;letter-spacing:-.015em;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card) {
 background:linear-gradient(145deg,#FFFFFF 68%,#F7FBFF 100%);
 border:1.6px solid #B7D0E5!important;
 border-radius:17px!important;
 padding:19px 22px!important;
 box-shadow:0 4px 15px rgba(28,77,116,.07),0 1px 3px rgba(28,77,116,.04);
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card) .hs-section {
 border-left:4px solid #317DB8;padding-left:12px;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-soft-card) {
 background:#E7F2FC;border:1.6px solid #B7D0E5!important;
 border-radius:16px!important;padding:18px 21px!important;
 box-shadow:0 3px 12px rgba(28,77,116,.05);
}
[data-testid="stMetric"] {
 background:linear-gradient(135deg,#E7F3FE,#F3F9FE);
 border:1.5px solid #C0DAEE;
 border-radius:15px;padding:17px 19px;
 box-shadow:0 2px 8px rgba(40,103,153,.055);
}
[data-testid="stMetricValue"] {color:#1C5E96;font-weight:750;}
[data-testid="stMetricLabel"] {color:#486B88;font-weight:600;}
.stTabs [data-baseweb="tab-list"] {background:#EAF3FB;border:1.5px solid #BBD5EA;padding:7px;gap:10px;}
.stTabs [data-baseweb="tab"] {background:#F9FCFF;border:1.5px solid #BBD5EA;color:#1C5485!important;font-weight:750;min-height:60px;}
.stTabs [data-baseweb="tab"][aria-selected="true"] {background:linear-gradient(110deg,#286DAA,#1A568F)!important;border-color:#1A568F!important;box-shadow:0 4px 12px rgba(30,92,145,.23);}
.stButton>button {border:1.5px solid #A9CBE4;color:#205E96;font-weight:700;min-height:40px;box-shadow:0 1px 3px rgba(30,80,125,.04);}
.stButton>button:hover {background:#E6F2FC;border-color:#2E7BB7;box-shadow:0 3px 9px rgba(30,80,125,.1);}
[data-testid="stExpander"] {border:1.5px solid #C2D9EA;border-radius:12px;}
/* Stronger profile identity banner; does not change the patient roster. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-profile-banner) {
 background:linear-gradient(105deg,#D9EBFA 0%,#E9F4FD 60%,#F7FBFF 100%);
 border:1.5px solid #B4D2E9!important;border-radius:17px!important;
 padding:18px 24px!important;box-shadow:0 3px 12px rgba(27,85,132,.08);
}
.hs-profile-banner {display:none;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-profile-banner) h3 {font-size:1.6rem!important;font-weight:750!important;color:#174B78!important;}
@media(max-width:700px) {
 [data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card) {padding:12px!important;}
 .stTabs [data-baseweb="tab"] {min-height:48px;}
}
</style>
""", unsafe_allow_html=True)


def white_card():
    """Marker for a white, blue-outline Streamlit bordered container."""
    st.markdown('<span class="hs-white-card"></span>', unsafe_allow_html=True)


def soft_card():
    st.markdown('<span class="hs-soft-card"></span>', unsafe_allow_html=True)


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

# =====================================================
# EPIC SANDBOX HANDOFF (local development only)
# =====================================================
# A short-lived, single-use ticket is exchanged server-to-server.
# Epic OAuth tokens and client secrets are never sent to Streamlit.
if "epic_sandbox_patient" not in st.session_state:
    st.session_state.epic_sandbox_patient = None

handoff_ticket = st.query_params.get("epic_ticket")
if handoff_ticket:
    # Clear the ticket from the address bar immediately.
    del st.query_params["epic_ticket"]
    handoff_secret = os.getenv("HOMESTRETCH_HANDOFF_SECRET", "")
    if not handoff_secret:
        st.error("Epic handoff is not configured in Streamlit. Set HOMESTRETCH_HANDOFF_SECRET.")
    else:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/internal/consume-handoff",
                json={"ticket": str(handoff_ticket)},
                headers={"X-HomeStretch-Secret": handoff_secret},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("id") and data.get("name"):
                st.session_state.epic_sandbox_patient = data
                st.session_state.page = "patients"
                st.session_state.selected_patient = None
                st.session_state.selected_patient_id = None
                st.success("Epic sandbox patient retrieved successfully.")
            else:
                st.error("Epic returned an incomplete patient summary.")
        except requests.RequestException:
            st.error("Epic handoff failed or expired. Return to localhost:8000 and connect again.")


# =====================================================
# EPIC SANDBOX CLASSROOM DEMO (NO FIRESTORE WRITES)
# =====================================================
EPIC_DEMO_PROFILE_ID = "__epic_sandbox_demo__"


def epic_demo_sessions():
    """Clearly fictional rehab sessions; not associated with Epic clinical data."""
    return [
        {"date": "Oct 19, 2026", "exercise": "Bicep curl", "side": "Right",
         "reps": 10, "typical": 7, "atypical": 3, "duration": 112.0,
         "classification": "Needs Review", "fatigue_before": 3, "fatigue_after": 5},
        {"date": "Oct 21, 2026", "exercise": "Bicep curl", "side": "Right",
         "reps": 12, "typical": 10, "atypical": 2, "duration": 108.5,
         "classification": "Typical", "fatigue_before": 2, "fatigue_after": 4},
        {"date": "Oct 23, 2026", "exercise": "Bicep curl", "side": "Right",
         "reps": 12, "typical": 11, "atypical": 1, "duration": 105.0,
         "classification": "Typical", "fatigue_before": 2, "fatigue_after": 3},
    ]


def render_epic_demo_profile():
    """Separate synthetic example: does not assign Firestore recordings to Epic patient."""
    patient = st.session_state.get("epic_sandbox_patient")
    if not patient:
        st.warning("Epic sandbox patient is not loaded. Reconnect through FastAPI.")
        if st.button("Back to roster", key="epic_missing_back"):
            st.session_state.selected_patient = None
            st.session_state.selected_patient_id = None
            st.rerun()
        return

    if st.button("← Back to Patients", key="epic_demo_back"):
        st.session_state.selected_patient = None
        st.session_state.selected_patient_id = None
        st.session_state.epic_demo_history = False
        st.session_state.epic_demo_detail = None
        st.rerun()

    with st.container(border=True):
        white_card()
        st.subheader(patient.get("name", "Epic Sandbox Patient"))
        st.caption("Epic FHIR R4 sandbox · Synthetic patient")
        st.info("CLASSROOM DEMONSTRATION: All rehabilitation sessions below are invented example data, not Epic records or HomeStretch Firestore measurements.")

    sessions = epic_demo_sessions()
    if st.session_state.get("epic_demo_detail") is not None:
        idx = st.session_state.epic_demo_detail
        if st.button("← Back to Session History", key="epic_detail_back"):
            st.session_state.epic_demo_detail = None
            st.rerun()
        if 0 <= idx < len(sessions):
            item = sessions[idx]
            section_heading("Example Session Details")
            st.caption(f"{item['date']} · {item['exercise']} · {item['side']} arm")
            a,b,c=st.columns(3)
            a.metric("Repetitions", item['reps'])
            b.metric("Typical", item['typical'])
            c.metric("Atypical", item['atypical'])
            with st.container(border=True):
                white_card()
                st.write("**Movement classification:**", item['classification'])
                st.write("**Duration:**", f"{item['duration']:.1f} sec")
                st.write("**Fatigue (before / after):**", f"{item['fatigue_before']} / 10 → {item['fatigue_after']} / 10")
                st.caption("Illustrative numbers only. No real IMU/PPG data was used.")
        return

    if st.session_state.get("epic_demo_history", False):
        section_heading("Example Session History")
        if st.button("← Back to Profile", key="epic_history_back"):
            st.session_state.epic_demo_history = False
            st.rerun()
        for idx in reversed(range(len(sessions))):
            item=sessions[idx]
            with st.container(border=True):
                white_card()
                left,right=st.columns([4,1], vertical_alignment="center")
                left.markdown(f"**{item['date']} · {item['exercise']}**")
                left.caption(f"{item['reps']} reps · {item['classification']}")
                with right:
                    if st.button("View Details", key=f"epic_example_{idx}"):
                        st.session_state.epic_demo_detail = idx
                        st.rerun()
        return

    m1,m2,m3=st.columns(3)
    m1.metric("Example sessions",len(sessions))
    m2.metric("Latest example",sessions[-1]['date'])
    m3.metric("Latest typical reps",f"{sessions[-1]['typical']}/{sessions[-1]['reps']}")

    tab_info,tab_sessions,tab_latest=st.tabs(["Information", "Sessions", "Latest Session"])
    with tab_info:
        left,right=st.columns(2)
        with left:
            with st.container(border=True):
                white_card()
                section_heading("Epic Patient Information")
                st.markdown(f"**FHIR Patient ID:** {patient.get('id','Unavailable')}")
                st.markdown(f"**Gender:** {patient.get('gender','Unavailable')}")
                st.markdown(f"**Date of birth:** {patient.get('birthDate','Unavailable')}")
                st.caption("Retrieved from Epic's synthetic sandbox record.")
        with right:
            with st.container(border=True):
                white_card()
                section_heading("HomeStretch Rehabilitation")
                st.caption("Example exercise plan: Right-arm bicep curls · 3 sessions/week")
                st.caption("Demonstration only; no prescription was retrieved from Epic.")
    with tab_sessions:
        with st.container(border=True):
            white_card()
            section_heading("Session History")
            st.caption("View the three synthetic example recordings.")
            if st.button("View Session History →", key="epic_demo_history_btn", use_container_width=True):
                st.session_state.epic_demo_history = True
                st.rerun()
        chart=pd.DataFrame([{"Session":s['date'], "Repetitions":s['reps'], "Duration (sec)":s['duration']} for s in sessions])
        with st.container(border=True):
            white_card()
            section_heading("Repetitions per Session")
            st.bar_chart(chart.set_index("Session")["Repetitions"])
        with st.container(border=True):
            white_card()
            section_heading("Session Duration Trend")
            st.line_chart(chart.set_index("Session")["Duration (sec)"])
    with tab_latest:
        item=sessions[-1]
        with st.container(border=True):
            white_card()
            section_heading("Latest Example Session")
            st.caption(f"{item['date']} · {item['exercise']}")
            a,b,c=st.columns(3)
            a.metric("Total reps",item['reps'])
            b.metric("Typical",item['typical'])
            c.metric("Atypical",item['atypical'])
            st.write("**Movement classification:**",item['classification'])
            st.write("**Duration:**",f"{item['duration']:.1f} sec")
            st.write("**Fatigue before / after:**",f"{item['fatigue_before']}/10 → {item['fatigue_after']}/10")
            st.caption("All movement metrics are simulated; not validated clinical outputs.")


# -----------------------

# HELPER: STATUS COLORS

# -----------------------

def render_status(status):
    """Use native Streamlit text, avoiding raw HTML/CSS shown as code."""
    icons = {"Active": "🟢", "Needs Review": "🟡", "Inactive": "🔴", "Unlinked Sessions": "🔵", "Epic Demo": "🔵", }
    st.write(f"{icons.get(status, '⚪')} {status}")


# -----------------------

# MAIN LOGIC

# -----------------------

if st.session_state.page == "patients":



    if st.session_state.selected_patient is None:



        section_heading("Patient Roster")
        demo_sessions = get_all_sessions(FIRESTORE_DEMO_ID)
        named_firestore_patients = get_named_firestore_patients()
        status_by_name = {}
        for key, name in named_firestore_patients:
            status_by_name[key] = derive_firestore_status(
                get_all_sessions(FIRESTORE_NAMED_PREFIX + key)
            )
        active_count = sum(v == "Active" for v in status_by_name.values())
        review_count = sum(v == "Needs Review" for v in status_by_name.values())
        inactive_count = sum(v == "Inactive" for v in status_by_name.values())
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Named patients", len(named_firestore_patients))
        k2.metric("Active", active_count)
        k3.metric("Needs Review", review_count)
        k4.metric("Inactive", inactive_count)
        st.caption("Statuses are provisional: Needs Review = explicit atypical movement/flag; Inactive = no recording in 30 days; Active = other recent activity. They do not measure adherence or clinical safety.")
        search_term = st.text_input("Search patients", placeholder="Patient name", key="patient_roster_search")
        status_filter = st.selectbox("Filter status", ["All", "Active", "Needs Review", "Inactive", "Unlinked Sessions", "Epic Demo"], key="patient_roster_filter")
        headers = st.columns([2.3, 1.25, 1.25, 1.2, 2.2, .85])
        for col, label in zip(headers, ["Patient", "Status", "Sessions", "Latest", "Notes", "Profile"]):
            col.markdown(f"**{label}**")
        # Epic sandbox patient appears in the same roster as Firestore patients.
        # The session counts below are simulated classroom data, not Firestore data.
        epic_patient = st.session_state.get("epic_sandbox_patient")
        if epic_patient:
            epic_name = epic_patient.get("name", "Epic sandbox patient")
            matches_search = (not search_term or search_term.casefold() in epic_name.casefold())
            matches_filter = status_filter in ("All", "Epic Demo")
            if matches_search and matches_filter:
                def open_epic_demo():
                    st.session_state.selected_patient = epic_name
                    st.session_state.selected_patient_id = EPIC_DEMO_PROFILE_ID
                    st.session_state.epic_demo_history = False
                    st.session_state.epic_demo_detail = None
                    st.rerun()

                roster_entry(
                    epic_name,
                    "Epic Demo",
                    f"{len(epic_demo_sessions())} simulated",
                    None,
                    "Epic sandbox demographics; simulated rehabilitation sessions",
                    None,
                    "epic_patient_profile_view",
                    open_epic_demo,
                )

        for name_key, display_name in named_firestore_patients:
            named_id = FIRESTORE_NAMED_PREFIX + name_key
            named_sessions = get_all_sessions(named_id)
            status = status_by_name[name_key]
            if status_filter not in ("All", status):
                continue
            if search_term and search_term.casefold() not in display_name.casefold():
                continue
            last = format_session_time(named_sessions[-1].get("session_time")) if named_sessions else "—"
            roster_entry(
                display_name, status, f"{len(named_sessions)} sessions", None,
                f"Last: {last}", None, "named_" + name_key,
                lambda n=display_name, p=named_id: select_patient(n, p),
            )
        if status_filter in ("All", "Unlinked Sessions") and (not search_term or search_term.casefold() in "unlinked firestore sessions"):
            roster_entry(
                "Unlinked Firestore Sessions", "Unlinked Sessions",
                f"{len(demo_sessions)} sessions", None,
                "Records without an explicit Patient name; not one verified person", None,
                "view_firestore_demo",
                lambda: select_patient("Unlinked Firestore Sessions", FIRESTORE_DEMO_ID),
            )

    elif st.session_state.selected_patient_id == EPIC_DEMO_PROFILE_ID:
        render_epic_demo_profile()

    else:

        patient = st.session_state.selected_patient

        pid = st.session_state.selected_patient_id



        if st.button("← Back to Patients", key="profile_top_back"):
            st.session_state.selected_patient = None
            st.session_state.selected_patient_id = None
            st.rerun()
        profile_sessions = get_all_sessions(pid, patient)
        latest_profile = profile_sessions[-1] if profile_sessions else None
        with st.container(border=True):
            st.markdown('<span class="hs-profile-banner"></span>', unsafe_allow_html=True)
            top_left, top_right = st.columns([4, 1], vertical_alignment="center")
            with top_left:
                st.subheader(patient)
                st.caption("HomeStretch · Patient profile" if pid != FIRESTORE_DEMO_ID else
                           "Unlinked recordings · Testing profile, not an individual patient")
            with top_right:
                if pid == FIRESTORE_DEMO_ID:
                    st.caption("Unlinked")
                else:
                    render_status(derive_firestore_status(profile_sessions))
        k1,k2,k3=st.columns(3)
        k1.metric("Recorded sessions",len(profile_sessions))
        k2.metric("Latest activity",format_session_time(latest_profile.get("session_time")) if latest_profile else "—")
        k3.metric("Review flags",sum(needs_review(x) for x in profile_sessions))
        if pid == FIRESTORE_DEMO_ID:
            st.caption("These recordings have no explicit patient name and may belong to different people.")
        else:
            st.caption("Prototype status is based on available recordings, not verified adherence or clinical safety.")
        render_pain_flag(get_latest_pain(pid))

        tab1, tab2, tab3 = st.tabs(["Information", "Sessions", "Latest Session"])



        # -----------------------

        # INFORMATION TAB

        # -----------------------

        with tab1:
            st.caption("Clinical details and prescriptions are shown only when available in Firestore. No inferred patient history is displayed.")
            left, right = st.columns(2, gap="medium")
            with left:
                with st.container(border=True):
                    white_card()
                    section_heading("Clinical Overview")
                    st.caption("Stroke history, assistive devices and clinical risks have not been entered in the current session records.")
                with st.container(border=True):
                    white_card()
                    section_heading("Functional Baseline")
                    st.caption("No verified functional assessment is available.")
            with right:
                with st.container(border=True):
                    white_card()
                    section_heading("Current Program")
                    st.caption("No verified exercise prescription is available in these session documents.")
                    if st.button("Open Program Builder", key="open_program_builder"):
                        st.session_state.page = "builder"
                        st.rerun()
                with st.container(border=True):
                    white_card()
                    section_heading("Clinician Notes")
                    st.caption("No clinician notes are stored in these Firestore session documents.")
                    n1,n2=st.columns(2)
                    n1.button("View All Notes",disabled=True)
                    n2.button("Add Note",disabled=True)

            with st.container(border=True):
                white_card()
                section_heading("Recorded Sessions")
                profile_sessions = get_all_sessions(pid, patient)
                st.caption("Firestore recordings. Unlinked recordings are not assigned to named patients.")
                q1,q2,q3=st.columns(3)
                q1.metric("Sessions",len(profile_sessions))
                q2.metric("Typical classifications",sum(str(x.get("classification","")).casefold()=="typical" for x in profile_sessions))
                q3.metric("Atypical classifications",sum(str(x.get("classification","")).casefold()=="atypical" for x in profile_sessions))
                if profile_sessions:
                    with st.expander("View recording details"):
                        st.dataframe(pd.DataFrame([{
                            "Date":format_session_time(x.get("session_time")),
                            "Exercise":(x.get("exercise") or {}).get("name","—") if isinstance(x.get("exercise"),dict) else "—",
                            "Recording":x.get("file_name") or x.get("raw_file") or "—",
                            "Classification":x.get("classification") or "Not analyzed",
                        } for x in reversed(profile_sessions)]),hide_index=True,use_container_width=True)

        # -----------------------

        # SESSION TAB

        # -----------------------

        with tab2:
            sessions = get_all_sessions(pid, patient)

            with st.container(border=True):
                white_card()
                section_heading("Session History")
                st.caption("Open previous recordings and review individual session details.")
                if st.button("View Session History →", key=f"history_{pid}", use_container_width=True):
                    st.session_state.history_patient_id = pid
                    st.session_state.history_patient_name = patient
                    st.session_state.page = "session_history"
                    st.rerun()

            section_heading("Session Overview")
            if not sessions:
                st.info("No Firestore sessions are associated with this profile.")
            else:
                st.metric("Total Recorded Sessions", len(sessions))
                rep_sessions = [s for s in sessions if s.get("num_reps") is not None]
                duration_sessions = [s for s in sessions if s.get("duration_sec") is not None]
                if rep_sessions:
                    rep_df = pd.DataFrame({
                        "Session": [format_session_time(s.get("session_time")) + " · " + s.get("session_label", "") for s in rep_sessions],
                        "Reps": [float(s["num_reps"]) for s in rep_sessions],
                    })
                    with st.container(border=True):
                        white_card()
                        section_heading("Repetitions per Session")
                        st.bar_chart(rep_df.set_index("Session")["Reps"])
                else:
                    st.info("Repetition analysis is not yet available for these sessions.")

                if duration_sessions:
                    duration_df = pd.DataFrame({
                        "Session": [format_session_time(s.get("session_time")) + " · " + s.get("session_label", "") for s in duration_sessions],
                        "Duration (sec)": [float(s["duration_sec"]) for s in duration_sessions],
                    })
                    with st.container(border=True):
                        white_card()
                        section_heading("Session Duration Trend")
                        st.line_chart(duration_df.set_index("Session")["Duration (sec)"])
                else:
                    st.info("Session duration data is not yet available.")

        st.divider()



        with tab3:

            latest = get_all_sessions(pid, patient)[-1] if get_all_sessions(pid, patient) else None



            if latest is None:

                st.info("No Firestore sessions are associated with this profile.")

            else:

                section_heading("Latest Session")

                st.caption(format_session_time(latest.get("session_time")))

                with st.container(border=True):
                    white_card()
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



    if st.button("⬅ Back to Session History" if st.session_state.get("session_detail_return") == "session_history" else "⬅ Back to Patient Profile"):

        st.session_state.page = st.session_state.get("session_detail_return", "patients")
        st.rerun()



# -----------------------

# SESSION DETAIL PAGE

# -----------------------

# -----------------------
# SESSION HISTORY PAGE
# -----------------------

elif st.session_state.page == "session_history":
    pid = st.session_state.get("history_patient_id")
    patient_name = st.session_state.get("history_patient_name")
    section_heading("Session History")
    st.caption(f"{patient_name or 'Patient'} · Previous exercise recordings")
    if st.button("← Back to Patient Profile", key="back_from_history"):
        st.session_state.page = "patients"
        st.rerun()

    sessions = get_all_sessions(pid, patient_name)
    st.caption(f"{len(sessions)} recorded sessions")
    if not sessions:
        st.info("No session history available.")
    else:
        for s in reversed(sessions):
            exercise = s.get("exercise") or {}
            exercise_name = exercise.get("name", "Exercise Session") if isinstance(exercise, dict) else "Exercise Session"
            when = format_session_time(s.get("session_time"))
            with st.container(border=True):
                white_card()
                info_col, action_col = st.columns([4, 1])
                with info_col:
                    st.markdown(f"**{exercise_name}**")
                    st.caption(when)
                    st.write(f"Classification: {s.get('classification') or 'Not analyzed'}")
                    st.write(f"Reps: {s['num_reps']}" if s.get("num_reps") is not None else "Reps: Not available")
                    st.caption(s.get("file_name") or s.get("raw_file") or "Recording filename unavailable")
                with action_col:
                    if st.button("View Details", key=f"history_detail_{s['id']}"):
                        st.session_state.selected_session = s["id"]
                        st.session_state.selected_session_data = s
                        st.session_state.selected_session_time = when
                        st.session_state.selected_session_label = s.get("session_label", "Session")
                        st.session_state.session_detail_return = "session_history"
                        st.session_state.page = "session_detail"
                        st.rerun()


elif st.session_state.page == "session_detail":



    session_data = st.session_state.selected_session_data



    session_label = st.session_state.get("selected_session_label", "Session")

    session_time = st.session_state.get("selected_session_time")



    section_heading("Session Details")

    st.subheader(session_label)



    if session_time:

        st.caption(session_time)



    if st.button("⬅ Back to Session History" if st.session_state.get("session_detail_return") == "session_history" else "⬅ Back to Patient Profile"):

        st.session_state.page = st.session_state.get("session_detail_return", "patients")
        st.rerun()



    if session_data is None:

        st.info("No session selected.")

    else:

        with st.container(border=True):
            white_card()
            render_session_metrics(session_data)