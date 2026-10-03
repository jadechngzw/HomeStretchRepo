#!/usr/bin/env python3
"""Build firmware with mandatory charger module; merge official S140 image."""
from pathlib import Path
import subprocess,hashlib,json
ROOT=Path(__file__).resolve().parent
SDK=ROOT/'vendor/nRF5_SDK_17.1.0_ddde560'
MDK=SDK/'modules/nrfx/mdk'
SD=SDK/'components/softdevice/s140'
OUT=ROOT/'build';OUT.mkdir(exist_ok=True)
if not (SD/'hex/s140_nrf52_7.2.0_softdevice.hex').exists():raise SystemExit('Run tools/setup_sdk.py first.')
linker=OUT/'app.ld';linker.write_text('''SEARCH_DIR(.)
GROUP(-lgcc -lc -lnosys)
MEMORY {
 FLASH (rx) : ORIGIN = 0x27000, LENGTH = 0xD9000
 RAM (rwx) : ORIGIN = 0x20008000, LENGTH = 0x38000
}
INCLUDE "nrf_common.ld"
''')
cpu=['-mcpu=cortex-m4','-mthumb','-mfloat-abi=hard','-mfpu=fpv4-sp-d16']
incs=[MDK,SDK/'components/toolchain/cmsis/include',SD/'headers',SD/'headers/nrf52',ROOT/'src']
sources=[ROOT/'src'/s for s in ['main.c','board.c','sensors.c','session.c','config.c','ppg.c','power/charger_policy.c']]+[MDK/'system_nrf52840.c',MDK/'gcc_startup_nrf52840.S']
objects=[]
for s in sources:
 o=OUT/(s.stem+'.o');objects.append(str(o))
 subprocess.run(['arm-none-eabi-gcc',*cpu,'-DNRF52840_XXAA','-DS140','-DSOFTDEVICE_PRESENT','-DFLOAT_ABI_HARD','-std=c99','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Os','-g3','-ffunction-sections','-fdata-sections',*[x for p in incs for x in ['-I' if p==ROOT/'src' else '-isystem',str(p)]],'-c',str(s),'-o',str(o)],check=True)
elf=OUT/'vitalwave_v0.elf';app=OUT/'application.hex'
subprocess.run(['arm-none-eabi-gcc',*cpu,'-T'+str(linker),'-L'+str(MDK),'-Wl,--gc-sections','-Wl,-Map='+str(OUT/'vitalwave_v0.map'),'-specs=nano.specs','-specs=nosys.specs',*objects,'-o',str(elf)],check=True)
subprocess.run(['arm-none-eabi-objcopy','-O','ihex',str(elf),str(app)],check=True)
def readhex(path):
 mem={};base=0
 for line in path.read_text().splitlines():
  b=bytes.fromhex(line[1:]);assert len(b)==b[0]+5 and sum(b)%256==0
  n=b[0];a=int.from_bytes(b[1:3],'big');kind=b[3];d=b[4:4+n]
  if kind==4:base=int.from_bytes(d,'big')<<16
  elif kind==2:base=int.from_bytes(d,'big')<<4
  elif kind==0:
   for i,v in enumerate(d):
    addr=base+a+i
    if addr in mem and mem[addr]!=v:raise ValueError('Conflicting HEX bytes')
    mem[addr]=v
 return mem
memory=readhex(SD/'hex/s140_nrf52_7.2.0_softdevice.hex');appmem=readhex(app)
assert min(appmem)==0x27000 and max(appmem)<0x100000
assert not(set(memory)&set(appmem));memory.update(appmem)
def record(addr,kind,data):
 b=bytes([len(data)])+addr.to_bytes(2,'big')+bytes([kind])+data
 return ':'+(b+bytes([-sum(b)&255])).hex().upper()
lines=[];addresses=sorted(memory);i=0;upper=-1
while i<len(addresses):
 addr=addresses[i]
 if addr>>16!=upper:upper=addr>>16;lines.append(record(0,4,upper.to_bytes(2,'big')))
 block=bytearray([memory[addr]]);i+=1
 while i<len(addresses) and addresses[i]==addr+len(block) and len(block)<16 and addresses[i]>>16==upper:
  block.append(memory[addresses[i]]);i+=1
 lines.append(record(addr&65535,0,block))
lines.append(record(0,1,b''));dest=OUT/'vitalwave_v0.hex';dest.write_text('\n'.join(lines)+'\n')
assert readhex(dest)==memory
manifest=dict(firmware='VitalWave-v0',protocol=3,sdk='17.1.0',softdevice='S140 7.2.0',charger_mA=240,charger_voltage_mV=4080,input_limit_mA=500,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),hardware_validation='pending')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
subprocess.run(['arm-none-eabi-size',str(elf)],check=True)
print('Merged and checksum-verified:',dest)
