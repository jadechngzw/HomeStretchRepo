import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
from datetime import datetime

# --- Firebase Init ---
if not firebase_admin._apps:
    KEY_PATH = Path(__file__).parent / "homestretch-pipeline-5f8f03e61254.json"
    cred = credentials.Certificate(str(KEY_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Session State ---
# Replace these with your actual auth session state values
CURRENT_USER_ID = st.session_state.get("user_id", "patient123")
CURRENT_USER_ROLE = st.session_state.get("role", "patient")  # "patient" or "pt"

if "active_conversation" not in st.session_state:
    st.session_state.active_conversation = None

# --- Helpers ---
def get_conversations(user_id):
    """Fetch all conversations this user is part of, sorted by latest message."""
    convos = db.collection("messages") \
        .where("meta.participants", "array_contains", user_id) \
        .stream()
    result = []
    for doc in convos:
        data = doc.to_dict()
        meta = data.get("meta", {})
        result.append({
            "id": doc.id,
            "last_message": meta.get("last_message", ""),
            "last_timestamp": meta.get("last_timestamp"),
            "unread": meta.get(f"unread_{CURRENT_USER_ROLE}", False),
            "participants": meta.get("participants", []),
        })
    # Sort by latest message, unread first
    result.sort(key=lambda x: (
        not x["unread"],
        x["last_timestamp"] or datetime.min
    ), reverse=True)
    return result

def get_thread(conversation_id):
    """Fetch all messages in a conversation thread."""
    msgs = db.collection("messages").document(conversation_id) \
        .collection("thread") \
        .order_by("timestamp") \
        .stream()
    return [m.to_dict() for m in msgs]

def send_message(conversation_id, text):
    """Send a message and update conversation metadata."""
    now = firestore.SERVER_TIMESTAMP
    thread_ref = db.collection("messages").document(conversation_id).collection("thread")
    thread_ref.add({
        "sender_id": CURRENT_USER_ID,
        "text": text,
        "timestamp": now,
    })
    # Update meta — mark unread for the OTHER party
    other_role = "pt" if CURRENT_USER_ROLE == "patient" else "patient"
    db.collection("messages").document(conversation_id).set({
        "meta": {
            "last_message": text,
            "last_timestamp": now,
            f"unread_{other_role}": True,
            f"unread_{CURRENT_USER_ROLE}": False,
        }
    }, merge=True)

def mark_as_read(conversation_id):
    """Mark conversation as read for the current user."""
    db.collection("messages").document(conversation_id).set({
        "meta": {f"unread_{CURRENT_USER_ROLE}": False}
    }, merge=True)

def get_display_name(participant_id):
    """Swap this with a real name lookup from your users collection."""
    names = {
        "patient123": "You",
        "pt456": "Dr. Smith (PT)",
    }
    return names.get(participant_id, participant_id)

# --- UI ---
st.title("Messages")

conversations = get_conversations(CURRENT_USER_ID)

# --- Chat List View ---
if st.session_state.active_conversation is None:
    if not conversations:
        st.info("No conversations yet.")
    else:
        for convo in conversations:
            other_participant = next(
                (p for p in convo["participants"] if p != CURRENT_USER_ID),
                "Unknown"
            )
            display_name = get_display_name(other_participant)
            unread = convo["unread"]

            # Format timestamp
            ts = convo["last_timestamp"]
            ts_str = ts.strftime("%b %d, %I:%M %p") if ts and hasattr(ts, "strftime") else ""

            # Unread badge
            badge = "🔴 " if unread else ""

            col1, col2, col3 = st.columns([1, 4, 1])
            with col1:
                st.image(str(Path(__file__).parent / "caregiverphoto.jpg"), width=80)
            with col2:
                if st.button(
                    f"{badge}**{display_name}**\n{convo['last_message']}",
                    key=convo["id"],
                    use_container_width=True
                ):
                    st.session_state.active_conversation = convo["id"]
                    mark_as_read(convo["id"])
                    st.rerun()
            with col3:
                st.caption(ts_str)

            st.divider()

# --- Thread View ---
else:
    conversation_id = st.session_state.active_conversation

    if st.button("← Back to chats"):
        st.session_state.active_conversation = None
        st.rerun()

    # Get other participant name for header
    convo_data = next((c for c in conversations if c["id"] == conversation_id), None)
    if convo_data:
        other_participant = next(
            (p for p in convo_data["participants"] if p != CURRENT_USER_ID),
            "Unknown"
        )
        col1, col2 = st.columns([4, 4])
        with col1:
            st.markdown(f"<h3 style='white-space: nowrap;'>{get_display_name(other_participant)}</h3>", unsafe_allow_html=True)
        with col2:
            st.image(str(Path(__file__).parent / "caregiverphoto.jpg"), width=400)
    
    st.divider()

    # Display thread
    thread = get_thread(conversation_id)
    for msg in thread:
        sender = msg.get("sender_id")
        text = msg.get("text", "")
        ts = msg.get("timestamp")
        ts_str = ts.strftime("%b %d, %I:%M %p") if ts and hasattr(ts, "strftime") else ""
        is_me = sender == CURRENT_USER_ID

        if is_me:
            st.markdown(
                f"""
                <div style="text-align:right; margin-bottom:10px;">
                    <span style="background-color:#dbe5f1; padding:10px 15px;
                    border-radius:18px 18px 0px 18px; display:inline-block; color:black;">
                        {text}
                    </span><br>
                    <small style="color:gray;">{ts_str}</small>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="text-align:left; margin-bottom:10px;">
                    <span style="background-color:#f0f0f0; padding:10px 15px;
                    border-radius:18px 18px 18px 0px; display:inline-block; color:black;">
                        {text}
                    </span><br>
                    <small style="color:gray;">{ts_str}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    # Message input
    with st.form("message_form", clear_on_submit=True):
        new_message = st.text_input("Type a message...", label_visibility="collapsed")
        submitted = st.form_submit_button("Send", use_container_width=True)
        if submitted and new_message.strip():
            send_message(conversation_id, new_message.strip())
            st.rerun()