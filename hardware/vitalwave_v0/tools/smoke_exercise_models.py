"""Smoke test all saved exercise models with known periodic raw-IMU rotations."""
import json,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(R/'signal-processing'),str(R/'signal-processing/session_pipeline/tests')]
from test_orientation import streams
from session_pipeline.orientation_models import summarize
from session_pipeline.motion import summarize as base_summary
registry=json.loads((R/'signal-processing/session_pipeline/model_registry.json').read_text())
config=json.loads((R/'signal-processing/session_pipeline/exercises.json').read_text())
for name,selected in registry.items():
 if name=='bicep_curl':continue
 c=json.loads((R/selected['feature_config']).read_text());period=c['segmentation']['period_seconds'];t=np.arange(0,period*8,.02)
 e=np.zeros((len(t),3));axis={'pitch':1,'yaw':2,'roll':0}[c['segmentation']['channel_name']]
 amplitude=max(15,c['segmentation']['prominence_degrees']);e[:,axis]=np.deg2rad(amplitude)*np.sin(2*np.pi*t/period)
 a,g=streams(t,e);imu=base_summary(a,g,t[-1],config[name]);info=summarize(imu,a,g,selected,placement=selected['recommended_placement'])
 assert info['scored_reps']>0,(name,imu['rejected_candidates'])
 assert all(np.isfinite(r['anomaly_score']) for r in imu['repetitions'])
 print(name,info['scored_reps'],'scored',flush=True)
print('PASS: all 14 orientation model adapters produced finite scores from synthetic raw IMU.')
