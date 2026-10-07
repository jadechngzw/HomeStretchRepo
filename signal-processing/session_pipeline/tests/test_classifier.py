import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from session_pipeline.classifier import classify, FEATURES


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        rng=np.random.default_rng(42)
        frame=pd.DataFrame(rng.normal(size=(100,4)),columns=FEATURES)
        scaler=StandardScaler().fit(frame);model=IsolationForest(random_state=42).fit(scaler.transform(frame))
        self.model=self.root/'model.pkl';self.scaler=self.root/'scaler.pkl'
        joblib.dump(model,self.model);joblib.dump(scaler,self.scaler)
    def tearDown(self):self.tmp.cleanup()
    def inputs(self):
        t=np.arange(0,8,.02)
        a=np.column_stack([t,np.zeros(len(t)),np.cos(2*np.pi*t/2.5),np.ones(len(t)),np.ones(len(t))])
        imu={'axis':'y','repetitions':[dict(start_sec=0,end_sec=2.5,classification='Unknown'),
                                     dict(start_sec=2.5,end_sec=5,classification='Unknown')]}
        return imu,a
    def test_score_threshold_direction_and_provenance(self):
        imu,a=self.inputs();info=classify(imu,a,self.model,self.scaler,threshold=-1)
        self.assertEqual(imu['typical_reps'],2);self.assertEqual(info['feature_order'],FEATURES)
        self.assertEqual(len(info['model_sha256']),64)
        self.assertIn('anomaly_score',imu['repetitions'][0])
        imu,a=self.inputs();classify(imu,a,self.model,self.scaler,threshold=1)
        self.assertEqual(imu['atypical_reps'],2)
    def test_long_gap_stays_unknown(self):
        imu,a=self.inputs();a[(a[:,0]>.4)&(a[:,0]<1.2),4]=0
        classify(imu,a,self.model,self.scaler)
        self.assertEqual(imu['repetitions'][0]['classification'],'Unknown')
        self.assertEqual(imu['classification'],'Unknown')
    def test_feature_mismatch_rejected(self):
        scaler=StandardScaler().fit(pd.DataFrame(np.ones((5,4)),columns=['wrong','names','for','model']))
        joblib.dump(scaler,self.scaler);imu,a=self.inputs()
        with self.assertRaisesRegex(ValueError,'feature schema'):classify(imu,a,self.model,self.scaler)

if __name__=='__main__':unittest.main()
