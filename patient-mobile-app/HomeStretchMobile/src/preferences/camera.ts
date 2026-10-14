import { useSyncExternalStore } from 'react';
import { Platform, Settings } from 'react-native';

const key = 'HomeStretchExerciseCameraEnabled';
// iOS Settings stores this preference across app launches; permission is separate.
let enabled = Platform.OS === 'ios' ? Settings.get(key) !== false : true;
const listeners = new Set<() => void>();
function setEnabled(value: boolean) {
  if (Platform.OS === 'ios') Settings.set({ [key]: value });
  enabled = value;
  listeners.forEach(listener => listener());
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
export function useCameraPreference(): [boolean, (value: boolean) => void] {
  return [useSyncExternalStore(subscribe, () => enabled, () => true), setEnabled];
}
