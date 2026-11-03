import React, { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { Alert, AppState, Linking, Pressable, Text, View } from 'react-native';
import { router, useFocusEffect, useNavigation } from 'expo-router';
import { usePreventRemove } from 'expo-router/react-navigation';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { makeSession } from '../sync/schema';
import type { PatientProfile } from '../sync/schema';
import { syncSessions } from '../sync/upload';
import { getCatalog, saveSession, useCatalog } from './store';
import { uid } from './types';
import { useCameraPreference } from '../preferences/camera';
import { connection, useWearable } from '../wearable/useWearable';
import { BaselineRecorder, isSetRunning } from '../wearable/baselineRecorder';
import { assessFrames, paceCue } from './liveGuidance';
import type { LiveResult } from './liveGuidance';
import type { Baseline, Exercise, Survey } from './types';
import { sideLabel } from './types';
import { Button, Card, Hint, Page, s, colors } from './ui';

export default function LiveExercise({ exercise, baselines, preSurvey, preferredBaselineId }: {
  exercise: Exercise; baselines: Baseline[]; preSurvey?: Survey; preferredBaselineId?: string;
}) {
  const catalog=useCatalog();
  const [savedId,setSavedId]=useState('');
  const patient=useRef<PatientProfile|null>(null);
  const saved=catalog.data.sessionUploads?.find(s=>s.document.session_id===savedId);
  const [recorder] = useState(() => new BaselineRecorder(() => connection.getConnectedDevice()));
  const capture = useSyncExternalStore(recorder.subscribe, recorder.getSnapshot, recorder.getSnapshot);
  const running = isSetRunning(capture), wearable = useWearable(), navigation = useNavigation();
  const [selectedId, setSelectedId] = useState(preferredBaselineId ?? '');
  const selected = baselines.find(b => b.id === selectedId) ?? baselines[0];
  const frozen = useRef<Baseline | null>(null);
  const sessionSurvey = useRef<Survey | undefined>(undefined);
  const [placementConfirmed, setPlacementConfirmed] = useState(false);
  const [result, setResult] = useState<LiveResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false), [finishing, setFinishing] = useState(false);
  const lock = useRef(false), mounted = useRef(true), timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [now, setNow] = useState(Date.now()), [focused, setFocused] = useState(false);
  const [cameraEnabled] = useCameraPreference(), [permission, requestPermission] = useCameraPermissions();
  const badData = capture.invalid > 0 || capture.missing > 0 || capture.unexpected > 0 || capture.phase === 'interrupted';
  const reps = result?.reps ?? [], latest = reps.at(-1);
  const pace = paceCue(reps.filter(r => r.assessable).map(r => r.duration));
  const elapsed = capture.startedAt ? Math.max(0, (now - capture.startedAt) / 1000) : 0;
  useEffect(() => { setPlacementConfirmed(false); }, [selected?.id]);
  useEffect(() => {
    mounted.current = true;
    const sub = AppState.addEventListener('change', state => { if (state !== 'active') recorder.interrupt('Set interrupted when the app left the screen. Start a new set when ready.'); });
    const unsubscribe = connection.subscribe(() => { if (connection.getSnapshot().phase !== 'connected') recorder.interrupt('Watch disconnected. Reconnect and start a new set.'); });
    return () => { mounted.current = false; clearTimeout(timer.current); recorder.interrupt(); sub.remove(); unsubscribe(); };
  }, [recorder]);
  useFocusEffect(useCallback(() => { setFocused(true); return () => { setFocused(false); clearTimeout(timer.current); recorder.interrupt('Set interrupted when you left the exercise.'); }; }, [recorder]));
  usePreventRemove(running, ({data}) => {
    Alert.alert('End this set?', 'Leaving stops recording. This set will be marked interrupted.', [
      {text:'Keep exercising',style:'cancel'}, {text:'End and leave',style:'destructive',onPress:()=>{clearTimeout(timer.current);recorder.interrupt();navigation.dispatch(data.action);}},
    ]);
  });
  useEffect(() => {
    if (capture.phase === 'interrupted') { clearTimeout(timer.current); setFinishing(false); setBusy(false); lock.current = false; }
  }, [capture.phase]);
  useEffect(() => {
    if (!running) return;
    const clock = setInterval(() => setNow(Date.now()), 250);
    const refresh = setInterval(() => {
      const state = recorder.getSnapshot(), frames = recorder.getFrames();
      if (!frozen.current || frames.length < 150 || state.missing || state.invalid || state.unexpected || state.phase !== 'active') return;
      try { setResult(assessFrames(frames, frozen.current.reference)); setError(''); }
      catch (e) { setError(e instanceof Error ? e.message : 'Movement could not be assessed.'); }
    }, 750);
    return () => { clearInterval(clock); clearInterval(refresh); };
  }, [running, recorder]);
  async function start() {
    if (lock.current || !preSurvey || !selected || !placementConfirmed) return;
    lock.current = true; setBusy(true); setError(''); setSavedId(''); setResult(null); setFinishing(false);
    // Freeze both reference and survey for this set, even if the catalog changes elsewhere.
    frozen.current = JSON.parse(JSON.stringify(selected)) as Baseline;
    sessionSurvey.current = {...preSurvey};
    patient.current = getCatalog().data.patientProfile ? {...getCatalog().data.patientProfile!} : null;
    try { await recorder.start(selected.placement.wrist); setNow(Date.now()); }
    finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  async function stop() {
    await recorder.stop();
    if (!mounted.current) return;
    const state = recorder.getSnapshot(); setNow(Date.now()); setFinishing(false);
    if (state.phase !== 'ended' || !state.complete) { lock.current=false; setBusy(false); setError('This set could not be fully assessed because movement data was missing or interrupted. Start a new set.'); return; }
    try {
      const final = assessFrames(recorder.getFrames(), frozen.current!.reference, true); setResult(final); setError('');
      const id=uid();
      const document=makeSession({id,patient:patient.current,exercise,startedAt:state.startedAt!,endedAt:state.endedAt!,protocolSessionId:state.sessionId,survey:sessionSurvey.current,baseline:frozen.current!,result:final,complete:true});
      await saveSession(document,recorder.getFrames());
      if(mounted.current && recorder.getSnapshot().sessionId===state.sessionId)setSavedId(id);
      void syncSessions().catch(()=>{});
    } catch (e) { setError(e instanceof Error?e.message:'This set could not be assessed.'); }
    finally { lock.current=false; if(mounted.current)setBusy(false); }
  }
  function finish() {
    if (lock.current || !running || capture.phase !== 'active') return;
    lock.current = true; setBusy(true); setFinishing(true);
    timer.current = setTimeout(()=>{void stop();},2000);
  }
  const ended = capture.phase === 'ended' || capture.phase === 'interrupted';
  const status = finishing ? 'Return to your starting position and hold' : capture.phase === 'starting' ? 'Getting ready…'
    : capture.phase === 'interrupted' ? 'Let’s try that set again' : capture.phase === 'ended' ? (badData || error ? 'Set finished' : 'Nice work—set complete!')
    : running && elapsed < 2 ? 'Hold still for a moment' : !running ? 'Let’s start!'
    : badData || error ? 'Pause and check your watch' : reps.length >= exercise.reps ? 'You did it! End the set when you’re ready.'
    : pace === 'slow' ? 'Try a slightly quicker, steady pace' : pace === 'fast' ? 'Slow down a little—you’ve got this'
    : !reps.length ? 'Let’s go—you’ve got this!' : reps.length % 2 ? 'Keep going—you’ve got this!' : 'Nice and steady. Keep it up!';
  return <Page title={exercise.name}>
    {!running && <View style={{gap:8}}>
      <Text style={s.small}>{sideLabel(selected.placement.side)} · {selected.placement.wrist} wrist · face {selected.placement.face === 'top' ? 'on top' : 'inside'}</Text>
      {baselines.length > 1 && baselines.map(b=><Button key={b.id} title={`${sideLabel(b.placement.side)} · ${b.placement.wrist} wrist · ${b.placement.face}${selected.id===b.id?' ✓':''}`} secondary onPress={()=>{setSelectedId(b.id);setPlacementConfirmed(false);frozen.current=null;setResult(null);setError('');}}/>)}
      <Pressable accessibilityRole="checkbox" accessibilityState={{checked:placementConfirmed}} onPress={()=>setPlacementConfirmed(!placementConfirmed)} style={[s.choice,{backgroundColor:placementConfirmed?colors.green:'#fff'}]}><Text style={s.text}>{placementConfirmed?'☑':'☐'} Watch in place—I’m ready</Text></Pressable>
    </View>}
    <Text style={s.small}>{wearable.message}</Text>
    {wearable.phase!=='connected'&&<Button title="Connect watch" secondary onPress={()=>router.push('/settings')}/>}
    {!running&&<Button title={preSurvey?`Pain before exercise: ${preSurvey.pain}/10 · Update`:'Complete pre-exercise survey'} secondary onPress={()=>router.push({pathname:'/survey',params:{phase:'before',exerciseId:exercise.id,returnTo:'exercise'}})}/>}
    <Card><Text accessibilityLiveRegion="polite" style={[s.title,{textAlign:'center'}]}>{status}</Text><Text style={{fontSize:54,color:colors.blue,textAlign:'center',fontWeight:'600'}}>{reps.length} <Text style={{fontSize:20}}>/ {exercise.reps}</Text></Text><Text style={[s.small,{textAlign:'center'}]}>Reps · {Math.floor(elapsed/60)}:{String(Math.floor(elapsed%60)).padStart(2,'0')}</Text></Card>
    {running?<Button title={finishing?'Finishing…':'End set'} danger busy={busy} disabled={capture.phase!=='active'} onPress={finish}/>:<Button title={ended?'Start next set':'Start exercise'} busy={busy} disabled={!preSurvey||!placementConfirmed||wearable.phase!=='connected'} onPress={()=>void start()}/>}
    {badData?<Hint error>{capture.phase==='interrupted'?capture.message:'Movement data is missing or invalid. Rep comparisons are unavailable for this set.'}</Hint>:error?<Hint error>{error}</Hint>:latest&&<View style={[s.card,{backgroundColor:!latest.assessable?colors.card:latest.flags.length?colors.amber:colors.green}]}><Text accessibilityLiveRegion="polite" style={s.title}>Rep {latest.id}: {!latest.assessable?'Could not assess':latest.flags.length?'Atypical':'Within range'}</Text></View>}
    {cameraEnabled&&permission?.granted&&focused?<CameraView facing="front" style={{height:260,borderRadius:16}}/>:cameraEnabled&&<Button title="Enable exercise camera" secondary onPress={()=>{if(permission?.canAskAgain===false)void Linking.openSettings();else void requestPermission();}}/>}
    {saved&&<Text accessibilityLiveRegion="polite" style={s.small}>{saved.status==='synced'?'Session synced':'Saved on phone · sync pending'}</Text>}
    {!running&&<><Button title="Post-exercise survey" secondary disabled={busy} onPress={()=>router.push({pathname:'/survey',params:{exerciseId:exercise.id,sessionId:savedId}})}/></>}
  </Page>;
}
