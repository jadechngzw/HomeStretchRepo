import { command, samples, status, UUID } from './protocol';
import type { WatchStatus } from './protocol';
import { CurlCounter } from './curlCounter';
import type { RepEvent } from './curlCounter';
type Subscription = { remove(): void };
type Value = { value: string | null };
export interface SessionDevice {
  monitorCharacteristicForService(service: string, characteristic: string, listener: (error: Error | null, value: Value | null) => void): Subscription;
  readCharacteristicForService(service: string, characteristic: string): Promise<Value>;
  writeCharacteristicWithResponseForService(service: string, characteristic: string, value: string): Promise<unknown>;
}
export type Arm = 'left' | 'right';
export type SetState = {
  phase: 'idle' | 'starting' | 'calibrating' | 'active' | 'stopping' | 'ended' | 'interrupted';
  arm: Arm | null; reps: number; repDurations: number[]; message: string;
  sessionId: number; startedAt: number | null; endedAt: number | null;
  received: number; missing: number; invalid: number; unexpected: number;
  complete: boolean | null;
};
const empty = (): SetState => ({ phase: 'idle', arm: null, reps: 0, repDurations: [], message: '', sessionId: 0,
  startedAt: null, endedAt: null, received: 0, missing: 0, invalid: 0, unexpected: 0, complete: null });
