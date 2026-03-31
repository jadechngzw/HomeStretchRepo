import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
import plotly.graph_objects as go

# --- Firebase Init ---
if not firebase_admin._apps:
    KEY_PATH = Path(__file__).parent / "homestretch-pipeline-5f8f03e61254.json"
    cred = credentials.Certificate(str(KEY_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Fetch All Sessions ---
@st.cache_data(ttl=60)
def get_all_sessions():
    docs = db.collection("sessions").stream()
    sessions = []
    for doc in docs:
        data = doc.to_dict()
        data["doc_id"] = doc.id  # e.g. "001_BicepCurl_L_T"
        sessions.append(data)
    return sessions

sessions = get_all_sessions()

# --- Derived Stats ---
total_sessions = len(sessions)
total_minutes = round(sum(s.get("duration_sec", 0) for s in sessions) / 60, 1)
total_reps = sum(s.get("num_reps", 0) for s in sessions)

# Parse exercise types from doc IDs (e.g. "001_BicepCurl_L_T" → "Bicep Curl")
def parse_exercise_type(doc_id):
    parts = doc_id.replace("Trimmed_", "").split("_")
    # Remove leading number and trailing side/type identifiers
    name_parts = [p for p in parts[1:] if p not in ("L", "R", "T", "A")]
    return " ".join(name_parts)

exercise_types = list({parse_exercise_type(s["doc_id"]) for s in sessions})

# Tremor info
tremor_levels = [s.get("tremor_level", "N/A") for s in sessions]
classifications = [s.get("classification", "") for s in sessions]
good_control_count = sum(1 for c in classifications if c in ("Good Control", "Very Smooth"))

# --- UI ---
st.title("Progress")
st.markdown("### You're doing great!")
st.markdown("**Movement this week:**")
st.write(f"{total_sessions} sessions completed")
st.write(f"{total_minutes} minutes of movement")
st.write(f"{total_reps} total reps logged")

# --- Chart: Reps per session ---
st.markdown("")
if sessions:
    labels = [s["doc_id"] for s in sessions]
    reps = [s.get("num_reps", 0) for s in sessions]
    classifications_list = [s.get("classification", "") for s in sessions]

    colors = []
    for c in classifications_list:
        if c in ("Good Control", "Very Smooth"):
            colors.append("#2d6a4f")  # dark green
        elif c == "Poor Control / Tremor Dominant":
            colors.append("#d62828")  # red
        else:
            colors.append("#a8dadc")  # neutral fallback

    fig = go.Figure(go.Bar(
        x=labels,
        y=reps,
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Reps: %{y}<extra></extra>"
    ))

    fig.update_layout(
        xaxis_title="Session",
        yaxis_title="Reps",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-45,
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No session data yet.")

st.caption("Any movement counts")

# --- What You Worked On ---
st.markdown("### What you worked on:")

def pill(text):
    st.markdown(
        f"""
        <div style="
            background-color:#dbe5f1;
            padding:10px;
            border-radius:20px;
            margin-bottom:8px;
            width:100%;
            color:black;
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )

for ex in exercise_types:
    pill(ex)

# --- Accomplishments ---
longest_session = max((s.get("duration_sec", 0) for s in sessions), default=0)
most_reps = max((s.get("num_reps", 0) for s in sessions), default=0)
best_snr = max((s.get("snr_db", 0) for s in sessions), default=0)

st.markdown("### Accomplishments:")
st.markdown(
    f"""
    <div style="border-left:5px solid #dbe5f1; padding-left:10px;">
        Longest Session: {round(longest_session / 60, 1)} min<br><br>
        Most Reps in a Session: {most_reps}<br><br>
        Sessions with Good Control: {good_control_count} / {total_sessions} 🎉
    </div>
    """,
    unsafe_allow_html=True
)

# --- Tremor Summary ---
st.markdown("### Exercise Summary:")
tremor_df = pd.DataFrame({
    "Session": [s["doc_id"] for s in sessions],
    "Tremor Level": [s.get("tremor_level", "N/A") for s in sessions],
    "Classification": [s.get("classification", "N/A") for s in sessions],
})
st.dataframe(tremor_df, use_container_width=True)