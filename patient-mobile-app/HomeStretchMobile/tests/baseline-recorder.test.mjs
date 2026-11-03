import {test} from 'node:test';
import assert from 'node:assert/strict';
import {BaselineRecorder,protocol as p} from './load-core.mjs';
function fixture({fail=false,tail=false}={}){
 const listeners=new Map(),commands=[];
 let state=0,id=0,request=0,mask=0,generated=0,seq=0;
 const status=()=>{const b=Buffer.alloc(20);b[0]=3;b[1]=state;b[3]=mask;b.writeUInt32LE(id,4);b.writeUInt16LE(request,8);b.writeUInt32LE(generated,12);return b.toString('base64');};
 const send=(type,ms,valid=1,session=id)=>{const b=Buffer.alloc(20);b[0]=3;b[1]=type;b.writeUInt32LE(session,2);b.writeUInt16LE(seq++&65535,6);b.writeUInt32LE(ms>>>0,8);b.writeInt16LE(valid,18);generated++;listeners.get(p.UUID.samples)?.(null,{value:b.toString('base64')});};
 const device={monitorCharacteristicForService(_s,c,fn){listeners.set(c,fn);return{remove(){listeners.delete(c);}};},async readCharacteristicForService(){return{value:status()};},async writeCharacteristicWithResponseForService(_s,_c,value){const b=Buffer.from(value,'base64'),op=b[1],arg=b.readUInt32LE(4);commands.push({op,arg});if(fail&&op===1)return;request=b.readUInt16LE(2);if(op===1){state=1;id=b.readUInt32LE(8);mask=arg;seq=0;generated=0;}if(op===2){state=0;if(tail){generated+=2;setTimeout(()=>{generated-=2;send(1,80);send(2,80);},10);}}listeners.get(p.UUID.status)?.(null,{value:status()});}};
 const recorder=new BaselineRecorder(()=>device,{ack:5,io:30,drain:50,heartbeat:10,stall:40});
 return{recorder,send,commands,listeners,skip:()=>{seq++;generated++;}};
}
test('captures paired acceleration/gyro at 25 Hz, shared sequence, equal timestamps',async()=>{
 const f=fixture();await f.recorder.start('right');assert.deepEqual(f.commands.slice(0,2),[{op:4,arg:25|(10<<8)|(50<<16)},{op:1,arg:9}]);
 for(let ms=0;ms<800;ms+=40){f.send(1,ms);f.send(2,ms);}await f.recorder.stop();assert.equal(f.recorder.getSnapshot().complete,true);assert.equal(f.recorder.getFrames().length,40);assert.equal(f.listeners.size,0);
 await f.recorder.start('left');assert.equal(f.recorder.getFrames().length,0);f.recorder.interrupt();
});
test('STOP drains the final frames from both streams',async()=>{const f=fixture({tail:true});await f.recorder.start('right');f.send(1,0);f.send(2,0);f.send(1,40);f.send(2,40);await f.recorder.stop();assert.equal(f.recorder.getFrames().length,6);assert.equal(f.recorder.getSnapshot().complete,true);});
test('an absent gyro cannot pass completeness or keep the recorder alive',async()=>{const f=fixture();await f.recorder.start('right');const timer=setInterval(()=>f.send(1,Date.now()>>>0),10);await new Promise(r=>setTimeout(r,90));clearInterval(timer);assert.equal(f.recorder.getSnapshot().phase,'interrupted');assert.equal(f.recorder.getSnapshot().complete,false);assert.equal(f.listeners.size,0);});
test('invalid frames and sequence gaps remain incomplete',async()=>{const f=fixture();await f.recorder.start('right');f.send(1,0);f.send(2,0);f.skip();f.send(1,40,0);f.send(2,40);await f.recorder.stop();assert.equal(f.recorder.getSnapshot().complete,false);assert.equal(f.recorder.getSnapshot().missing,1);assert.equal(f.recorder.getSnapshot().invalid,1);});
test('START must be acknowledged and interrupted sessions never resume',async()=>{const f=fixture({fail:true});await f.recorder.start('right');assert.equal(f.recorder.getSnapshot().phase,'interrupted');assert.equal(f.listeners.size,0);});