export const isSetRunning = (state: SetState) => ['starting', 'calibrating', 'active', 'stopping'].includes(state.phase);
export class CurlSession {
  private snapshot = empty();
  private listeners = new Set<() => void>();
  private repListeners = new Set<(rep: RepEvent) => void>();
  private counter = new CurlCounter();
  private device?: SessionDevice;
  private subscriptions: Subscription[] = [];
  private heartbeat?: ReturnType<typeof setInterval>;
  private lastSampleAt = 0;
  private request = 0;
  private queue: Promise<unknown> = Promise.resolve();
  private pendingAck?: { request: number; accept: (value: WatchStatus) => void };
  private pingBusy = false;
  private epoch = 0;
  private previousSequence?: number;
  private previousMs?: number;
  private elapsedMs = 0;
  private getDevice: () => SessionDevice | undefined;
  private timing: { ack: number; io: number; drain: number; heartbeat: number; stall: number };
  constructor(getDevice: () => SessionDevice | undefined, timing = { ack: 1000, io: 1500, drain: 3000, heartbeat: 1000, stall: 4000 }) {
    this.getDevice = getDevice; this.timing = timing;
  }
  getSnapshot = () => this.snapshot;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  // Future live-guidance state machine can consume these completed-rep events.
  onRep = (listener: (rep: RepEvent) => void) => { this.repListeners.add(listener); return () => { this.repListeners.delete(listener); }; };
  private update(patch: Partial<SetState>) {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach(listener => listener());
  }
  private async deadline<T>(promise: Promise<T>, ms: number): Promise<T> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      return await Promise.race([promise, new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error('The watch did not respond. Reconnect and try again.')), ms);
      })]);
    } finally { clearTimeout(timer); }
  }
  private receiveStatus = (value: string | null) => {
    const decoded = status(value);
    if (this.pendingAck?.request === decoded.request) this.pendingAck.accept(decoded);
    if (['active', 'calibrating'].includes(this.snapshot.phase) &&
        (decoded.session !== this.snapshot.sessionId || decoded.state !== 1 || decoded.reason !== 0)) {
      this.interrupt('The watch stopped recording. Reconnect before starting another set.');
    }
    return decoded;
  };
  private send(opcode: number, argument = 0): Promise<WatchStatus> {
    const epoch = this.epoch;
    const job = this.queue.then(async () => {
      if (epoch !== this.epoch || !this.device) throw new Error('Set interrupted.');
      const device = this.device;
      const request = this.request = this.request % 65535 + 1;
      let acknowledged: WatchStatus | undefined;
      let signal: (() => void) | undefined;
      const wait = new Promise<void>(resolve => { signal = resolve; });
      this.pendingAck = { request, accept: result => { acknowledged = result; signal?.(); } };
      try {
        await this.deadline(device.writeCharacteristicWithResponseForService(UUID.service, UUID.control,
          command(opcode, request, argument, this.snapshot.sessionId)), this.timing.io);
        if (!acknowledged) {
          let timer: ReturnType<typeof setTimeout> | undefined;
          try { await Promise.race([wait, new Promise<void>(resolve => { timer = setTimeout(resolve, this.timing.ack); })]); }
          finally { clearTimeout(timer); }
        }
        if (!acknowledged) {
          const value = await this.deadline(device.readCharacteristicForService(UUID.service, UUID.status), this.timing.io);
          if (epoch !== this.epoch) throw new Error('Set interrupted.');
          const readback = this.receiveStatus(value.value);
          if (readback.request === request) acknowledged = readback;
        }
        if (epoch !== this.epoch) throw new Error('Set interrupted.');
        const result = acknowledged as WatchStatus | undefined;
        const expectedState = opcode === 1 || opcode === 3 ? 1 : 0;
        // CONFIGURE does not change session.id in the firmware; all other commands must match.
        if (!result || result.request !== request || result.reason !== 0 || result.state !== expectedState ||
            (opcode !== 4 && result.session !== this.snapshot.sessionId) || result.charger === 2 ||
            ((opcode === 1 || opcode === 3) && result.mask !== 1)) {
          throw new Error('The watch could not confirm the request. Reconnect and try again.');
        }
        return result;
      } finally { if (this.pendingAck?.request === request) this.pendingAck = undefined; }
    });
    this.queue = job.catch(() => {});
    return job;
  }
  private receiveSamples(value: string | null) {
    if (!isSetRunning(this.snapshot)) return;
    const frames = samples(value);
    let { received, missing, invalid, unexpected } = this.snapshot;
    for (const frame of frames) {
      if (frame.session !== this.snapshot.sessionId || frame.type !== 1) {
        unexpected++; this.counter.discardPartial(); continue;
      }
      this.lastSampleAt = Date.now();
      const expected = this.previousSequence === undefined ? 0 : (this.previousSequence + 1) & 65535;
      const delta = (frame.sequence - expected + 65536) & 65535;
      if (delta > 32767) { unexpected++; this.counter.discardPartial(); continue; }
      if (delta) { missing += delta; this.counter.noteMissing(delta); }
      this.previousSequence = frame.sequence;
      received++;
      if (this.previousMs !== undefined) {
        const elapsed = (frame.ms - this.previousMs) >>> 0;
        if (!elapsed || elapsed > 0x7fffffff) { invalid++; this.counter.discardPartial(); continue; }
        this.elapsedMs += elapsed;
      }
      this.previousMs = frame.ms;
      if (!frame.valid) { invalid++; this.counter.noteMissing(); continue; }
      const event = this.counter.add(this.elapsedMs, frame.y * 0.000061);
      if (event) {
        this.snapshot = { ...this.snapshot, reps: event.count, repDurations: [...this.snapshot.repDurations, event.durationSec] };
        this.repListeners.forEach(listener => listener(event));
      }
    }
    const phase = ['calibrating', 'active'].includes(this.snapshot.phase)
      ? this.counter.ready ? 'active' : 'calibrating' : this.snapshot.phase;
    this.update({ received, missing, invalid, unexpected, phase,
      message: phase === 'active' ? 'Counting your reps' : phase === 'calibrating' ? 'Hold your arm still at your side' : this.snapshot.message });
  }
  start = async (arm: Arm) => {
    if (isSetRunning(this.snapshot)) return;
    const device = this.getDevice();
    if (!device) { this.update({ phase: 'interrupted', message: 'Connect your watch before starting.', complete: false }); return; }
    if (arm !== 'left' && arm !== 'right') return;
    const epoch = ++this.epoch;
    this.cleanup(); this.device = device; this.counter = new CurlCounter();
    this.previousSequence = undefined; this.previousMs = undefined; this.elapsedMs = 0;
    this.snapshot = empty();
    this.update({ phase: 'starting', arm, sessionId: ((Date.now() ^ Math.floor(Math.random() * 0xffffffff)) >>> 0) || 1, message: 'Preparing your watch…' });
    try {
      this.subscriptions.push(device.monitorCharacteristicForService(UUID.service, UUID.status, (error, value) => {
        if (epoch !== this.epoch) return;
        if (error) { this.interrupt('Watch connection interrupted. Reconnect to start a new set.'); return; }
        if (value) try { this.receiveStatus(value.value); } catch (e) { this.interrupt(this.errorMessage(e)); }
      }));
      this.subscriptions.push(device.monitorCharacteristicForService(UUID.service, UUID.samples, (error, value) => {
        if (epoch !== this.epoch) return;
        if (error) { this.interrupt('Movement data was interrupted. Reconnect to start a new set.'); return; }
        if (value) try { this.receiveSamples(value.value); } catch (e) { this.interrupt(this.errorMessage(e)); }
      }));
      const initial = status((await this.deadline(device.readCharacteristicForService(UUID.service, UUID.status), this.timing.io)).value);
      if (epoch !== this.epoch) return;
      if (initial.state !== 0 || initial.charger === 2) throw new Error('Your watch is not ready. Reconnect and try again.');
      // 50 Hz acceleration; PPG disabled. Keep other sensor settings valid.
      await this.send(4, 50 | (10 << 8) | (50 << 16));
      if (epoch !== this.epoch) return;
      await this.send(1, 1);
      if (epoch !== this.epoch) return;
      this.lastSampleAt = Date.now();
      this.update({ phase: this.counter.ready ? 'active' : 'calibrating', startedAt: Date.now(), message: 'Hold your arm still at your side' });
      this.heartbeat = setInterval(() => {
        if (!['active', 'calibrating'].includes(this.snapshot.phase)) return;
        if (Date.now() - this.lastSampleAt > this.timing.stall) { this.interrupt('Movement data stopped. Reconnect before starting another set.'); return; }
        if (this.pingBusy) return;
        this.pingBusy = true;
        void this.send(3).catch(e => { if (epoch === this.epoch) this.interrupt(this.errorMessage(e)); }).finally(() => { this.pingBusy = false; });
      }, this.timing.heartbeat);
    } catch (error) { if (epoch === this.epoch) this.interrupt(this.errorMessage(error)); }
  };
  stop = async () => {
    if (!['active', 'calibrating'].includes(this.snapshot.phase)) return;
    const epoch = this.epoch;
    clearInterval(this.heartbeat);
    this.update({ phase: 'stopping', message: 'Finishing your set…' });
    try {
      const stopped = await this.send(2);
      const until = Date.now() + this.timing.drain;
      while (epoch === this.epoch && this.snapshot.received < stopped.generated - stopped.dropped && Date.now() < until) {
        await new Promise(resolve => setTimeout(resolve, 25));
      }
      if (epoch !== this.epoch) return;
      const complete = stopped.dropped === 0 && this.snapshot.received === stopped.generated &&
        this.snapshot.missing === 0 && this.snapshot.invalid === 0 && this.snapshot.unexpected === 0;
      this.epoch++; this.cleanup();
      this.update({ phase: 'ended', endedAt: Date.now(), complete,
        message: complete ? 'Set finished' : 'Set finished. Some movement data was missing; the count may be incomplete.' });
    } catch (error) { if (epoch === this.epoch) this.interrupt(this.errorMessage(error)); }
  };
  interrupt = (message = 'Set interrupted. Start a new set when you are ready.') => {
    if (!isSetRunning(this.snapshot)) return;
    this.epoch++;
    // Unsubscribing stops acquisition in the firmware; keepalive expiry is a fallback.
    this.cleanup();
    this.update({ phase: 'interrupted', endedAt: Date.now(), complete: false, message });
  };
  private cleanup() {
    clearInterval(this.heartbeat); this.heartbeat = undefined;
    const subscriptions = this.subscriptions; this.subscriptions = [];
    for (const subscription of subscriptions) subscription.remove();
    this.pendingAck = undefined; this.pingBusy = false;
  }
  private errorMessage(error: unknown) { return error instanceof Error ? error.message : 'The set was interrupted. Please reconnect.'; }
}
