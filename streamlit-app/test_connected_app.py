import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import clinician_backend as backend
from clinician_charts import metric_frame

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
        with patch.object(backend,'clinician',return_value=('c',{'display_name':'Test clinician'})),patch.object(backend,'linked_patients',return_value=[{'patient_id':'p','patient_name':'Test patient'}]),patch.object(backend,'sessions',return_value=[session]),patch.object(backend,'surveys',return_value={}):
            page.run()
        self.assertFalse(page.exception)
        self.assertFalse(page.error)

if __name__=='__main__':unittest.main()
