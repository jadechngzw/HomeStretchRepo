"""Authenticated clinician access. No shared patient-data cache or implicit admin viewer."""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import firebase_admin
from firebase_admin import auth, credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import requests

PROJECT_ID = 'homestretch-pipeline'
WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDHakg-G1e5XTVGcC2gAl9qrHQ7FR6Z9yk')

def database():
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.ApplicationDefault(), {'projectId': PROJECT_ID})
    app = firebase_admin.get_app()
    if app.project_id != PROJECT_ID:
        raise ValueError('The server is configured for the wrong Firebase project.')
    return firestore.client()

def sign_in(email, password):
    database()
    response = requests.post(
        'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword',
        params={'key': WEB_API_KEY},
        json={'email': email.strip(), 'password': password, 'returnSecureToken': True}, timeout=15)
    if not response.ok:
        raise PermissionError('Could not sign in. Check your email and password.')
    token = response.json()['idToken']
    clinician(token)
    return token

def clinician(token):
    db = database()
    identity = auth.verify_id_token(token, check_revoked=True)
    profile = db.collection('users').document(identity['uid']).get().to_dict() or {}
    if profile.get('role') != 'clinician':
        raise PermissionError('This account does not have clinician access.')
    return identity['uid'], profile

def linked_patients(token):
    uid, _ = clinician(token)
    rows = database().collection('careLinks').where(filter=FieldFilter('clinician_id', '==', uid)).stream()
    result = []
    for row in rows:
        data = row.to_dict()
        if data.get('status') != 'active':
            continue
        patient = database().collection('patients').document(data['patient_id']).get().to_dict() or {}
        result.append(dict(data, id=row.id, patient_name=patient.get('full_name') or data.get('patient_name','Patient')))
    return result

def require_patient(token, patient_id):
    uid, _ = clinician(token)
    links = database().collection('careLinks').where(filter=FieldFilter('clinician_id', '==', uid)).stream()
    for row in links:
        data = row.to_dict()
        if data.get('patient_id') == patient_id and data.get('status') == 'active':
            return uid, dict(data, id=row.id)
    raise PermissionError('This patient is not connected to your account.')

def sessions(token, patient_id):
    require_patient(token, patient_id)
    docs = (database().collection('sessions').where(filter=FieldFilter('patient_id', '==', patient_id))
            .order_by('ended_at', direction=firestore.Query.DESCENDING).limit(100).stream())
    return [dict(d.to_dict(), id=d.id) for d in docs]

def surveys(token, patient_id, local_date):
    require_patient(token, patient_id)
    result = {}
    for phase in ('before', 'after'):
        row = database().collection('dailySurveys').document(f'{patient_id}_{local_date}_{phase}').get()
        data = row.to_dict()
        if data and data.get('patient_id') == patient_id:
            result[phase] = data
    return result

def invite_patient(token, email):
    uid, profile = clinician(token)
    patient = auth.get_user_by_email(email.strip())
    if patient.uid == uid:
        raise ValueError('Use the patient’s email, not your own.')
    target = database().collection('users').document(patient.uid).get().to_dict() or {}
    if target.get('role') == 'clinician':
        raise ValueError('That account is a clinician account.')
    link_id = f'{uid}_{patient.uid}'
    current = database().collection('careLinks').document(link_id).get().to_dict() or {}
    if current.get('status') == 'active':
        raise ValueError('This patient is already connected.')
    # One pending invitation per pair; no email is sent by this operation.
    ref = database().collection('careInvites').document(link_id)
    existing = ref.get().to_dict() or {}
    if existing.get('status') == 'pending' and existing.get('expires_at', datetime.min.replace(tzinfo=timezone.utc)) > datetime.now(timezone.utc):
        return
    ref.set({'patient_id':patient.uid, 'patient_name':patient.display_name or patient.email,
             'clinician_id':uid, 'clinician_name':profile.get('display_name') or 'Clinician',
             'link_id':link_id, 'status':'pending', 'created_at':firestore.SERVER_TIMESTAMP,
             'expires_at':datetime.now(timezone.utc)+timedelta(days=7)})

def invitations(token):
    uid, _ = clinician(token)
    return [dict(d.to_dict(), id=d.id) for d in database().collection('careInvites').where(filter=FieldFilter('clinician_id','==',uid)).stream()]

def messages(token, patient_id):
    _, link = require_patient(token, patient_id)
    docs = (database().collection('conversations').document(link['id']).collection('messages')
            .order_by('created_at', direction=firestore.Query.DESCENDING).limit(100).stream())
    return list(reversed([dict(d.to_dict(), id=d.id) for d in docs]))

def send_message(token, patient_id, text, message_id):
    uid, link = require_patient(token, patient_id)
    text = text.strip()
    if not text or len(text)>2000: raise ValueError('Enter a message of up to 2,000 characters.')
    ref = database().collection('conversations').document(link['id']).collection('messages').document(message_id)
    if ref.get().exists: return
    ref.create({'sender_id':uid,'text':text,'created_at':firestore.SERVER_TIMESTAMP})

def disconnect(token, patient_id):
    _, link = require_patient(token, patient_id)
    database().collection('careLinks').document(link['id']).update({'status':'revoked','revoked_at':firestore.SERVER_TIMESTAMP})


def update_clinician_profile(token, name):
    uid, _ = clinician(token)
    name = ' '.join(name.split())
    if not 2 <= len(name) <= 100:
        raise ValueError('Enter your full name (2–100 characters).')
    db = database()
    auth.update_user(uid, display_name=name)
    db.collection('users').document(uid).update({'display_name': name})
    # Existing invitations and connections carry a display-name snapshot.
    for collection in ('careLinks', 'careInvites'):
        for row in db.collection(collection).where(filter=FieldFilter('clinician_id','==',uid)).stream():
            row.reference.update({'clinician_name': name})
