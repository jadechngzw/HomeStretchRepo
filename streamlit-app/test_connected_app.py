import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import clinician_backend as backend
from clinician_charts import metric_frame, session_trend_frame, rep_duration_frame, metric_trend_frame, is_bicep_curl

class ChartTests(unittest.TestCase):
    def test_no_fake_values_for_legacy_or_unassessed_rows(self):
        self.assertEqual(metric_frame({'num_reps':10},'gyro_peak_deg_s'),([],None))
        row={'rep_assessments':[{'rep':1,'assessable':False,'metrics':{'x':12}},{'rep':2,'assessable':True,'metrics':{'x':float('nan')}}]}
        self.assertEqual(metric_frame(row,'x'),([],None))
    def test_uses_recording_baseline_and_keeps_zero(self):
        row={'baseline':{'reference':{'stats':{'x':{'mean':5,'lower':0,'upper':10}}}},'rep_assessments':[{'rep':1,'assessable':True,'metrics':{'x':0}},{'rep':2,'assessable':True,'metrics':{'x':11}}]}
        values,band=metric_frame(row,'x')
        self.assertEqual(values[0]['value'],0)
        self.assertEqual(values[1]['status'],'Outside baseline')
        self.assertEqual(band['upper'],10)

class TrendTests(unittest.TestCase):
    def test_bicep_detection(self):
        self.assertTrue(is_bicep_curl({'exercise':{'id':'bicep-curls','name':'Bicep Curls'}}))
        self.assertFalse(is_bicep_curl({'exercise':{'id':'squat','name':'Squat'}}))
    def test_trends_skip_missing_values(self):
        rows=[{'id':'a','started_at':'2026-11-02T17:00:00Z','num_reps':3,'num_typical':2,'num_atypical':1,'num_unassessed':0,
               'rep_assessments':[{'rep':1,'duration_sec':2.0,'assessable':True,'metrics':{'x':4}},{'rep':2,'duration_sec':None,'assessable':True,'metrics':{'x':6}},{'rep':3,'duration_sec':3.0,'assessable':False,'metrics':{'x':99}}],
               'baseline':{'reference':{'stats':{'x':{'mean':5,'lower':4.5,'upper':5.5}}}}},
              {'id':'b','num_reps':2}]
        counts=session_trend_frame(rows)
        self.assertEqual(sorted((r['classification'],r['reps']) for r in counts),[('Outside baseline',1),('Typical',2),('Unassessed',0)])
        durations=rep_duration_frame(rows)
        self.assertEqual(len(durations),1);self.assertAlmostEqual(durations[0]['mean'],2.5)
        trend=metric_trend_frame(rows,'x')
        self.assertEqual(trend[0]['mean'],5);self.assertEqual(trend[0]['outside'],2);self.assertEqual(trend[0]['upper'],5.5)

class AccessTests(unittest.TestCase):
    def test_role_checked_even_for_valid_token(self):
        db=MagicMock();db.collection.return_value.document.return_value.get.return_value.to_dict.return_value={'role':'patient'}
        with patch.object(backend,'database',return_value=db),patch.object(backend.auth,'verify_id_token',return_value={'uid':'p'}):
            with self.assertRaises(PermissionError):backend.clinician('token')
    def test_unlinked_patient_never_reaches_session_query(self):
        db=MagicMock();db.collection.return_value.where.return_value.stream.return_value=[]
        with patch.object(backend,'database',return_value=db),patch.object(backend,'clinician',return_value=('c',{})):
            with self.assertRaises(PermissionError):backend.sessions('token','other-patient')
        self.assertTrue(all(call.args[0]=='careLinks' for call in db.collection.call_args_list))
    def test_revoked_link_does_not_allow_messages(self):
        db=MagicMock();link=MagicMock();link.to_dict.return_value={'patient_id':'p','status':'revoked'}
        db.collection.return_value.where.return_value.stream.return_value=[link]
        with patch.object(backend,'database',return_value=db),patch.object(backend,'clinician',return_value=('c',{})):
            with self.assertRaises(PermissionError):backend.send_message('token','p','Hello','m')

class UITests(unittest.TestCase):
    def test_signed_out_screen_requires_login(self):
        from streamlit.testing.v1 import AppTest
        page=AppTest.from_file(str(Path(__file__).with_name('clinician_app.py'))).run()
        self.assertFalse(page.exception)
        self.assertEqual(page.subheader[0].value,'Clinician sign in')
    def test_connected_patient_chart_renders_without_database_access(self):
        from streamlit.testing.v1 import AppTest
        page=AppTest.from_file(str(Path(__file__).with_name('clinician_app.py')))
        page.session_state.clinician_token='test-token'
        session={'id':'s','exercise':{'name':'Test exercise'},'started_at':'2026-11-07','local_date':'2026-11-07','num_reps':1,'num_atypical':0,'num_unassessed':0,'baseline':{'reference':{'stats':{'gyro_peak_deg_s':{'mean':5,'lower':0,'upper':10}}}},'rep_assessments':[{'rep':1,'assessable':True,'metrics':{'gyro_peak_deg_s':5}}]}
        mocks=dict(clinician=('c',{'display_name':'Test clinician'}),linked_patients=[{'patient_id':'p','patient_name':'Test patient'}],sessions=[session],surveys={},invitations=[],messages=[])
        patches=[patch.object(backend,name,return_value=value) for name,value in mocks.items()]
        for item in patches: item.start()
        try:
            page.run()  # roster
            self.assertFalse(page.exception);self.assertFalse(page.error)
            page.session_state.selected_patient='p'
            page.run()  # patient profile with progress, sets and messages tabs
            self.assertFalse(page.exception);self.assertFalse(page.error)
            page.session_state.view='Messages';page.run()
            self.assertFalse(page.exception);self.assertFalse(page.error)
            page.session_state.view='Invite patients';page.run()
            self.assertFalse(page.exception);self.assertFalse(page.error)
        finally:
            for item in patches: item.stop()

if __name__=='__main__':unittest.main()
