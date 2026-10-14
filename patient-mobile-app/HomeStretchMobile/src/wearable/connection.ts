import type { SessionDevice } from './curlSession';
// Connection ownership is shared with the exercise session.
export const SERVICE = '7bfa0001-6e4d-4b9d-923b-5d234081a100';
const uuid = (n: number) => `7bfa000${n}-6e4d-4b9d-923b-5d234081a100`;
type Subscription = { remove(): void };
type Characteristic = { uuid: string; isReadable: boolean; isNotifiable: boolean; isWritableWithResponse: boolean };
export interface WatchDevice extends SessionDevice {
  id: string;
  name: string | null;
  localName?: string | null;
  serviceUUIDs?: string[] | null;
  discoverAllServicesAndCharacteristics(): Promise<WatchDevice>;
  characteristicsForService(service: string): Promise<Characteristic[]>;
  isConnected(): Promise<boolean>;
}
export interface Bluetooth {
  onStateChange(listener: (state: string) => void, emit: boolean): Subscription;
  startDeviceScan(uuids: null, options: null, listener: (error: Error | null, device: WatchDevice | null) => void): Promise<void>;
  stopDeviceScan(): Promise<void>;
  connectToDevice(id: string, options: { timeout: number }): Promise<WatchDevice>;
  cancelDeviceConnection(id: string): Promise<unknown>;
  onDeviceDisconnected(id: string, listener: (error: Error | null) => void): Subscription;
}
export type ConnectionState = {
  phase: 'disconnected' | 'preparing' | 'scanning' | 'connecting' | 'connected' | 'disconnecting';
  devices: { id: string; name: string }[];
  selectedName: string | null;
  message: string;
  error: string | null;
};
const initial: ConnectionState = { devices: [], selectedName: null, phase: 'disconnected', message: 'Watch disconnected', error: null };
const bluetoothError = (state: string) => ({
  PoweredOff: 'Turn on Bluetooth on your iPhone, then try again.',
  Unauthorized: 'Allow Bluetooth for HomeStretchMobile in iPhone Settings → Privacy & Security → Bluetooth.',
  Unsupported: 'Bluetooth Low Energy is not available on this device.',
}[state]);

