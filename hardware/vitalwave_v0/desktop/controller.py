"""Own BLE and recording outside Tk's main thread; only queues cross the boundary."""
import asyncio,queue,secrets,threading
from datetime import datetime,timezone
from pathlib import Path
from collections import deque
import logging
from desktop.processing.ppg import estimate,analyse_file
from desktop.recording.export import export_recording
from desktop.protocol import decode_sample,Settings
from dataclasses import asdict
from desktop.recording.session import Session
from desktop.bluetooth.client import Watch
from desktop.bluetooth.demo import DemoWatch

class Controller:
    def __init__(self,demo=False):
        self.demo=demo;self.events=queue.Queue();self.plot_samples=queue.Queue(maxsize=2000)
        self.loop=asyncio.new_event_loop();self.thread=threading.Thread(target=self._run,daemon=True);self.ready=threading.Event()
        self.session=None;self.heartbeat=None;self.connected=False;self.stop_expected=False;self.closing=False;self.device_name='';self.status=None;self.finished_path=None;self.finishing=False;self.starting=False;self.analysis_task=None;self.emergency_task=None
        self.live_history={k:deque(maxlen=1600) for k in range(4,8)};self.live_task=None
        self.thread.start();self.ready.wait()
        self.pipeline=None
        if (Path(__file__).resolve().parents[1]/'homestretch_integration.json').exists():
            from desktop.homestretch import HomeStretchBridge
            self.pipeline=HomeStretchBridge(Path(__file__).resolve().parents[1],self.post,demo=demo)
    def _run(self):
        asyncio.set_event_loop(self.loop);self.watch=(DemoWatch if self.demo else Watch)(self._sample,self._status,self._disconnected,self._telemetry)
        self.loop.set_exception_handler(lambda loop,ctx:logging.error('Background task failed: %s',ctx.get('message'),exc_info=ctx.get('exception')))
        self.ready.set();self.loop.run_forever()
    def post(self,event,payload=None):self.events.put((event,payload))
    def submit(self,method,*args):
        async def guarded():
            try:return await getattr(self,method)(*args)
            except Exception as e:
                logging.exception('Operation failed: %s',method);self.post('error',str(e) or type(e).__name__);self.post('busy',False)
        return asyncio.run_coroutine_threadsafe(guarded(),self.loop)
    async def scan(self):
        self.post('busy',True)
        try:self.post('devices',await self.watch.scan())
        finally:self.post('busy',False)
    async def connect(self,device,name):
        self.post('busy',True)
        try:
            await self.watch.connect(device);self.device_name=name;self.connected=True;self.post('connection',True)
        finally:self.post('busy',False)
    def _telemetry(self,t):self.post('telemetry',t)
    async def marker(self,watch_ms=None,button=0):
        if self.session:
            self.session.meta.setdefault('markers',[]).append({'watch_ms':watch_ms,'button':button,'host_time':datetime.now(timezone.utc).isoformat()})
            self.session._save();self.post('marker',len(self.session.meta['markers']))
    def _status(self,s):
        self.status=s;self.post('status',s)
        if self.session and s.session==self.session.session and s.state!=1 and not self.stop_expected:
            if not self.finishing:
                self.finishing=True;asyncio.create_task(self._watch_stopped(s))
    async def _drain(self,status,timeout=3):
        until=self.loop.time()+timeout
        while self.session and self.session.count<status.generated-status.dropped and self.loop.time()<until and self.connected:
            await asyncio.sleep(.02)
    async def _watch_stopped(self,s):
        try:
            await self._drain(s);self._finish(f'Watch stopped (reason {s.reason})',s)
        finally:self.finishing=False
    async def export(self,destination):
        if not self.finished_path:raise ValueError('Stop a recording first')
        path=await asyncio.to_thread(export_recording,self.finished_path,destination)
        self.finished_path=path;self.post('exported',path)
    async def process(self,path=None):
        path=path or self.finished_path
        if not path:raise ValueError('Stop a recording or choose a CSV first')
        if self.analysis_task:raise RuntimeError('Analysis is already running')
        self.analysis_task=True;self.post('processing',True)
        try:self.post('processed',await asyncio.to_thread(analyse_file,path))
        finally:self.analysis_task=None;self.post('processing',False)
    async def _live(self):
        while self.session:
            await asyncio.sleep(2)
            snapshots={k:list(v) for k,v in self.live_history.items() if v}
            def calculate():
                result={}
                for k,rows in snapshots.items():
                    end=rows[-1][0];recent=[v for v in rows if v[0]>=end-8000]
                    if rows[-1][0]-rows[0][0]<13000:result[k]={'bpm':None,'quality':'Warming up (13 s)'};continue
                    result[k]=estimate([v[0]/1000 for v in recent],[v[1] for v in recent])
                return result
            result=await asyncio.to_thread(calculate)
            if self.session:self.post('live',result)
    def _sample(self,data):
        if not self.session:return
        try:
            s=decode_sample(data)
            if s.session!=self.session.session:self.session.bad+=1;return
            if not self.session.add(s):return
            if s.kind>=4:
                value=s.values()[0];hist=self.live_history[s.kind]
                ms=s.watch_ms if not hist else hist[-1][0]+((s.watch_ms-int(hist[-1][0]))&0xffffffff)
                hist.append((ms,float('nan') if value is None else value))
            try:self.plot_samples.put_nowait(s)
            except queue.Full:pass # Display only; CSV already has the sample.
        except ValueError:self.session.bad+=1
        except Exception as e:
            self.post('error','Recording write failed: '+str(e))
            if self.emergency_task is None or self.emergency_task.done():self.emergency_task=asyncio.create_task(self.emergency_stop('Storage failure'))
    def _finish(self,reason,status=None):
        if self.live_task:self.live_task.cancel();self.live_task=None
        if self.heartbeat and self.heartbeat is not asyncio.current_task():self.heartbeat.cancel()
        self.heartbeat=None
        if self.session:
            recording=self.session;self.session=None
            try:
                recording.finish(reason,status);self.finished_path=str(recording.path)
                logging.info('Recording ended: %s %s',reason,recording.meta)
                self.post('stopped',(str(recording.path),recording.meta))
                if self.pipeline:
                    try:self.pipeline.enqueue(recording.path,recording.meta.get('homestretch'))
                    except Exception as exc:self.post('homestretch_status','Queue failed; raw recording retained: '+str(exc))
            finally:self.post('recording',False)
    def _disconnected(self):
        self.connected=False
        try:self._finish('Bluetooth disconnected')
        except Exception as e:self.post('error',str(e))
        self.post('connection',False)
    async def start(self,folder,name,mask,settings=None,homestretch=None):
        if not self.connected or self.session or self.starting or self.finishing:raise RuntimeError('Connect to an idle watch first')
        if mask not in range(1,16):raise ValueError('Select at least one sensor')
        homestretch=self.pipeline.validate(homestretch) if self.pipeline else None
        settings=settings or Settings()
        packed=settings.packed()
        if mask&4 and not settings.leds:raise ValueError('Select a PPG colour')
        sid=secrets.randbelow(0xffffffff)+1
        self.starting=True;self.post('busy',True)
        try:configured=await self.watch.request(4,sid,packed)
        finally:self.starting=False

        if configured.reason or configured.state!=0:raise RuntimeError('Watch rejected sampling settings')
        self.session=Session(Path(folder)/'.recovery',name,sid,mask,self.device_name,self.demo)
        for hist in self.live_history.values():hist.clear()
        self.session.meta['settings']=asdict(settings);self.session.meta['protocol_version']=3
        if homestretch:self.session.meta['homestretch']=homestretch
        self.session._save()
        self.post('busy',True)
        try:
            s=await self.watch.request(1,sid,mask)
            if s.reason or s.state!=1 or s.session!=sid:raise RuntimeError(f'Watch rejected Start (reason {s.reason}, state {s.state})')
            self.post('recording',True);self.heartbeat=asyncio.create_task(self._keepalive(sid));self.live_task=asyncio.create_task(self._live())
        except BaseException:
            # Best effort STOP; MCU watchdog still ends unacknowledged sessions.
            try:await self.watch.request(2,sid)
            except Exception:pass
            self._finish('Start failed');raise
        finally:self.post('busy',False)
    async def _keepalive(self,sid):
        try:
            while self.session:
                await asyncio.sleep(1);s=await self.watch.request(3,sid)
                if s.reason or s.state!=1 or s.session!=sid:raise RuntimeError('Watch no longer acknowledges this recording')
        except asyncio.CancelledError:pass
        except Exception as e:
            logging.exception('Keepalive failed');self.post('error',str(e) or type(e).__name__);await self.emergency_stop('Keepalive failed: '+(str(e) or type(e).__name__))
    async def stop(self):
        if not self.session:return
        self.post('busy',True);self.stop_expected=True
        if self.heartbeat:self.heartbeat.cancel();self.heartbeat=None
        try:
            sid=self.session.session;s=await self.watch.request(2,sid)
            if s.state!=0 or s.reason or s.session!=sid:raise RuntimeError('Watch did not confirm normal Stop')
            await self._drain(s)
            self._finish('Stopped',s)
        except Exception:
            self._finish('Stop not confirmed');raise
        finally:self.stop_expected=False;self.post('busy',False)
    async def emergency_stop(self,reason):
        if self.heartbeat and self.heartbeat is not asyncio.current_task():self.heartbeat.cancel()
        self.heartbeat=None;self.stop_expected=True
        try:
            if self.session:
                s=await self.watch.request(2,self.session.session);await self._drain(s)
        except Exception:pass
        finally:self._finish(reason);self.stop_expected=False
    async def disconnect(self):
        if self.session:
            try:await self.stop()
            except Exception as e:self.post('error',str(e))
        await self.watch.disconnect();self.connected=False;self.post('connection',False)
    async def shutdown(self):
        self.closing=True
        try:await asyncio.wait_for(self.disconnect(),5)
        except Exception:
            self._finish('App closed without confirmed Stop')
        finally:
            if self.pipeline:self.pipeline.close()
            self.post('closed')
