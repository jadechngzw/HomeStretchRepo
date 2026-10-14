import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CurlCounter, CurlSession, protocol as p } from './load-core.mjs';

function movement(counter, { sign = 1, count = 12, amplitude = 1.2 } = {}) {
  const events = [];
  for (let ms = 0; ms <= 2500 + count * 3000 + 1500; ms += 20) {
    const t = ms - 2500;
    const y = t > 0 && t < count * 3000 ? sign * amplitude * (1 - Math.cos(2 * Math.PI * (t % 3000) / 3000)) / 2 : 0;
    const event = counter.add(ms, y);
    if (event) events.push(event);
  }
  return events;
}
for (const sign of [-1, 1]) test(`counts full curls in either polarity, including the first and beyond ten (${sign})`, () => {
  const c = new CurlCounter(), events = movement(c, { sign });
  assert.equal(events.length, 12);
  assert.deepEqual(events.map(e => e.count), Array.from({length:12}, (_, i) => i + 1));
});
test('stillness, noise, and partial curls do not count', () => {
  const c = new CurlCounter();
  for (let ms = 0; ms < 10000; ms += 20) c.add(ms, 0.03 * Math.sin(ms));
  assert.equal(c.count, 0);
  assert.equal(movement(new CurlCounter(), { amplitude: 0.3 }).length, 0);
});
test('a missing interval resets an unfinished curl and requires a new baseline', () => {
  const c = new CurlCounter();
  for (let ms = 0; ms < 2500; ms += 20) c.add(ms, 0);
  for (let ms = 2500; ms < 3500; ms += 20) c.add(ms, (ms - 2500) / 1000);
  c.add(4000, 0);
  assert.equal(c.count, 0); assert.equal(c.ready, false);
});
test('base64 and v3 command bytes agree with known wire layout', () => {
  const bytes = Buffer.from(p.command(1, 0x1234, 1, 0x12345678), 'base64');
  assert.deepEqual([...bytes], [3,1,0x34,0x12,1,0,0,0,0x78,0x56,0x34,0x12]);
  for (let length = 1; length <= 240; length++) {
    const input = Uint8Array.from({length}, (_, i) => i & 255);
    assert.equal(p.encode(input), Buffer.from(input).toString('base64'));
    assert.deepEqual(p.decode(p.encode(input)), input);
  }
  assert.throws(() => p.samples(p.encode(new Uint8Array(19))));
  assert.throws(() => p.status(p.encode(new Uint8Array(20))));
});
function sample(id, sequence, ms, y = 0, valid = 1) {
  const b = Buffer.alloc(20); b[0] = 3; b[1] = 1;
  b.writeUInt32LE(id, 2); b.writeUInt16LE(sequence & 65535, 6); b.writeUInt32LE(ms >>> 0, 8);
  b.writeInt16LE(Math.round(y / 0.000061), 14); b.writeInt16LE(valid, 18); return b;
}
function fixture({ failStart = false, notifyAck = true, delayTail = false, silent = false } = {}) {
  const listeners = new Map(), commands = [];
  let state = 0, sessionId = 0, request = 0, mask = 0, generated = 0, dropped = 0;
  let sequence = 0;
  const encodeStatus = () => {
    const b = Buffer.alloc(20); b[0]=3; b[1]=state; b[3]=mask;
    b.writeUInt32LE(sessionId,4); b.writeUInt16LE(request,8); b.writeUInt32LE(generated,12); b.writeUInt32LE(dropped,16);
    return b.toString('base64');
  };
  const device = {
    monitorCharacteristicForService(_s, char, listener) {
      listeners.set(char, listener);
      return { remove() { listeners.delete(char); } };
    },
    async readCharacteristicForService() { return { value: encodeStatus() }; },
    async writeCharacteristicWithResponseForService(_s, _c, value) {
      const b = Buffer.from(value,'base64'); const op=b[1]; commands.push(op);
      if (silent) return;
      if (!(failStart && op === 1)) request=b.readUInt16LE(2);
      if (op === 1 && !failStart) { sessionId=b.readUInt32LE(8); state=1; mask=b.readUInt32LE(4); generated=0; sequence=0; }
      if (op === 2) {
        state=0;
        if (delayTail) {
          const tail = sample(sessionId, sequence++, 0); generated++;
          setTimeout(() => listeners.get(p.UUID.samples)?.(null,{value:tail.toString('base64')}),10);
        }
      }
      if (notifyAck) listeners.get(p.UUID.status)?.(null,{value:encodeStatus()});
    },
  };
  const session = new CurlSession(() => device, { ack: 5, io: 30, drain: 50, heartbeat: 20, stall: 5000 });
  function frames(data) {
    generated += data.length;
    const b = Buffer.concat(data.map(([ms,y=0,valid=1,id=sessionId]) => sample(id,sequence++,ms,y,valid)));
    listeners.get(p.UUID.samples)?.(null,{value:b.toString('base64')});
  }
  return { session, commands, listeners, frames,
    skip: () => { sequence++; generated++; dropped++; },
    resetSequence: n => { sequence=n; },
    getSessionId: () => sessionId };
}
test('start subscribes, configures, confirms START and counts a full live set; normal end sends STOP', async () => {
  const f = fixture(); await f.session.start('left');
  assert.equal(f.session.getSnapshot().phase,'calibrating');
  assert.deepEqual(f.commands,[4,1]);
  for (let ms=0;ms<=40000;ms+=20) {
    const t=ms-2500;
    const y=t>0&&t<36000?0.6*(1-Math.cos(2*Math.PI*(t%3000)/3000)):0;
    f.frames([[ms,y]]);
  }
  assert.equal(f.session.getSnapshot().reps,12);
  await f.session.stop();
  assert.equal(f.commands.at(-1),2);
  assert.equal(f.session.getSnapshot().phase,'ended');
  assert.equal(f.session.getSnapshot().complete,true);
  assert.equal(f.listeners.size,0);
  await f.session.start('right');
  assert.equal(f.session.getSnapshot().reps,0);
  assert.equal(f.session.getSnapshot().arm,'right');
  f.session.interrupt();
});
test('write success without the matching START acknowledgement never starts a set', async () => {
  const f=fixture({failStart:true}); await f.session.start('right');
  assert.equal(f.session.getSnapshot().phase,'interrupted'); assert.equal(f.listeners.size,0);
});
test('status readback recovers a missing notification acknowledgement', async () => {
  const f=fixture({notifyAck:false}); await f.session.start('right');
  assert.equal(f.session.getSnapshot().phase,'calibrating'); f.session.interrupt();
});
test('STOP drains packets that arrive after its acknowledgement', async () => {
  const f=fixture({delayTail:true}); await f.session.start('right'); await f.session.stop();
  assert.equal(f.session.getSnapshot().received,1); assert.equal(f.session.getSnapshot().complete,true);
});
test('gaps and invalid samples mark a set incomplete', async () => {
  const f=fixture(); await f.session.start('right'); f.frames([[0],[20]]); f.skip(); f.frames([[60,0,0]]);
  await f.session.stop(); const s=f.session.getSnapshot();
  assert.equal(s.missing,1); assert.equal(s.invalid,1); assert.equal(s.complete,false);
});
test('wrong-session packets are not counted', async () => {
  const f=fixture(); await f.session.start('right'); f.frames([[0,0,1,(f.getSessionId()+1)>>>0]]);
  assert.equal(f.session.getSnapshot().received,0); assert.equal(f.session.getSnapshot().unexpected,1); f.session.interrupt();
});
test('heartbeat runs only during the set and interruption never resumes counting', async () => {
  const f=fixture(); await f.session.start('right');
  await new Promise(r=>setTimeout(r,55)); assert.ok(f.commands.includes(3));
  f.session.interrupt('Set interrupted.'); const n=f.commands.length;
  await new Promise(r=>setTimeout(r,40)); assert.equal(f.commands.length,n);
  assert.equal(f.session.getSnapshot().complete,false); assert.equal(f.listeners.size,0);
});
test('twelve frames in a notification and timestamp wrap are decoded', async () => {
  const f=fixture(); await f.session.start('right');
  f.frames(Array.from({length:12},(_,i)=>[((0xfffffff0+i*20)>>>0)]));
  assert.equal(f.session.getSnapshot().received,12);
  assert.equal(f.session.getSnapshot().invalid,0); f.session.interrupt();
});

