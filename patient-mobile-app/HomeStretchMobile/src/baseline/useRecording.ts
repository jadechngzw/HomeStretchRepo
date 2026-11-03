import { useEffect, useSyncExternalStore } from 'react';
import { AppState } from 'react-native';
import { connection } from '../wearable/useWearable';
import { BaselineRecorder } from '../wearable/baselineRecorder';
import { isSetRunning } from '../wearable/curlSession';
export const recorder = new BaselineRecorder(() => connection.getConnectedDevice());
connection.subscribe(() => { if (connection.getSnapshot().phase !== 'connected')
    recorder.interrupt('Watch disconnected. This recording was not saved.'); });
export function useRecording() {
    const state = useSyncExternalStore(recorder.subscribe, recorder.getSnapshot, recorder.getSnapshot);
    useEffect(() => { const sub = AppState.addEventListener('change', next => { if (next !== 'active')
        recorder.interrupt('Recording interrupted when the app left the screen. Nothing was saved.'); }); return () => sub.remove(); }, []);
    return { ...state, running: isSetRunning(state) };
}
