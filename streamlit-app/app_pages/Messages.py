import streamlit as st
from datetime import datetime

st.set_page_config(page_title="HomeStretch | Messages", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1250px; padding-top: 1.4rem; padding-bottom: 2.5rem;}
.hs-header {background:#C4DCEF; border-radius:16px; padding:22px 28px; margin-bottom:20px;}
.hs-header h1 {color:#285F91; font-size:30px; margin:0; font-weight:650;}
.hs-header p {color:#527D9F; margin:5px 0 0; font-size:14px;}
.hs-panel-title {color:#285F91; font-size:19px; font-weight:650; margin-bottom:6px;}
.hs-muted {color:#73899C; font-size:13px;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-color:#BBD5E9; border-radius:15px;}
.stButton > button {border-radius:11px; border:1px solid #BBD5E9;}
.stButton > button[kind="primary"] {background:#367FBD; color:white; border-color:#367FBD;}
.stTextInput input {border-radius:10px; border-color:#BBD5E9;}
</style>
""", unsafe_allow_html=True)

# This is local prototype messaging only; no messages are sent to patients.
PATIENTS = [f"Patient {i}" for i in range(1, 10)]

if "hs_selected_chat" not in st.session_state:
    st.session_state.hs_selected_chat = None
if "hs_messages" not in st.session_state:
    st.session_state.hs_messages = {}
if "hs_chat_drafts" not in st.session_state:
    st.session_state.hs_chat_drafts = {}
for name in PATIENTS:
    st.session_state.hs_messages.setdefault(name, [])
    st.session_state.hs_chat_drafts.setdefault(name, "")

st.markdown('''<div class="hs-header"><h1>Messages</h1><p>Communicate with your patients</p></div>''', unsafe_allow_html=True)

left, right = st.columns([1, 2.15], gap="medium")

with left:
    with st.container(border=True):
        st.markdown('<div class="hs-panel-title">Patients</div>', unsafe_allow_html=True)
        search = st.text_input("Search conversations", placeholder="Search patients...", label_visibility="collapsed")
        with st.container(height=475, border=False):
            matches = [p for p in PATIENTS if search.strip().lower() in p.lower()]
            if not matches:
                st.caption("No matching patients.")
            for p in matches:
                selected = st.session_state.hs_selected_chat == p
                count = len(st.session_state.hs_messages[p])
                label = f"{'●  ' if selected else '○  '}{p}" + (f"  ·  {count}" if count else "")
                if st.button(label, key=f"hs_patient_{p}", use_container_width=True,
                             type="primary" if selected else "secondary"):
                    st.session_state.hs_selected_chat = p
                    st.rerun()

with right:
    with st.container(border=True):
        patient = st.session_state.hs_selected_chat
        if patient is None:
            st.markdown('<div class="hs-panel-title">Select a conversation</div>', unsafe_allow_html=True)
            st.caption("Choose a patient on the left to view or write messages.")
            st.info("Messages in this prototype are stored only in your current Streamlit session.")
        else:
            st.markdown(f'<div class="hs-panel-title">{patient}</div>', unsafe_allow_html=True)
            st.caption("Prototype conversation · not connected to the patient iOS app")
            with st.container(height=385, border=False):
                history = st.session_state.hs_messages[patient]
                if not history:
                    st.caption("No messages yet. Start the conversation below.")
                for msg in history:
                    role = "assistant" if msg["sender"] == "clinician" else "user"
                    with st.chat_message(role):
                        st.write(msg["text"])
                        st.caption(msg.get("time", ""))
            with st.form(key=f"hs_send_form_{patient}", clear_on_submit=True):
                msg = st.text_input("Message", placeholder="Type a message...", label_visibility="collapsed")
                sent = st.form_submit_button("Send message →", type="primary", use_container_width=True)
                if sent and msg.strip():
                    st.session_state.hs_messages[patient].append({
                        "sender": "clinician", "text": msg.strip(),
                        "time": datetime.now().strftime("%I:%M %p")
                    })
                    st.rerun()

st.caption("Prototype only: conversations are not persisted to Firestore and are not delivered to patients.")
