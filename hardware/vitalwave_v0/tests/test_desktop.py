import asyncio,csv,struct
from pathlib import Path
import pytest
from desktop.protocol import DATA,STATE,decode_sample,decode_status,command,Status
from desktop.recording.session import Session
from desktop.bluetooth.demo import DemoWatch

def sample(n=0,session=42,valid=1):return decode_sample(DATA.pack(3,1,session,n,1234,100,-200,16000,valid))
def status(count,drop=0):return Status(3,0,0,1,42,3,0,count,drop)
def test_codec():
    s=sample();assert s.x==100 and s.y==-200 and s.values()[1]==pytest.approx(-.0122)
    assert command(1,1,42,3)==bytes.fromhex('03010100030000002a000000')
    for b in (b'',DATA.pack(1,1,42,0,0,0,0,0,1),DATA.pack(3,8,42,0,0,0,0,0,1)):
        with pytest.raises(ValueError):decode_sample(b)
    with pytest.raises(ValueError):command(1,1,42,0)
    with pytest.raises(ValueError):decode_status(bytes(20))
def test_save_complete(tmp_path):
    r=Session(tmp_path,'trial',42,1,'test');r.add(sample());r.add(sample(1));r.finish('Stopped',status(2))
    assert r.meta['complete'];assert len(list(csv.reader(r.path.open())))==3
    with pytest.raises(FileExistsError):Session(tmp_path,'trial',42,1,'test')
def test_gaps_and_missing_tail(tmp_path):
    r=Session(tmp_path,'gap',42,1,'test');r.add(sample(1));r.add(sample(3));r.finish('Stopped',status(4,2))
    assert not r.meta['complete'] and r.gaps==2
    r=Session(tmp_path,'tail',42,1,'test');r.add(sample());r.finish('Stopped',status(2));assert not r.meta['complete']
def test_disconnect_invalid_and_wrong_session(tmp_path):
    r=Session(tmp_path,'lost',42,1,'test');r.add(sample(valid=0));r.add(sample(session=43));r.finish('Bluetooth disconnected')
    assert not r.meta['complete'] and r.invalid==1 and r.bad==1
    with pytest.raises(ValueError):Session(tmp_path,'../escape',42,1,'test')
def test_sequence_wrap(tmp_path):
    r=Session(tmp_path,'wrap',42,1,'test');r.last_seq=65535;r.add(sample(0));assert r.gaps==0;r.finish('test')
def test_demo_end_to_end():
    async def run():
        frames=[];states=[];w=DemoWatch(frames.append,states.append,lambda:None)
        await w.connect('demo');await w.request(1,42,3);await asyncio.sleep(.2);s=await w.request(2,42)
        count=len(frames);await asyncio.sleep(.08);assert len(frames)==count and count>2 and s.generated==count
        assert all(decode_sample(p).session==42 for p in frames)
        await w.disconnect()
    asyncio.run(run())

def test_connected_transport_acknowledgement():
    from desktop.bluetooth.client import Watch
    from desktop.protocol import COMMAND,STATUS,SAMPLES
    async def run():
        statuses=[];watch=Watch(lambda data:None,statuses.append,lambda:None)
        class FakeClient:
            is_connected=True
            async def write_gatt_char(self,uuid,data,response):
                version,op,request,mask,sid=COMMAND.unpack(data)
                assert response
                watch._status(None,STATE.pack(3,1 if op==1 else 0,0,mask,sid,request,0,0,0))
        watch.client=FakeClient()
        s=await watch.request(1,42,3);assert s.session==42 and s.state==1 and s.request==1
        s=await watch.request(2,42);assert s.state==0 and s.request==2
        assert len(statuses)==2
    asyncio.run(run())


def test_ppg_lossless_counts_and_settings(tmp_path):
    from desktop.protocol import Settings
    for v in (0,32767,32768,65535,65536,524287):
        lo=v&65535
        s=decode_sample(DATA.pack(3,6,42,0,20,lo if lo<32768 else lo-65536,v>>16,0,1))
        assert s.values()[0]==v
    with pytest.raises(ValueError):Settings(ppg_hz=100,leds=15).packed()
    assert Settings(50,500,50,15).packed()==0x0f320532
    r=Session(tmp_path,'optical',42,4,'test')
    r.add(decode_sample(DATA.pack(3,6,42,0,20,-1,7,0,1)))
    r.finish('Stopped',Status(3,0,0,4,42,1,0,1,0))
    assert r.meta['complete'] and '524287' in r.path.read_text()

def test_power_telemetry():
    from desktop.protocol import decode_telemetry
    def t(reg,valid=1,policy=1):return decode_telemetry(bytes([3,valid,reg,policy])+struct.pack('<HHI',3,8,1234)+bytes(8))
    assert 'Charging ·' in t(0x74).text
    assert 'Charge complete' in t(0x7c).text
    assert 'Not charging' in t(0x64).text
    assert 'absent' in t(0).text
    assert 'unavailable' in t(0x74,0).text
    assert 'fault' in t(0x74,1,2).text
    assert t(0).button2==8

def test_all_colours_demo_recording(tmp_path):
    from desktop.protocol import Settings
    async def run():
        r=Session(tmp_path,'all_colours',42,15,'demo',True)
        w=DemoWatch(lambda b:r.add(decode_sample(b)),lambda s:None,lambda:None)
        await w.connect('demo');await w.request(4,42,Settings(50,500,50,15).packed())
        await w.request(1,42,15);await asyncio.sleep(.65);s=await w.request(2,42)
        r.finish('Stopped',s);await w.disconnect()
        assert r.meta['complete']
        rows=list(csv.DictReader(r.path.open()));assert len(set(x['sensor'] for x in rows))==7
    asyncio.run(run())
