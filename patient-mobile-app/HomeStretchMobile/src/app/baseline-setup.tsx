import { activeBaselines, isActive } from '../baseline/activation';
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable } from 'react-native';
import { router, useLocalSearchParams, useNavigation } from 'expo-router';
import { usePreventRemove } from 'expo-router/react-navigation';
import { Alert } from 'react-native';
import { Page, Card, Button, Hint, Steps, Choice, Badge, s, colors } from '../baseline/ui';
import { addExercise, exercises, saveBaseline, useCatalog } from '../baseline/store';
import { sideLabel } from '../baseline/types';
import type { Placement } from '../baseline/types';
import { analyze, buildReference, FEATURES, LABELS } from '../baseline/analysis';
import type { Analysis } from '../baseline/analysis';
import { recorder, useRecording } from '../baseline/useRecording';
import { useWearable } from '../wearable/useWearable';
type Step = 'choose' | 'details' | 'prepare' | 'record' | 'review' | 'saved';
export default function BaselineSetup() {
    const navigation = useNavigation();
    const params = useLocalSearchParams<{
        exerciseId?: string;
        surveyId?: string;
        replaceId?: string;
    }>();
    const catalog = useCatalog(), wearable = useWearable(), recording = useRecording();
    const [step, setStep] = useState<Step>(params.exerciseId ? 'details' : 'choose');
    const [exerciseId, setExerciseId] = useState(params.exerciseId ?? '');
    const [search, setSearch] = useState(''), [name, setName] = useState('');
    const [placement, setPlacement] = useState<Placement>({ side: 'right', wrist: 'right', face: 'top', notes: '' });
    const [error, setError] = useState(''), [busy, setBusy] = useState(false), [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [ids, setIds] = useState<number[]>([]), [technical, setTechnical] = useState(false), [savedId, setSavedId] = useState('');
    const [now, setNow] = useState(Date.now()), [finishing, setFinishing] = useState(false), [liveReps, setLiveReps] = useState(0);
    const operationLock = useRef(false);
    const mounted = useRef(true), initialized = useRef(false), finishTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    const all = exercises(catalog.data), exercise = all.find(e => e.id === exerciseId);
    const survey = catalog.data.surveys.find(s => s.id === params.surveyId && s.phase === 'before' && s.exerciseId === exerciseId);
    useEffect(() => { if (!initialized.current && catalog.ready) {
        initialized.current = true;
        const previous = catalog.data.baselines.find(b => b.id === params.replaceId);
        if (previous)
            setPlacement({ ...previous.placement });
    } }, [catalog.ready, params.replaceId, catalog.data.baselines]);
    useEffect(() => { mounted.current = true; return () => { mounted.current = false; clearTimeout(finishTimer.current); recorder.interrupt(); }; }, []);
    usePreventRemove(busy || recording.running || step === 'review' || (step === 'record' && !!analysis), ({ data }) => {
        if (busy) {
            Alert.alert('Please wait', 'The recording is being saved or prepared.');
            return;
        }
        Alert.alert('Leave this recording?', 'The unsaved recording will be discarded.', [{ text: 'Stay', style: 'cancel' }, { text: 'Discard', style: 'destructive', onPress: () => { clearTimeout(finishTimer.current); recorder.interrupt(); navigation.dispatch(data.action); } }]);
    });
    useEffect(() => { if (!recording.running)
        return; const timer = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(timer); }, [recording.running]);
    useEffect(() => { if (step === 'record' && recording.phase === 'interrupted') {
        clearTimeout(finishTimer.current);
        setFinishing(false);
        setError(recording.message);
    } }, [recording.phase, recording.message, step]);
    // Provisional live count; final features are recalculated from the complete drained recording.
    useEffect(() => { if (!recording.running)
        return; const timer = setInterval(() => { try {
        setLiveReps(analyze(recorder.getFrames()).reps.length);
    }
    catch { /* Initial hold / too little data: no count yet. */ } }, 1500); return () => clearInterval(timer); }, [recording.running]);
    const pending = catalog.data.baselines.filter(b => b.exerciseId === exerciseId);
    const elapsed = recording.startedAt ? Math.max(0, (now - recording.startedAt) / 1000) : 0;
    async function run(action: () => Promise<void>) { if (operationLock.current)
        return; operationLock.current = true; setBusy(true); setError(''); try {
        await action();
    }
    catch (e) {
        setError(e instanceof Error ? e.message : 'Something went wrong. Please try again.');
    }
    finally {
        operationLock.current = false;
        if (mounted.current)
            setBusy(false);
    } }
    async function start() { setError(''); setAnalysis(null); setIds([]); setLiveReps(0); setFinishing(false); setStep('record'); await recorder.start(placement.wrist); setNow(Date.now()); }
    async function finish() { setFinishing(true); clearTimeout(finishTimer.current); finishTimer.current = setTimeout(() => { void run(async () => { await recorder.stop(); setFinishing(false); const snap = recorder.getSnapshot(); if (snap.phase !== 'ended' || !snap.complete)
        throw new Error(snap.message || 'Some movement data was missing. Record again.'); const result = analyze(recorder.getFrames()); setAnalysis(result); setIds(result.reps.filter(r => r.eligible).map(r => r.id)); if (result.reps.filter(r => r.eligible).length < 3)
        setError(`We found ${result.reps.filter(r => r.eligible).length} usable repetitions. At least 3 are needed. Please record again.`); }); }, 2000); }
    function reset() { clearTimeout(finishTimer.current); recorder.interrupt(); setAnalysis(null); setError(''); setFinishing(false); setStep('prepare'); }
    const back = () => { if (busy)
        return; if (step === 'choose' || step === 'saved')
        router.back();
    else if (recording.running || step === 'review' || analysis) {
        Alert.alert('Discard this recording?', 'This recording has not been saved.', [{ text: 'Keep recording', style: 'cancel' }, { text: 'Discard', style: 'destructive', onPress: reset }]);
    }
    else
        setStep(step === 'details' ? 'choose' : 'details'); };
    if (!catalog.ready)
        return <Page title="Set Up Baseline"><Text style={s.text}>Loading your exercises…</Text></Page>;
    if (catalog.error)
        return <Page title="Set Up Baseline"><Hint error>{catalog.error} Your saved data has not been replaced.</Hint></Page>;
    let reference;
    try {
        if (analysis && ids.length >= 3)
            reference = buildReference(analysis, ids);
    }
    catch { /* Selection helper below reports the minimum. */ }
    const stepNumber = step === 'choose' || step === 'details' ? 0 : step === 'prepare' ? 1 : step === 'record' ? 2 : 3;
    return <Page title={step === 'record' ? 'Recording Baseline' : step === 'review' ? 'Review Recording' : step === 'saved' ? (exercise?.name ?? 'Recording saved') : step === 'choose' ? 'Set Up Baseline' : exercise?.name ?? 'Set Up Baseline'} onBack={back}>
  {step !== 'saved' && <Steps current={stepNumber}/>}
  {!!error && <Hint error>{error}</Hint>}
  {step === 'choose' && <>
   <TextInput accessibilityLabel="Search exercises" placeholder="Search exercises" value={search} onChangeText={setSearch} style={s.input}/>
   <Text style={s.title}>Your exercises</Text>
   {all.filter(e => e.name.toLowerCase().includes(search.toLowerCase())).map(e => <Pressable key={e.id} accessibilityRole="button" onPress={() => { setExerciseId(e.id); setStep('details'); setError(''); }}><Card><View style={s.row}><Text style={[s.title, { flex: 1 }]}>{e.name}</Text><Text style={{ color: colors.blue }}>›</Text></View><Badge active={activeBaselines(catalog.data, e.id).length > 0} pending={catalog.data.baselines.some(b => b.exerciseId === e.id && b.status === "awaiting-review")}/></Card></Pressable>)}
   {!all.some(e => e.name.toLowerCase().includes(search.toLowerCase())) && <Text style={s.small}>No matching exercises. Add one below.</Text>}
   <Text style={s.title}>Add a new exercise</Text>
   <TextInput accessibilityLabel="New exercise name" maxLength={80} value={name} onChangeText={setName} placeholder="Type an exercise name" style={s.input}/>
   <Button title="Add exercise" disabled={!name.trim()} busy={busy} onPress={() => void run(async () => { const id = await addExercise(name); setExerciseId(id); setStep('details'); })}/>
   <Hint>Comparing movement with a baseline is experimental and has not been checked for every exercise. Saved baselines are automatically activated on this device for experimental live guidance.</Hint>
  </>}
  {step === 'details' && <>
   <Card><Text style={s.title}>Baseline status</Text><Badge active={activeBaselines(catalog.data, exerciseId).length > 0} pending={pending.some(b=>b.status === "awaiting-review")}/><Text style={s.small}>{pending.length ? 'A reference recording is saved. A new baseline becomes active for the same side and watch placement; previous recordings are kept.' : 'Record your reference movement for this exercise.'}</Text></Card>
   <Choice label="Which side are you exercising?" value={placement.side} options={[{ value: 'left', label: 'Left' }, { value: 'right', label: 'Right' }, { value: 'both', label: 'Both' }, { value: 'na', label: 'N/A' }]} onChange={side => setPlacement({ ...placement, side })}/>
   <Choice label="Which wrist is the watch on?" value={placement.wrist} options={[{ value: 'left', label: 'Left wrist' }, { value: 'right', label: 'Right wrist' }]} onChange={wrist => setPlacement({ ...placement, wrist })}/>
   <Choice label="Watch face position" value={placement.face} options={[{ value: 'top', label: 'Top of wrist' }, { value: 'inside', label: 'Inside of wrist' }]} onChange={face => setPlacement({ ...placement, face })}/>
   <Text style={s.title}>Setup notes (optional)</Text><TextInput accessibilityLabel="Setup notes" value={placement.notes} onChangeText={notes => setPlacement({ ...placement, notes })} multiline maxLength={1000} placeholder="Starting position, support, weight used…" style={[s.input, { minHeight: 100, textAlignVertical: 'top' }]}/>
   <Button title="Continue" disabled={!exercise} onPress={() => setStep('prepare')}/>
  </>}
  {step === 'prepare' && <>
   <Card><Text style={s.title}>{wearable.phase === 'connected' ? '● Watch connected' : 'Watch not connected'}</Text><Text style={s.small}>{wearable.message}</Text>{wearable.phase !== 'connected' && <Button title="Connect watch" secondary onPress={() => router.push('/settings')}/>}</Card>
   <Card><Text style={s.title}>Get into position</Text><Text style={s.text}>1. Watch on your {placement.wrist} wrist, face {placement.face === 'top' ? 'on top' : 'inside'}, snug.</Text><Text style={s.text}>2. {exerciseId === 'bicep-curls' ? 'Start with your arm relaxed at your side, palm forward.' : 'Use the starting position prescribed for this exercise.'}</Text><Text style={s.text}>3. Hold still for about 2 seconds before your first repetition. Return to the same starting position after each repetition.</Text>{!!placement.notes && <Text style={s.small}>{placement.notes}</Text>}</Card>
   <Card><Text style={s.title}>Before you exercise</Text><Text style={s.text}>{survey ? `Pain rating recorded: ${survey.pain} / 10` : 'Please complete the pre-exercise survey, including your pain rating.'}</Text><Button title={survey ? 'Update pre-exercise survey' : 'Complete pre-exercise survey'} secondary onPress={() => router.push({ pathname: '/survey', params: { phase: 'before', exerciseId, returnTo: 'baseline' } })}/></Card>
   <Button title="Start baseline recording" disabled={wearable.phase !== 'connected' || !survey || busy} onPress={() => void run(start)}/>
  </>}
  {step === 'record' && <>
   <View style={s.circle}><Text style={{ fontSize: 48, color: colors.blue, fontWeight: '600' }}>{recording.phase === 'starting' ? '…' : analysis ? '✓' : recording.phase === 'interrupted' ? '!' : finishing ? 'Ⅱ' : elapsed < 2 ? Math.ceil(2 - elapsed) : liveReps}</Text><Text style={s.small}>{analysis ? 'Finished' : elapsed < 2 ? 'seconds' : 'reps detected'}</Text></View>
   <Text style={[s.title, { textAlign: 'center', fontSize: 23 }]}>{analysis ? 'Recording complete' : recording.phase === 'interrupted' ? 'Recording interrupted' : recording.phase === 'starting' ? 'Getting your watch ready' : finishing ? 'Return to your starting position and hold' : recording.phase === 'ended' ? 'Recording needs another try' : elapsed < 2 ? 'Hold still' : 'Recording'}</Text>
   <Text style={[s.text, { textAlign: 'center' }]}>{analysis ? `We found ${analysis.reps.length} complete repetitions. Review which ones to keep.` : finishing ? 'Hold briefly while we finish capturing your last movement.' : elapsed < 2 ? 'Keep your wrist and arm still.' : 'Repeat the exercise at a comfortable pace. Return to your starting position after each repetition.'}</Text>
   <Card><View style={s.row}><Text style={s.text}>{Math.floor(elapsed / 60)}:{String(Math.floor(elapsed % 60)).padStart(2, '0')}</Text><Text style={s.small}>{recording.running ? '● Recording' : analysis ? '● Finished' : 'Not recording'}</Text></View><Text style={s.small}>The count is provisional until the complete recording is checked.</Text></Card>
   {analysis?.warnings.map(w => <Hint key={w}>{w}</Hint>)}
   {recording.running ? <><Button title={finishing ? 'Finishing recording…' : 'Stop recording'} danger busy={finishing || busy} disabled={recording.phase === 'starting' || recording.phase === 'stopping'} onPress={() => void finish()}/><Button title="Cancel recording" secondary onPress={() => { recorder.interrupt('Recording cancelled. Nothing was saved.'); clearTimeout(finishTimer.current); setFinishing(false); }}/></> : <>
   {analysis && analysis.reps.filter(r => r.eligible).length >= 3 && <Button title="Review repetitions" onPress={() => { setError(''); setStep('review'); }}/>}
   <Button title={wearable.phase === 'connected' ? 'Record again' : 'Reconnect and start over'} secondary onPress={() => { reset(); if (wearable.phase !== 'connected')
                router.push('/settings'); }}/><Button title="Check watch placement" secondary onPress={() => { reset(); setStep('details'); }}/>
   </>}
  </>}
  {step === 'review' && analysis && <>
   <Text style={s.text}>Reference recording for {exercise?.name} ({sideLabel(placement.side).toLowerCase()}). Keep the repetitions that represent your reference movement. Saving activates this baseline for live guidance.</Text>
   <Card><Text style={s.title}>{analysis.reps.length} detected · {ids.length} kept · 3+ needed</Text></Card>
   {analysis.reps.map(rep => <Pressable key={rep.id} accessibilityRole="checkbox" accessibilityState={{ checked: ids.includes(rep.id), disabled: !rep.eligible }} disabled={!rep.eligible || busy} onPress={() => setIds(current => current.includes(rep.id) ? current.filter(i => i !== rep.id) : [...current, rep.id].sort((a, b) => a - b))}><Card><View style={s.row}><Text style={s.title}>{ids.includes(rep.id) ? '☑' : '☐'} Rep {rep.id}</Text><Text style={{ color: colors.blue }}>{rep.eligible ? (ids.includes(rep.id) ? 'Exclude' : 'Include') : 'Auto-excluded'}</Text></View><Text style={s.small}>{rep.duration.toFixed(1)} s · {rep.start.toFixed(1)}–{rep.end.toFixed(1)} s</Text>{rep.reason && <Text style={s.small}>{rep.reason}</Text>}</Card></Pressable>)}
   {analysis.unconfirmedFinal && <Hint>An incomplete final movement was automatically excluded because its return was not confirmed.</Hint>}
   <Button title={technical ? 'Hide technical details' : 'Technical details'} secondary onPress={() => setTechnical(!technical)}/>
   {technical && <><Hint>Experimental · for care-team review. Watch-motion estimates are not anatomical joint angles or a diagnosis.</Hint><Card><Text style={s.title}>Recording</Text><Text style={s.text}>Processing rate: {analysis.rate} Hz</Text><Text style={s.text}>Still start: {analysis.stillness ? 'Passed · gyro bias removed' : 'Failed · no bias correction'}</Text><Text style={s.small}>Duration is used to check repetition boundaries, not as one of the nine features.</Text></Card>{reference ? <Card>{FEATURES.map(key => <View key={key} style={{ paddingVertical: 7, borderBottomWidth: 1, borderBottomColor: colors.line }}><Text style={s.small}>{LABELS[key]}</Text><Text style={s.text}>{reference!.stats[key].mean.toFixed(3)} ± {reference!.stats[key].sd.toFixed(3)}</Text></View>)}</Card> : <Hint>Keep at least three usable repetitions to calculate statistics.</Hint>}<Hint>Future comparisons use each feature’s mean ±3 sample standard deviations. These limits stay fixed; there is no overall “incorrect rep” score.</Hint></>}
   <Button title="Save and activate baseline" disabled={!reference} busy={busy} onPress={() => void run(async () => { const snap = recorder.getSnapshot(); const id = await saveBaseline({ exerciseId, placement, analysis, ids, frames: recorder.getFrames(), surveyId: survey?.id ?? '', deviceName: wearable.selectedName ?? 'HomeStretch wearable', protocolSessionId: snap.sessionId, complete: snap.complete === true }); setSavedId(id); setStep('saved'); })}/>
   <Button title="Record again" secondary disabled={busy} onPress={reset}/>
   <Text style={[s.small, { textAlign: 'center' }]}>Saving automatically approves and activates this baseline on this device. This is temporary prototype approval, not clinician review.</Text>
  </>}
  {step === 'saved' && <><View style={[s.circle, { borderColor: '#D9AE50' }]}><Text style={{ fontSize: 50 }}>✓</Text></View><Text style={[s.title, { textAlign: 'center', fontSize: 24 }]}>Recording saved</Text><Badge active/><Card><Text style={s.text}>✓ {ids.length} repetitions kept</Text><Text style={s.text}>✓ Saved on this device</Text><Text style={s.text}>✓ Automatically approved for this prototype</Text><Text style={s.text}>✓ Active for live rep comparisons</Text></Card><Hint>Your baseline is ready for live guidance. Previous recordings are retained; this reference replaces the previous one for the same side and watch placement.</Hint><Button title="Exercise with this baseline" onPress={() => router.replace({pathname:"/exercise-detail",params:{id:exerciseId,baselineId:savedId}})}/><Button title="View saved recording" onPress={() => router.replace({ pathname: '/baselines', params: { recordingId: savedId } })}/><Button title="Back to exercises" secondary onPress={() => router.replace('/exercise')}/></>}
 </Page>;
}
