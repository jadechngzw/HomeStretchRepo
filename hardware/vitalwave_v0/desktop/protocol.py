"""Strict codec shared by real BLE, demo, tests and recording."""
import struct
from dataclasses import dataclass,asdict
SERVICE='7bfa0001-6e4d-4b9d-923b-5d234081a100'
CONTROL='7bfa0002-6e4d-4b9d-923b-5d234081a100'
STATUS='7bfa0003-6e4d-4b9d-923b-5d234081a100'
SAMPLES='7bfa0004-6e4d-4b9d-923b-5d234081a100'
TELEMETRY='7bfa0005-6e4d-4b9d-923b-5d234081a100'
COMMAND=struct.Struct('<BBHII');STATE=struct.Struct('<BBBBIHHII');DATA=struct.Struct('<BBIHIhhhh')
@dataclass(frozen=True)
class Status:
    version:int;state:int;reason:int;mask:int;session:int;request:int;charger:int;generated:int;dropped:int
@dataclass(frozen=True)
class Sample:
    version:int;kind:int;session:int;sequence:int;watch_ms:int;x:int;y:int;z:int;valid:int
    def values(self):
        if self.kind>=4:return (((self.y&7)<<16)|(self.x&65535),None,None) if self.valid else (None,None,None)
        scale={1:.000061,2:.00875,3:.01}[self.kind]
        return (self.x*scale,self.y*scale,self.z*scale) if self.valid else (None,None,None)
def decode_status(data):
    if len(data)!=20:raise ValueError('Status must be 20 bytes')
    s=Status(*STATE.unpack(data))
    if s.version!=3 or s.state not in (0,1,2) or s.reason>6 or s.mask&~15 or s.charger>2 or s.dropped>s.generated:raise ValueError('Invalid status')
    return s
def decode_sample(data):
    if len(data)!=20:raise ValueError('Sample must be 20 bytes')
    s=Sample(*DATA.unpack(data))
    if s.version!=3 or s.kind not in (1,2,3,4,5,6,7) or not s.session or s.valid not in (0,1):raise ValueError('Invalid sample')
    if s.kind>=4 and (not 0<=s.y<=7 or s.z):raise ValueError("Invalid optical value")
    return s
def command(op,request,session,mask=0):
    if op not in (1,2,3,4) or not 0<session<=0xffffffff or not 1<=request<=65535:raise ValueError('Invalid command')
    if op==1 and mask not in range(1,16):raise ValueError('Choose at least one sensor')
    return COMMAND.pack(3,op,request,mask,session)

@dataclass(frozen=True)
class Settings:
    imu_hz:int=25
    temp_ms:int=1000
    ppg_hz:int=50
    leds:int=0
    def packed(self):
        if self.imu_hz not in (10,25,50) or self.temp_ms not in (500,1000,2000) or self.ppg_hz not in (50,100) or not 0<=self.leds<=15:raise ValueError('Unsupported sampling settings')
        if self.leds&(self.leds-1) and self.ppg_hz!=50:raise ValueError('Multiple PPG colours require 50 Hz')
        return self.imu_hz|(self.temp_ms//100)<<8|self.ppg_hz<<16|self.leds<<24

@dataclass(frozen=True)
class Telemetry:
    valid:bool
    register:int
    policy:int
    button1:int
    button2:int
    watch_ms:int
    @property
    def text(self):
        if self.policy==2:return 'Charger fault · Battery % unavailable'
        if not self.valid:return 'Charging status unavailable · Battery % unavailable'
        if not self.register&4:return 'External power absent · Battery % unavailable'
        phase=(self.register>>3)&3
        label={0:'Plugged in · Not charging',1:'Charging · Pre-charge',2:'Charging',3:'Charge complete'}[phase]
        return label+' · 240 mA policy · Battery % unavailable'

def decode_telemetry(data):
    if len(data)!=20 or data[0]!=3 or data[1]>1 or data[3]>2:raise ValueError('Incompatible telemetry')
    return Telemetry(bool(data[1]),data[2],data[3],*struct.unpack_from('<HHI',data,4))
