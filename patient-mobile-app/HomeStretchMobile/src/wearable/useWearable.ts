import { useSyncExternalStore } from 'react';
import { Platform } from 'react-native';
import type { BleManager } from 'react-native-ble-plx';
import { WatchConnection } from './connection';

// One owner keeps Settings and Exercise on the same real connection.
// Load native Bluetooth only after a tap, so web and Expo Go can show an error.
export const connection = new WatchConnection(() => {
  if (Platform.OS !== 'ios') {
    throw new Error('This first watch connection is for the iPhone development build.');
  }
  try {
    const BLE = require('react-native-ble-plx') as { BleManager: typeof BleManager };
    return new BLE.BleManager();
  } catch {
    throw new Error('Open your installed HomeStretchMobile development build, rather than Expo Go.');
  }
});

export function useWearable() {
  const state = useSyncExternalStore(connection.subscribe, connection.getSnapshot, connection.getSnapshot);
  return {
    ...state,
    busy: !['connected', 'disconnected'].includes(state.phase),
    scan: connection.scan,
    stopScan: connection.stopScan,
    connect: connection.connect,
    disconnect: connection.disconnect,
  };
}
