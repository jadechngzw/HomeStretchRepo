"""Run locally with trusted Admin credentials after creating the Auth user in Firebase."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import clinician_backend as backend
from firebase_admin import auth, firestore
parser=argparse.ArgumentParser(description='Grant clinician access to an existing Firebase Authentication account.')
parser.add_argument('--email',required=True)
parser.add_argument('--name',required=True)
args=parser.parse_args()
db=backend.database()
user=auth.get_user_by_email(args.email.strip())
db.collection('users').document(user.uid).set({'display_name':args.name.strip(),'role':'clinician','updated_at':firestore.SERVER_TIMESTAMP},merge=True)
print('Clinician access granted to the specified account.')
