"""Create a patient login for the HomeStretch app and its patients/{uid} record.

    Usage (from the repo root, with the service account JSON available as for the
    clinician app):

        python streamlit-app/create_patient.py --email test1@example.com \
            --password 'ChangeMe123' --name "Test Patient 1" \
            --diagnosis "Stroke, left hemiparesis" --affected-side left

    The printed uid is the patient_id that the app writes on every session.
"""

import argparse
import os
from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials, firestore

CREDENTIAL_NAME = "homestretch-pipeline-5f8f03e61254.json"


def init_firebase():
    if firebase_admin._apps:
        return
    here = Path(__file__).resolve().parent
    candidates = [here / CREDENTIAL_NAME, here.parent / CREDENTIAL_NAME]
    credential_file = next((p for p in candidates if p.is_file()), None)
    if credential_file:
        firebase_admin.initialize_app(credentials.Certificate(str(credential_file)))
    elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        firebase_admin.initialize_app()
    else:
        raise SystemExit(f"Service account JSON not found. Put {CREDENTIAL_NAME} next to this "
                         "script (never commit it) or set GOOGLE_APPLICATION_CREDENTIALS.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True, help="At least 6 characters")
    parser.add_argument("--name", required=True)
    parser.add_argument("--dob")
    parser.add_argument("--diagnosis")
    parser.add_argument("--affected-side", choices=["left", "right", "both"])
    parser.add_argument("--epic-patient-id")
    args = parser.parse_args()

    init_firebase()
    try:
        user = auth.get_user_by_email(args.email)
        print(f"Login already exists: {user.uid}")
    except auth.UserNotFoundError:
        user = auth.create_user(email=args.email, password=args.password, display_name=args.name)
        print(f"Created login: {user.uid}")

    record = {"name": args.name, "email": args.email, "created_at": firestore.SERVER_TIMESTAMP}
    for field in ("dob", "diagnosis", "affected_side", "epic_patient_id"):
        value = getattr(args, field)
        if value:
            record[field] = value
    firestore.client().collection("patients").document(user.uid).set(record, merge=True)
    print(f"Saved patients/{user.uid}")


if __name__ == "__main__":
    main()
