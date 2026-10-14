"""Explicit Firestore upload; preview is default and requires no credentials."""
import argparse
import json
import hashlib
from datetime import datetime
import re
from pathlib import Path


def make_document(result):
    if result.get('schema_version')!='1.0':raise ValueError('Unsupported results schema.')
    if not re.fullmatch(r'hs-[a-f0-9]{24}',result.get('session_id','')):
        raise ValueError('Invalid session ID.')
    if not isinstance(result.get('patient_id'),str) or not result['patient_id'].strip():
        raise ValueError('Patient ID is required.')
    doc=dict(result)
    imu=result['imu']
    # Compatibility fields for the existing HomeStretch Progress screen.
    doc.update(file_name=result['recording']['raw_file'],duration_sec=result['recording']['duration_sec'],
               num_reps=imu['accepted_reps'],num_typical=imu['typical_reps'],
               num_atypical=imu['atypical_reps'],classification=imu['classification'])
    payload=json.dumps(doc,allow_nan=False)
    if len(payload.encode())>800_000:
        raise ValueError('Summary too large. Store detailed time series in Cloud Storage instead.')
    return doc


def upload_result(result, project):
    """Create once, verify by readback, safely recognize identical retries."""
    from google.cloud import firestore
    from google.api_core.exceptions import AlreadyExists
    doc=make_document(result)
    fingerprint=hashlib.sha256(json.dumps(doc,sort_keys=True,allow_nan=False).encode()).hexdigest()
    client=firestore.Client(project=project)
    ref=client.collection('sessions').document(doc['session_id'])
    doc['_result_sha256']=fingerprint
    for key in ('started_at','ended_at'):
        doc[key]=datetime.fromisoformat(doc[key])
    doc['uploaded_at']=firestore.SERVER_TIMESTAMP
    try:
        ref.create(doc,retry=None,timeout=20)
    except AlreadyExists:
        pass
    saved=ref.get(retry=None,timeout=20)
    if not saved.exists or saved.to_dict().get('_result_sha256')!=fingerprint:
        raise ValueError('Document ID already contains a different result; refusing to overwrite.')
    return {'project':project,'document_path':ref.path,'verified':True}


def main():
    parser=argparse.ArgumentParser(description='Preview a session document or explicitly upload it using Application Default Credentials.')
    parser.add_argument('result')
    parser.add_argument('--project',required=True,help='Destination Google Cloud/Firebase project ID')
    parser.add_argument('--upload',action='store_true',help='Actually create the Firestore document')
    args=parser.parse_args()
    try:
        doc=make_document(json.loads(Path(args.result).read_text()))
        print(f"Destination: {args.project}/sessions/{doc['session_id']}")
        print(f"Patient: {doc['patient_id']}; schema: {doc['schema_version']}")
        if not args.upload:
            print('Preview only. No credentials loaded and nothing uploaded.')
            return
        receipt=upload_result(json.loads(Path(args.result).read_text()),args.project)
        print('Uploaded and verified: '+receipt['document_path'])
    except (ValueError,OSError,KeyError,ImportError) as exc:
        parser.exit(2,f'Upload not completed: {exc}\n')

if __name__=='__main__':main()
