"""Explicit simulation; never presented as watch data."""
import asyncio,math
from desktop.protocol import Status,DATA,Settings,Telemetry
class DemoWatch:
    def __init__(self,on_sample,on_status,on_disconnect,on_telemetry=None):
        self.on_sample=on_sample;self.on_status=on_status;self.on_disconnect=on_disconnect
        self.on_telemetry=on_telemetry or (lambda _:None);self.settings=Settings();self.power_task=None
        self.connected=False;self.task=None;self.session=0;self.mask=0;self.seq=0;self.generated=0;self.req=0
    async def scan(self):await asyncio.sleep(.1);return [('DEMO','DEMO — simulated watch',-45)]
    def status(self):return Status(3,int(self.task is not None),0,self.mask,self.session,self.req,0,self.generated,0)
    async def connect(self,device):
        self.connected=True;self.on_status(self.status());self.power_task=asyncio.create_task(self.telemetry());return self.status()
    async def telemetry(self):
        while self.connected:
            self.on_telemetry(Telemetry(True,0,0,0,0,0));await asyncio.sleep(.5)
    async def request(self,op,session,mask=0):
        self.req+=1
        if op==4:self.settings=Settings(mask&255,((mask>>8)&255)*100,(mask>>16)&255,mask>>24)
        if op==1:
            self.session=session;self.mask=mask;self.seq=self.generated=0;self.task=asyncio.create_task(self.stream())
        elif op==2:
            if self.task:self.task.cancel();self.task=None
        s=self.status();self.on_status(s);return s
    async def stream(self):
        tick=0
        while True:
            ms=tick*10;t=ms/1000;entries=[]
            if ms%(1000//self.settings.imu_hz)==0:
                if self.mask&1:entries.append((1,int(1600*math.sin(t)),int(1200*math.cos(t)),16393))
                if self.mask&8:entries.append((2,int(120*math.cos(t)),int(70*math.sin(t)),0))
            if self.mask&2 and ms%self.settings.temp_ms==0:entries.append((3,int(2450+10*math.sin(t/5)),4700,0))
            if self.mask&4 and ms%(1000//self.settings.ppg_hz)==0:
                for c in range(4):
                    if self.settings.leds&(1<<c):
                        v=int(80000+c*18000+(700+c*160)*math.sin(t*7.5+c*.1));lo=v&65535
                        entries.append((4+c,lo if lo<32768 else lo-65536,v>>16,0))
            for kind,x,y,z in entries:
                self.on_sample(DATA.pack(3,kind,self.session,self.seq&65535,ms,x,y,z,1));self.seq+=1;self.generated+=1
            tick+=1;await asyncio.sleep(.01)
    async def disconnect(self):
        if self.power_task:self.power_task.cancel();self.power_task=None
        if self.task:self.task.cancel();self.task=None
        if self.connected:self.connected=False;self.on_disconnect()
