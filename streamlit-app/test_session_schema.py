import unittest
from datetime import datetime
from session_schema import normalize_session, patient_key

class SessionTests(unittest.TestCase):
    def test_v2_patient_and_pain(self):
        d = normalize_session({'patient': {'id':'001', 'name':'Test'}, 'started_at':'2026-10-30T12:00:00Z', 'pain':{'before':{'pain':0},'after':{'pain':3}}})
        self.assertEqual(patient_key(d),'id:001')
        self.assertEqual(d['pre_exercise_pain'],0)
        self.assertEqual(d['pain_level'],3)
        self.assertIsInstance(d['started_at'],datetime)
    def test_legacy_and_no_invented_quality(self):
        d=normalize_session({'Patient':' Test Name ', 'exercise':'Bicep Curls','rep_count':4})
        self.assertEqual(patient_key(d),'name:test name')
        self.assertEqual(d['exercise']['name'],'Bicep Curls')
        self.assertEqual(d['num_reps'],4)
        self.assertNotIn('num_typical',d)
    def test_same_names_different_ids(self):
        self.assertNotEqual(patient_key({'patient_id':'001','patient_name':'Test'}),patient_key({'patient_id':'002','patient_name':'Test'}))
    def test_older_mobile_reps(self):
        d=normalize_session({'rep_durations':[2.5], 'rep_assessments':[{'rep':1,'assessable':True,'features_outside_baseline':['gyro_mean_deg_s']}]})
        self.assertEqual(d['num_atypical'],1)
        self.assertEqual(d['rep_assessments'][0]['duration_sec'],2.5)
    def test_unlinked(self):
        self.assertIsNone(patient_key(normalize_session({})))
if __name__=='__main__': unittest.main()
