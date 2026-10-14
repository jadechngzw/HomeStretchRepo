"""Durable local post-recording jobs. Errors retain raw data/results for retry."""
import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from .pipeline import process, clean
from .upload import upload_result


def atomic_json(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as f:
        json.dump(clean(data),f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def run_job(path, uploader=upload_result):
    path=Path(path)
    with path.with_suffix('.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        job=json.loads(path.read_text())
        if job['state'] in ('uploaded','local_only'):return job
        try:
            job.update(state='processing',error=None,attempts=job.get('attempts',0)+1)
            atomic_json(path,job)
            out=Path(job['output']);config=job['config']
            if out.exists():
                result=json.loads(out.read_text())
            else:
                result=process(job['csv'],patient_id=config['patient_id'],exercise_id=config['exercise_id'],
                               body_side=config['side'],axis=config['axis'],ppg_channel=config['ppg_channel'],
                               rep_goal=config.get('rep_goal'),max_hr_bpm=config.get('max_hr_bpm'),
                               experimental_model=config.get('model'),experimental_scaler=config.get('scaler'),
                               orientation_classification=config.get('orientation_classification',True),
                               orientation_sidecar=out.with_name('orientation.csv'),sensor_placement=config.get('sensor_placement','wrist'))
                result['data_use']=config['data_use']
                atomic_json(out,result)
            job['session_id']=result['session_id']
            if result['recording'].get('demo') or not config.get('upload',True):
                job.update(state='local_only',error=None)
            else:
                job['state']='uploading';atomic_json(path,job)
                receipt=uploader(result,config['project'])
                job.update(state='uploaded',receipt=receipt,error=None)
            job['finished_at']=datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            job.update(state='pending_retry',error=f'{type(exc).__name__}: {exc}')
        atomic_json(path,job)
        return job


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',required=True)
    args=p.parse_args();queue=Path(args.queue);queue.mkdir(parents=True,exist_ok=True)
    for path in sorted(queue.glob('*.json')):
        try:
            job=run_job(path)
            if job:print(json.dumps({'job':path.stem,'state':job['state'],'error':job.get('error'),'output':job['output']}),flush=True)
        except Exception as exc:print(json.dumps({'job':path.stem,'state':'error','error':str(exc)}),flush=True)

if __name__=='__main__':main()
