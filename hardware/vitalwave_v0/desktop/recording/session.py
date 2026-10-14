"""Incremental recordings, exclusive file creation and explicit completeness."""
import csv,json,os,re,time
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path

class Session:
    def __init__(self,folder,name,session,mask,device,demo=False):
        if not re.fullmatch(r'[\w .-]{1,80}',name) or name.strip(' .')=='':raise ValueError('Use a recording name with letters, numbers, spaces, dots, underscores or hyphens (1–80 characters).')
        folder=Path(folder).expanduser();folder.mkdir(parents=True,exist_ok=True)
        stem=f'{name.strip()}_{datetime.now().strftime("%Y%m%d-%H%M%S")}_{session:08x}'
        self.path=folder/(stem+'.csv');self.meta_path=folder/(stem+'.json')
        self.file=self.path.open('x',newline='');self.writer=csv.writer(self.file)
        self.writer.writerow(['host_time_utc','session_id','sequence','watch_ms','sensor','raw_x','raw_y','raw_z','valid','x','y','z'])
        self.session=session;self.mask=mask;self.last_seq=None;self.count=0;self.gaps=0;self.invalid=0;self.invalid_by_sensor={};self.bad=0;self.last_flush=time.monotonic();self.closed=False
        self.meta=dict(format_version=2,session_id=session,mask=mask,device=device,demo=demo,complete=False,reason='Recording interrupted or still active',started_utc=datetime.now(timezone.utc).isoformat(),received=0,units={'acceleration':'g','gyroscope':'degrees/s','temperature':'degrees C','humidity':'percent','ppg':'raw ADC counts'},raw_scales={'acceleration':.000061,'gyroscope':.00875,'temperature':.01,'humidity':.01})
        self._save()
    def _save(self):
        tmp=self.meta_path.with_suffix('.json.tmp');tmp.write_text(json.dumps(self.meta,indent=2)+'\n');os.replace(tmp,self.meta_path)
    def add(self,s):
        if self.closed:return
        if s.session!=self.session or not(self.mask & (4 if s.kind>=4 else (2 if s.kind==3 else (8 if s.kind==2 and s.version>=3 else 1)))):self.bad+=1;return
        step=s.sequence if self.last_seq is None else (s.sequence-self.last_seq-1)&65535
        if self.last_seq is not None and step>=32768:self.bad+=1;return
        self.gaps+=step;self.last_seq=s.sequence;self.count+=1;self.invalid+=not s.valid
        if not s.valid:self.invalid_by_sensor[str(s.kind)]=self.invalid_by_sensor.get(str(s.kind),0)+1
        self.writer.writerow([datetime.now(timezone.utc).isoformat(),s.session,s.sequence,s.watch_ms,{1:'acceleration',2:'gyroscope',3:'temperature_humidity',4:'ppg_infrared',5:'ppg_red',6:'ppg_green',7:'ppg_blue'}[s.kind],s.x,s.y,s.z,s.valid,*s.values()])
        if time.monotonic()-self.last_flush>=1:
            self.file.flush();self.last_flush=time.monotonic()
        return True
    def finish(self,reason,status=None):
        if self.closed:return
        complete=(reason=='Stopped' and status is not None and status.session==self.session and status.state==0 and status.reason==0 and status.generated==self.count and status.dropped==0 and self.count>0 and not(self.gaps or self.invalid or self.bad))
        self.meta.update(complete=complete,reason=reason if complete else reason+'; incomplete or invalid data',received=self.count,missing_by_sequence=self.gaps,invalid_samples=self.invalid,invalid_by_sensor=self.invalid_by_sensor,malformed_or_unexpected=self.bad,ended_utc=datetime.now(timezone.utc).isoformat(),final_status=asdict(status) if status else None)
        self.file.flush();os.fsync(self.file.fileno());self.file.close();self.closed=True;self._save()
