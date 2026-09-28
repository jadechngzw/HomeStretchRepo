from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

# --- Firebase Init ---
if not firebase_admin._apps:
    KEY_PATH = Path(__file__).parent / "homestretch-pipeline-5f8f03e61254.json"
    cred = credentials.Certificate(str(KEY_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Config ---
PATIENT_ID = "patient123"   # match your session state user_id
PT_ID = "pt456"             # your PT's user ID
CONVERSATION_ID = f"{PATIENT_ID}_{PT_ID}"
INTRO_MESSAGE = "Hi! I'm Dr. Smith, your physical therapist. Welcome to HomeStretch! Feel free to message me here anytime with questions about your exercises or progress. Looking forward to working with you! 💪"

now = datetime.now(timezone.utc)

# --- Create conversation meta ---
db.collection("messages").document(CONVERSATION_ID).set({
    "meta": {
        "participants": [PATIENT_ID, PT_ID],
        "last_message": INTRO_MESSAGE,
        "last_timestamp": now,
        "unread_patient": True,   # patient hasn't seen it yet
        "unread_pt": False,
    }
})

# --- Add introductory message to thread ---
db.collection("messages").document(CONVERSATION_ID) \
    .collection("thread").add({
        "sender_id": PT_ID,
        "text": INTRO_MESSAGE,
        "timestamp": now,
    })

print(f"✅ Conversation '{CONVERSATION_ID}' created successfully.")