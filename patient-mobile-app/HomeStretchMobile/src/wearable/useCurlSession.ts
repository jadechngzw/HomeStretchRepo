import { useEffect, useSyncExternalStore } from 'react';
import { AppState } from 'react-native';
import { connection } from './useWearable';
import { CurlSession, isSetRunning } from './curlSession';

const session = new CurlSession(() => connection.getConnectedDevice());
connection.subscribe(() => {
  if (connection.getSnapshot().phase !== 'connected') session.interrupt('Watch disconnected. Reconnect before starting a new set.');
});
export function useCurlSession() {
  const state = useSyncExternalStore(session.subscribe, session.getSnapshot, session.getSnapshot);
  useEffect(() => {
    const listener = AppState.addEventListener('change', next => {
      if (next === 'background') session.interrupt('Set interrupted when the app left the screen. Start a new set when ready.');
    });
    return () => listener.remove();
  }, []);
  return { ...state, running: isSetRunning(state), start: session.start, stop: session.stop, interrupt: session.interrupt };
}
