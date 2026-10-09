import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WatchConnection, SERVICE } from '../src/wearable/connection.ts';

function fixture({ radio = 'PoweredOn', discover = true, compatible = true, drops = false, multiple = false } = {}) {
  let scanCount = 0, stopCount = 0, connectCount = 0;
  let connectedId;
  let drop;
  const stateListeners = new Set();
  const device = {
    id: 'watch', name: 'VitalWave-v0',
    async discoverAllServicesAndCharacteristics() { return device; },
    async characteristicsForService(service) {
      assert.equal(service, SERVICE);
      return compatible ? [2, 3, 4, 5].map(n => ({
        uuid: `7bfa000${n}-6e4d-4b9d-923b-5d234081a100`,
        isReadable: n === 3 || n === 5, isNotifiable: n !== 2, isWritableWithResponse: n === 2,
      })) : [];
    },
    async isConnected() { return !drops; },
  };
  const manager = {
    onStateChange(listener, emit) {
      stateListeners.add(listener);
      if (emit) listener(radio);
      return { remove() { stateListeners.delete(listener); } };
    },
    async startDeviceScan(_uuids, _options, listener) {
      scanCount++;
      listener(null, { ...device, name: 'Unrelated headphones', id: 'other' });
      if (discover) { listener(null, device); listener(null, device); }
      if (multiple) listener(null, { ...device, id: 'second-watch' });
    },
    async stopDeviceScan() { stopCount++; },
    async connectToDevice(id) { connectedId = id; connectCount++; return { ...device, id }; },
    async cancelDeviceConnection() { drop?.(null); },
    onDeviceDisconnected(_id, listener) { drop = listener; return { remove() { drop = undefined; } }; },
  };
  const connection = new WatchConnection(() => manager, 25);
  return { connection, connectedId: () => connectedId, drop: () => drop?.(null), radio: (value) => stateListeners.forEach(fn => fn(value)),
    counts: () => ({ scanCount, stopCount, connectCount }) };
}

test('only a real verified connection turns green; duplicate taps do not start parallel scans', async () => {
  const f = fixture();
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  const states = [];
  f.connection.subscribe(() => states.push(f.connection.getSnapshot().phase));
  await Promise.all([f.connection.scan(), f.connection.scan()]);
  assert.equal(f.counts().connectCount, 0);
  assert.deepEqual(f.connection.getSnapshot().devices.map(d => d.id), ['watch']);
  await Promise.all([f.connection.connect('watch'), f.connection.connect('watch')]);
  assert.equal(f.connection.getSnapshot().phase, 'connected');
  assert.ok(states.includes('scanning'));
  assert.equal(states.at(-1), 'connected');
  assert.deepEqual(f.counts(), { scanCount: 1, stopCount: 1, connectCount: 1 });
  await f.connection.disconnect();
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  assert.equal(f.connection.getSnapshot().error, null);
  await f.connection.dispose();
});

test('missing watch times out, stops scanning, and permits retry', async () => {
  const f = fixture({ discover: false });
  await f.connection.scan();
  await f.connection.connect('watch');
  assert.equal(f.connection.getSnapshot().error, null);
  assert.deepEqual(f.connection.getSnapshot().devices, []);
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  assert.equal(f.counts().stopCount, 1);
  await f.connection.scan();
  await f.connection.connect('watch');
  assert.equal(f.counts().scanCount, 2);
  await f.connection.dispose();
});

for (const radio of ['PoweredOff', 'Unauthorized', 'Unsupported']) {
  test(`${radio} gives an actionable error without scanning`, async () => {
    const f = fixture({ radio });
    await f.connection.scan();
  await f.connection.connect('watch');
    assert.equal(f.counts().scanCount, 0);
    assert.ok(f.connection.getSnapshot().error);
    assert.equal(f.connection.getSnapshot().phase, 'disconnected');
    await f.connection.dispose();
  });
}

test('wrong services never report connected', async () => {
  const f = fixture({ compatible: false });
  await f.connection.scan();
  await f.connection.connect('watch');
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  assert.match(f.connection.getSnapshot().error, /not compatible/);
  await f.connection.dispose();
});

test('link loss updates subscribers and does not auto-reconnect', async () => {
  const f = fixture();
  await f.connection.scan();
  await f.connection.connect('watch');
  f.drop();
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  assert.match(f.connection.getSnapshot().error, /connection was lost/);
  assert.equal(f.counts().connectCount, 1);
  await f.connection.dispose();
});

test('Bluetooth switched off clears connected state', async () => {
  const f = fixture();
  await f.connection.scan();
  await f.connection.connect('watch');
  f.radio('PoweredOff');
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  assert.match(f.connection.getSnapshot().error, /Turn on Bluetooth/);
  await f.connection.dispose();
});

test('disconnect during service verification never reports success', async () => {
  const f = fixture({ drops: true });
  await f.connection.scan();
  await f.connection.connect('watch');
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  await f.connection.dispose();
});

test('unknown selection cannot connect', async () => {
  const f = fixture();
  await f.connection.scan();
  await f.connection.connect('not-found');
  assert.equal(f.counts().connectCount, 0);
  await f.connection.dispose();
});

test('closing the picker stops scanning without connecting', async () => {
  const f = fixture();
  const scanning = f.connection.scan();
  await new Promise(resolve => setTimeout(resolve, 2));
  await f.connection.stopScan();
  await scanning;
  assert.equal(f.connection.getSnapshot().phase, 'disconnected');
  assert.equal(f.counts().connectCount, 0);
  await f.connection.dispose();
});

test('multiple watches are deduplicated and only the selected watch connects', async () => {
  const f = fixture({ multiple: true });
  await f.connection.scan();
  assert.deepEqual(f.connection.getSnapshot().devices.map(d => d.id), ['watch', 'second-watch']);
  assert.equal(f.counts().connectCount, 0);
  await f.connection.connect('second-watch');
  assert.equal(f.connectedId(), 'second-watch');
  assert.equal(f.connection.getSnapshot().phase, 'connected');
  await f.connection.dispose();
});
