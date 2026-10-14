"""Optional HomeStretch bridge; no scientific/cloud dependencies in the BLE loop."""
import hashlib
import json
import os
import subprocess
import threading
from pathlib import Path


def atomic(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as f:
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


class HomeStretchBridge:
    def __init__(self, root, post, demo=False):
        self.root=Path(root);self.post=post
        self.config=json.loads((self.root/'homestretch_integration.json').read_text())
        self.catalog=json.loads((Path(self.config['pipeline_parent'])/'session_pipeline/model_registry.json').read_text())
        self.queue=Path(self.config.get('recordings_dir',self.root/'recordings'))/('homestretch-demo-jobs' if demo else 'homestretch-jobs')
        self.queue.mkdir(parents=True,exist_ok=True)
        self.closed=threading.Event();self.wakeup=threading.Event()
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def validate(self, context):
        if not context or not context.get('enabled'):return None
        context=dict(context)
        if not context['patient_id'].strip():raise ValueError('Enter a HomeStretch patient/development ID before recording.')
        if context['exercise_id'] not in self.catalog:raise ValueError('Choose a supported exercise.')
        if context['side'] not in ('left','right') or context['axis'] not in ('x','y','z'):
            raise ValueError('Choose side and analysis axis.')
        if not Path(self.config['python']).is_file():raise ValueError('HomeStretch processing environment is missing.')
        context['project']=self.config['project']
        selected=self.catalog[context['exercise_id']]
        if context.get('sensor_placement','wrist') not in ('wrist','forearm','lower_leg'):raise ValueError('Choose sensor placement.')
        context['selected_model']=selected
        enabled=context.pop('experimental_classifier',False)
        context['orientation_classification']=enabled
        if enabled and selected['input']=='acceleration':
            repo=Path(self.config['pipeline_parent']).parent
            context['model']=str(repo/selected['model']);context['scaler']=str(repo/selected['scaler'])
        return context
    def enqueue(self, csv, context):
        if not context:return
        source=Path(csv).resolve()
        # Same recovery path always maps to the same durable job; never reassign identity.
        key=hashlib.sha256(str(source).encode()).hexdigest()[:24]
        path=self.queue/(key+'.json')
        if not path.exists():
            base=source.parent.parent if source.parent.name=='.recovery' else source.parent
            output=base/'processed'/source.stem/'results.json'
            atomic(path,dict(state='queued',csv=str(source),output=str(output),config=context,attempts=0))
        self.post('homestretch_status','Queued local processing → '+context['project'])
        self.wakeup.set()
    def retry(self):self.wakeup.set()
    def close(self):self.closed.set();self.wakeup.set()
    def _run(self):
        while not self.closed.is_set():
            try:
                env=os.environ.copy();env['PYTHONPATH']=self.config['pipeline_parent'];env['PYTHONDONTWRITEBYTECODE']='1'
                run=subprocess.run([self.config['python'],'-m','session_pipeline.automation','--queue',str(self.queue)],
                                   env=env,capture_output=True,text=True,timeout=100)
                if run.returncode:
                    self.post('homestretch_status','Local processing/upload error: '+run.stderr[-700:])
                else:
                    states=[]
                    for path in self.queue.glob('*.json'):
                        try:states.append(json.loads(path.read_text()))
                        except (OSError,ValueError):continue
                    pending=[j for j in states if j['state'] not in ('uploaded','local_only')]
                    if pending:
                        j=pending[-1];self.post('homestretch_status',f"{len(pending)} pending — {j.get('error') or j['state']}. Retrying every 30 seconds; local files retained.")
                    elif states:
                        j=max(states,key=lambda j:j.get('finished_at',''))
                        self.post('homestretch_status',('Uploaded and verified. ' if j['state']=='uploaded' else 'Saved locally (demo or upload off). ')+j['output'])
            except Exception as exc:self.post('homestretch_status','Upload pending: '+str(exc))
            self.wakeup.wait(30);self.wakeup.clear()
