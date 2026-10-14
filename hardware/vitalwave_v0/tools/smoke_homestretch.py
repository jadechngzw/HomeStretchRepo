"""Test automatic GUI Stop→worker→JSON using simulated BLE, never cloud upload."""
import sys, tempfile, time, json, shutil, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import tkinter as tk
from desktop.controller import Controller
from desktop.homestretch import HomeStretchBridge
from desktop.ui.window import Window
folder=Path(tempfile.mkdtemp(prefix='homestretch-gui-'))
config=json.loads((ROOT/'homestretch_integration.json').read_text());config['recordings_dir']=str(folder)
(folder/'homestretch_integration.json').write_text(json.dumps(config))
root=tk.Tk();root.withdraw();controller=Controller(demo=True)
if controller.pipeline:controller.pipeline.close()
controller.pipeline=HomeStretchBridge(folder,controller.post,demo=True)
window=Window(root,controller);window.folder.set(str(folder));window.hs_enabled.set(True)
assert len(window.exercise_ids)==15
exercise=os.environ.get('HS_TEST_EXERCISE','bicep_curl')
window.hs_exercise.set(controller.pipeline.catalog[exercise]['name']);window.exercise_changed()
window.hs_patient.set('demo-smoke');window.hs_upload.set(True);window.hs_classifier.set(True)
window.acceleration.set(True);window.gyroscope.set(True);window.imu_rate.set('50')
window.ppg_enabled.set(True);window.select_leds(4);window.ppg_rate.set('50')
phase=0;began=time.monotonic();started=0;failure=None

def step():
 global phase,started,failure
 try:
  if time.monotonic()-began>65:raise AssertionError('Timed out: '+window.hs_status.get())
  if phase==0:window.action('scan');phase=1
  elif phase==1 and window.devices and not window.busy:window.connect();phase=2
  elif phase==2 and window.connected and not window.busy:window.start();phase=3
  elif phase==3 and window.recording:
   started=time.monotonic();window.hs_patient.set('changed-after-start');phase=4
  elif phase==4 and time.monotonic()-started>5:window.action('stop');phase=5
  elif phase==5:
   jobs=list(controller.pipeline.queue.glob('*.json'))
   if jobs:
    job=json.loads(jobs[0].read_text())
    if job['state']=='pending_retry':raise AssertionError(job['error'])
    if job['state']=='local_only':
     result=json.loads(Path(job['output']).read_text())
     meta=json.loads(Path(job['csv']).with_suffix('.json').read_text())
     assert meta['demo'] and meta['ended_utc']
     assert meta['homestretch']['patient_id']=='demo-smoke'
     assert result['patient_id']=='demo-smoke' and result['recording']['demo']
     assert result['exercise']['id']==exercise
     if exercise!='bicep_curl':
      assert result['imu']['accepted_reps'] is not None
      assert result['processing']['classifier']['status']=='experimental_transfer'
     assert 'receipt' not in job and Path(job['csv']).exists()
     print('PASS: GUI simulated BLE Start/Stop → raw + frozen metadata → background processing → results.json; demo cloud upload suppressed.',folder,flush=True)
     phase=6;window.close();return
 except Exception as exc:
  failure=exc;print('FAIL:',repr(exc),flush=True);window.close();return
 root.after(100,step)
root.after(100,step);root.mainloop();controller.loop.call_soon_threadsafe(controller.loop.stop)
if failure:raise failure
