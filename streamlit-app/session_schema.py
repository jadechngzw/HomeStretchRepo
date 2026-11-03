"""Normalize legacy and mobile v2 session documents without inventing results."""
from datetime import datetime


def patient_key(session):
    patient_id = session.get('patient_id')
    if patient_id is not None and str(patient_id).strip():
        return 'id:' + str(patient_id).strip()
    name = session.get('patient_name') or session.get('Patient') or session.get('patientName')
    return 'name:' + ' '.join(name.split()).casefold() if isinstance(name, str) and name.strip() else None


def normalize_session(source):
    data = dict(source)
    patient = data.get('patient')
    if isinstance(patient, dict):
        data.setdefault('patient_id', patient.get('id'))
        data.setdefault('patient_name', patient.get('name'))
    exercise = data.get('exercise')
    if isinstance(exercise, str):
        data['exercise'] = {'id': data.get('exercise_id'), 'name': exercise}
    for key in ('started_at', 'ended_at', 'startedAt', 'timestamp'):
        value = data.get(key)
        if isinstance(value, str):
            try:
                data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                pass
    data.setdefault('num_reps', data.get('rep_count'))
    pain = data.get('pain')
    if isinstance(pain, dict):
        before, after = pain.get('before'), pain.get('after')
        if isinstance(before, dict):
            data.setdefault('pre_exercise_pain', before.get('pain'))
        latest = after if isinstance(after, dict) else before
        if isinstance(latest, dict):
            data.setdefault('pain_level', latest.get('pain'))
    rows = data.get('rep_assessments')
    if isinstance(rows, list):
        durations = data.get('rep_durations') or []
        normalized = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            rep = dict(row)
            if 'duration_sec' not in rep and i < len(durations):
                rep['duration_sec'] = durations[i]
            if 'classification' not in rep:
                rep['classification'] = ('atypical' if rep.get('features_outside_baseline') else 'typical') if rep.get('assessable') is True and 'features_outside_baseline' in rep else 'unassessed'
            normalized.append(rep)
        data['rep_assessments'] = normalized
        for classification in ('typical', 'atypical', 'unassessed'):
            data.setdefault('num_' + classification, sum(r['classification'] == classification for r in normalized))
        data.setdefault('atypical_rep_ids', [r.get('rep') for r in normalized if r['classification'] == 'atypical'])
    return data