test('occasional invalid samples do not prevent still-position calibration', () => {
  const counter = new CurlCounter();
  for (let ms=0;ms<5000;ms+=20) {
    if (ms%500===0) counter.discardPartial();
    else counter.add(ms,0);
  }
  assert.equal(counter.ready,true); assert.equal(counter.count,0);
});
test('brief loss during a curl discards it until the arm returns', () => {
  const counter = new CurlCounter();
  for (let ms=0;ms<2500;ms+=20) counter.add(ms,0);
  for (let ms=2500;ms<4000;ms+=20) counter.add(ms,0.6*(1-Math.cos(2*Math.PI*(ms-2500)/3000)));
  counter.discardPartial();
  for (let ms=4000;ms<6500;ms+=20) counter.add(ms,ms<5500?0.6*(1-Math.cos(2*Math.PI*(ms-2500)/3000)):0);
  assert.equal(counter.count,0);
});

for (const period of [1000, 1200, 1500, 2000]) test(`continuous ${period} ms curls do not need a pause`, () => {
  for (const sign of [-1, 1]) {
    const counter = new CurlCounter();
    for (let ms=0; ms<2500+12*period+1200; ms+=20) {
      const t=ms-2500;
      counter.add(ms,t>0&&t<12*period?sign*0.4*(1-Math.cos(2*Math.PI*t/period)):0);
    }
    assert.equal(counter.count,12);
  }
});
test('isolated invalid samples preserve complete curls but remain flagged in the summary', async () => {
  const f=fixture(); await f.session.start('right');
  for (let ms=0;ms<40000;ms+=20) {
    const t=ms-2500, y=t>0&&t<36000?0.6*(1-Math.cos(2*Math.PI*t/3000)):0;
    f.frames([[ms,y,ms>2500&&ms%500===0?0:1]]);
  }
  assert.equal(f.session.getSnapshot().reps,12);
  await f.session.stop();
  assert.equal(f.session.getSnapshot().complete,false);
  assert.ok(f.session.getSnapshot().invalid>0);
});
test('reps with more than ten percent missing samples are not counted', () => {
  const counter=new CurlCounter();
  for(let ms=0;ms<13000;ms+=20) {
    if(ms>2500&&ms%80===0){counter.noteMissing();continue;}
    const t=ms-2500;
    counter.add(ms,t>0&&t<9000?0.6*(1-Math.cos(2*Math.PI*t/3000)):0);
  }
  assert.equal(counter.count,0);
});
