import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from session_pipeline.automation import run_job, atomic_json

class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.path=self.root/'job.json'
        self.result={'session_id':'test','recording':{'demo':False}}
        self.job=dict(state='queued',csv='input.csv',output=str(self.root/'results.json'),attempts=0,
                      config=dict(patient_id='test',exercise_id='bicep_curl',side='right',axis='y',
                                  ppg_channel='ppg_green',project='test-project',data_use='development',upload=True))
        atomic_json(self.path,self.job)
    def tearDown(self):self.temp.cleanup()
    def test_offline_retry_reuses_saved_result(self):
        with patch('session_pipeline.automation.process',return_value=self.result) as process:
            def fail(*args):raise ConnectionError('offline')
            first=run_job(self.path,uploader=fail)
            self.assertEqual(first['state'],'pending_retry');self.assertTrue(Path(self.job['output']).exists())
            second=run_job(self.path,uploader=lambda r,p:{'verified':True})
            self.assertEqual(second['state'],'uploaded');self.assertEqual(process.call_count,1)
    def test_uploaded_job_does_not_upload_twice(self):
        calls=[]
        with patch('session_pipeline.automation.process',return_value=self.result):
            def upload(*args):calls.append(args);return {'verified':True}
            run_job(self.path,uploader=upload);run_job(self.path,uploader=upload)
            self.assertEqual(len(calls),1)
    def test_demo_never_uploaded(self):
        self.result['recording']['demo']=True
        with patch('session_pipeline.automation.process',return_value=self.result):
            job=run_job(self.path,uploader=lambda *a:self.fail('Demo upload attempted'))
        self.assertEqual(job['state'],'local_only')
    def test_processing_error_retained_for_retry(self):
        with patch('session_pipeline.automation.process',side_effect=ValueError('bad recording')):
            job=run_job(self.path,uploader=lambda *a:self.fail('Upload attempted'))
        self.assertEqual(job['state'],'pending_retry');self.assertIn('bad recording',job['error'])
        self.assertFalse(Path(self.job['output']).exists())

if __name__=='__main__':unittest.main()