export class WatchConnection {
  private snapshot = initial;
  private listeners = new Set<() => void>();
  private manager?: Bluetooth;
  private stateSubscription?: Subscription;
  private disconnectSubscription?: Subscription;
  private device?: WatchDevice;
  private generation = 0;
  private pending = new Set<(error: Error) => void>();
  private finishScan?: () => void;
  private scanTask?: Promise<void>;
  private radio = 'Unknown';
  private createManager: () => Bluetooth;
  private timeoutMs: number;
  constructor(createManager: () => Bluetooth, timeoutMs = 15000) {
    this.createManager = createManager;
    this.timeoutMs = timeoutMs;
  }
  getConnectedDevice = () => this.snapshot.phase === 'connected' ? this.device : undefined;
  getSnapshot = () => this.snapshot;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  };
  private update(phase: ConnectionState['phase'], message: string, error: string | null = null) {
    this.snapshot = { ...this.snapshot, phase, message, error };
    this.listeners.forEach(listener => listener());
  }
  private stopPending(message: string) {
    for (const reject of [...this.pending]) reject(new Error(message));
  }
  private getManager() {
    if (!this.manager) {
      this.manager = this.createManager();
      this.stateSubscription = this.manager.onStateChange(state => {
        this.radio = state;
        const error = bluetoothError(state);
        if (error) {
          this.stopPending(error);
          if (this.snapshot.phase === 'connected') {
            this.generation++;
            this.disconnectSubscription?.remove();
            this.disconnectSubscription = undefined;
            const device = this.device;
            this.device = undefined;
            if (device) void this.manager?.cancelDeviceConnection(device.id).catch(() => {});
            this.update('disconnected', 'Watch disconnected', error);
          }
        }
      }, true);
    }
    return this.manager;
  }
  private bounded<T>(work: Promise<T>, message: string): Promise<T> {
    return new Promise((resolve, reject) => {
      const fail = (error: Error) => { cleanup(); reject(error); };
      const timer = setTimeout(() => fail(new Error(message)), this.timeoutMs);
      const cleanup = () => { clearTimeout(timer); this.pending.delete(fail); };
      this.pending.add(fail);
      work.then(value => { cleanup(); resolve(value); }, fail);
    });
  }
  private async waitForBluetooth(manager: Bluetooth) {
    let subscription: Subscription | undefined;
    try {
      await this.bounded(new Promise<void>((resolve, reject) => {
        subscription = manager.onStateChange(state => {
          this.radio = state;
          if (state === 'PoweredOn') resolve();
          const message = bluetoothError(state);
          if (message) reject(new Error(message));
        }, true);
      }), 'Bluetooth is not ready. Check your iPhone Bluetooth settings and try again.');
    } finally { subscription?.remove(); }
  }
  scan = () => {
    if (this.snapshot.phase !== 'disconnected') return this.scanTask ?? Promise.resolve();
    this.scanTask = this.findDevices();
    return this.scanTask;
  };
  private async findDevices() {
    const generation = ++this.generation;
    this.snapshot = { ...this.snapshot, devices: [], selectedName: null };
    this.update('preparing', 'Checking Bluetooth…');
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      const manager = this.getManager();
      await this.waitForBluetooth(manager);
      if (generation !== this.generation) return;
      this.update('scanning', 'Searching for watches…');
      await this.bounded(new Promise<void>((resolve, reject) => {
        this.finishScan = resolve;
        timer = setTimeout(resolve, this.timeoutMs - 1);
        void manager.startDeviceScan(null, null, (error, device) => {
          if (generation !== this.generation || this.snapshot.phase !== 'scanning') return;
          if (error) { reject(error); return; }
          if (!device || !(device.name === 'VitalWave-v0' || device.localName === 'VitalWave-v0' ||
              device.serviceUUIDs?.some(service => service.toLowerCase() === SERVICE))) return;
          const item = { id: device.id, name: device.localName || device.name || 'HomeStretch Watch' };
          const devices = this.snapshot.devices.filter(existing => existing.id !== item.id);
          this.snapshot = { ...this.snapshot, devices: [...devices, item] };
          this.update('scanning', 'Searching for watches…');
        }).catch(reject);
      }), 'Search timed out. Please try again.');
      if (generation === this.generation) this.update('disconnected', 'Watch disconnected');
    } catch (error) {
      if (generation === this.generation) this.update('disconnected', 'Watch disconnected',
        error instanceof Error ? error.message : 'Unable to search. Please try again.');
    } finally {
      clearTimeout(timer);
      this.finishScan = undefined;
      await this.manager?.stopDeviceScan().catch(() => {});
    }
  }
  stopScan = async () => {
    if (this.snapshot.phase === 'preparing') {
      this.stopPending('Search cancelled.');
    } else this.finishScan?.();
    await this.scanTask;
  };
  connect = async (id: string) => {
    if (!['disconnected', 'scanning'].includes(this.snapshot.phase)) return;
    const selected = this.snapshot.devices.find(device => device.id === id);
    if (!selected) return;
    await this.stopScan();
    if (this.snapshot.phase !== 'disconnected') return;
    const generation = ++this.generation;
    const candidate = selected;
    this.snapshot = { ...this.snapshot, selectedName: selected.name };
    this.update('connecting', 'Connecting…');
    try {
      const manager = this.getManager();
      await this.waitForBluetooth(manager);
      this.update('connecting', 'Connecting…');
      this.disconnectSubscription = manager.onDeviceDisconnected(candidate.id, () => {
        if (generation !== this.generation) return;
        if (this.snapshot.phase === 'connecting') this.stopPending('The watch disconnected while connecting. Please try again.');
        if (this.snapshot.phase === 'connected') {
          this.generation++;
          this.device = undefined;
          this.disconnectSubscription?.remove();
          this.disconnectSubscription = undefined;
          this.update('disconnected', 'Watch disconnected', 'The connection was lost. Bring the watch closer and reconnect.');
        }
      });
      const device = await this.bounded(manager.connectToDevice(candidate.id, { timeout: this.timeoutMs }), 'Unable to connect. Keep your watch nearby and try again.');
      await this.bounded(device.discoverAllServicesAndCharacteristics(), 'Could not discover the watch services. Try reconnecting.');
      const characteristics = await this.bounded(device.characteristicsForService(SERVICE), 'Could not verify the watch. Try reconnecting.');
      const characteristic = (n: number) => characteristics.find(item => item.uuid.toLowerCase() === uuid(n));
      if (!characteristic(2)?.isWritableWithResponse || !characteristic(3)?.isReadable ||
          !characteristic(3)?.isNotifiable || !characteristic(4)?.isNotifiable ||
          !characteristic(5)?.isReadable || !characteristic(5)?.isNotifiable) {
        throw new Error('This watch is not compatible with HomeStretch.');
      }
      const connected = await this.bounded(device.isConnected(), 'Could not confirm the watch connection.');
      if (!connected || this.radio !== 'PoweredOn') throw new Error('The watch disconnected. Please try again.');
      if (generation !== this.generation) return;
      this.device = device;
      this.update('connected', 'Watch connected');
    } catch (error) {
      if (generation !== this.generation) return;
      this.disconnectSubscription?.remove();
      this.disconnectSubscription = undefined;
      if (candidate) await this.manager?.cancelDeviceConnection(candidate.id).catch(() => {});
      this.device = undefined;
      this.update('disconnected', 'Watch disconnected', error instanceof Error ? error.message : 'Could not connect to the watch. Try again.');
    }
  };
  disconnect = async () => {
    if (this.snapshot.phase !== 'connected' || !this.device || !this.manager) return;
    const device = this.device;
    this.update('disconnecting', 'Disconnecting…');
    try {
      await this.bounded(this.manager.cancelDeviceConnection(device.id), 'Disconnect timed out. Turn off the watch to disconnect.');
      this.generation++;
      this.disconnectSubscription?.remove();
      this.disconnectSubscription = undefined;
      this.device = undefined;
      this.update('disconnected', 'Watch disconnected');
    } catch (error) {
      // Do not keep a green connected indicator when the link cannot be confirmed.
      this.generation++;
      this.disconnectSubscription?.remove();
      this.disconnectSubscription = undefined;
      this.device = undefined;
      this.update('disconnected', 'Connection not confirmed', error instanceof Error ? error.message : 'Could not disconnect. Turn off the watch.');
    }
  };
  dispose = async () => {
    this.generation++;
    this.finishScan?.();
    this.stopPending('Connection closed.');
    this.stateSubscription?.remove();
    this.disconnectSubscription?.remove();
    await this.manager?.stopDeviceScan().catch(() => {});
    if (this.device) await this.manager?.cancelDeviceConnection(this.device.id).catch(() => {});
    this.device = undefined;
    this.listeners.clear();
  };
}
