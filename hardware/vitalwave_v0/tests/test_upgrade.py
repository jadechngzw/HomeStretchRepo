import asyncio,csv,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from desktop.protocol import DATA,STATE,Status,Settings,decode_sample
from desktop.bluetooth.client import Watch
from desktop.bluetooth.demo import DemoWatch
from desktop.controller import Controller
from desktop.recording.session import Session
from desktop.recording.export import export_recording
from desktop.processing.ppg import estimate,filtered,analyse_file


def test_batched_notifications():
    got=[];w=Watch(got.append,lambda _:None,lambda:None)
    frames=[DATA.pack(3,4,42,i,20*i,1000,0,0,1) for i in range(12)]
    w._samples(None,b''.join(frames));assert got==frames
    w._samples(None,b'broken');assert got[-1]==b'broken'


def test_read_fallback_when_notification_queue_busy():
    async def run():
        seen=[];w=Watch(lambda _:None,seen.append,lambda:None)
        class Client:
            is_connected=True
            async def write_gatt_char(self,*a,**kw):pass
            async def read_gatt_char(self,*a):return STATE.pack(3,1,0,15,42,w.request_id,0,999,0)
        w.client=Client();s=await w.request(3,42)
        assert s.generated==999 and seen[-1]==s
    asyncio.run(run())


def test_independent_capture_masks():
    async def run():
        for mask,kinds in [(8,{2}),(1,{1}),(2,{3}),(4,{4,5}),(15,set(range(1,8)))]:
            got=[];w=DemoWatch(got.append,lambda _:None,lambda:None)
            await w.connect('demo');await w.request(4,42,Settings(50,500,50,3 if mask==4 else 15).packed())
            await w.request(1,42,mask);await asyncio.sleep(.1);await w.request(2,42);await w.disconnect()
            assert {decode_sample(f).kind for f in got}==kinds
    asyncio.run(run())


def test_stop_ack_before_final_samples_and_separate_export(tmp_path):
    c=Controller(demo=True)
    async def run():
        await c.connect('demo','demo');await c.start(tmp_path,'tail',4,Settings(25,1000,50,4))
        if c.heartbeat:c.heartbeat.cancel()
        c.watch.task.cancel()
        # Replace transport after starting: STOP ack overtakes a queued final batch.
        count=c.session.count;sid=c.session.session
        async def request(op,*args):
            assert op==2
            for i in range(3):
                c.loop.call_later(.04*(i+1),c._sample,DATA.pack(3,6,sid,count+i,100+i*20,1000,0,0,1))
            return Status(3,0,0,4,sid,1,0,count+3,0)
        c.watch.request=request
        await c.stop();path=Path(c.finished_path)
        assert json.loads(path.with_suffix('.json').read_text())['complete']
        assert not list(tmp_path.glob('*.csv')) and path.parent.name=='.recovery'
        await c.export(tmp_path/'export.csv');assert path.exists()
        with pytest.raises(FileExistsError):export_recording(path,tmp_path/'export.csv')
        assert (tmp_path/'export.csv').read_bytes()==path.read_bytes()
        await c.disconnect()
    try:asyncio.run_coroutine_threadsafe(run(),c.loop).result(10)
    finally:c.loop.call_soon_threadsafe(c.loop.stop);c.thread.join(2)


def test_estimator_drift_and_rejections():
    t=np.arange(0,8.02,.02);x=10000+50*t+150*np.sin(2*np.pi*1.25*t)
    assert estimate(t,x)['bpm']==pytest.approx(75,abs=2)
    assert np.std(filtered(t,x))<np.std(x)
    assert estimate(t,np.full(len(t),10000))['bpm'] is None
    bad=x.copy();bad[100]=np.nan;assert estimate(t,bad)['bpm'] is None
    assert estimate(np.delete(t,100),np.delete(x,100))['bpm'] is None
    bad=x.copy();bad[200:]+=5000;assert estimate(t,bad)['bpm'] is None
    rng=np.random.default_rng(5);assert estimate(t,10000+rng.normal(0,200,len(t)))['bpm'] is None


def test_report_red_ir_ratio_never_fabricates_spo2(tmp_path):
    path=tmp_path/'paired.csv'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['sensor','watch_ms','valid','x']);w.writeheader()
        for ms in range(0,18000,20):
            wave=np.sin(2*np.pi*1.25*ms/1000)
            for name,dc,ac in [('ppg_red',10000,100),('ppg_infrared',20000,400)]:
                w.writerow(dict(sensor=name,watch_ms=ms,valid=1,x=dc+ac*wave))
    report,result=analyse_file(path)
    assert Path(report).exists() and result['channels']['ppg_red']['average_bpm']==pytest.approx(75,abs=2)
    assert result['spo2']['percent'] is None
    assert np.median([r['R'] for r in result['spo2']['paired_windows']])==pytest.approx(.5,abs=.01)
