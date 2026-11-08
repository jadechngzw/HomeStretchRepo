import { activeBaselines, isActive } from '../baseline/activation';
import React, { useState } from 'react';
import { Text, TextInput, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Page, Card, Button, Hint, Badge, s, colors } from '../baseline/ui';
import { exercises, updateNotes, useCatalog } from '../baseline/store';
import { sideLabel } from '../baseline/types';
import { FEATURES, LABELS } from '../baseline/analysis';
export default function Baselines() {
    const params = useLocalSearchParams<{
        recordingId?: string;
    }>(), catalog = useCatalog();
    const [selected, setSelected] = useState(params.recordingId ?? ''), [technical, setTechnical] = useState(false), [editing, setEditing] = useState(false), [notes, setNotes] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
    const all = exercises(catalog.data), record = catalog.data.baselines.find(b => b.id === selected), exercise = all.find(e => e.id === record?.exerciseId);
    const date = (value: string) => new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    if (!catalog.ready)
        return <Page title="Exercise Baselines"><Text>Loading saved recordings…</Text></Page>;
    return <Page title={record ? (exercise?.name ?? 'Saved recording') : 'Exercise Baselines'} onBack={() => { if (selected) {
        setSelected('');
        setTechnical(false);
        setEditing(false);
    }
    else
        router.back(); }}>
  {(catalog.error || error) && <Hint error>{catalog.error || error}</Hint>}
  {!record ? <>
   <Button title="+ Add exercise / Set up baseline" secondary disabled={!!catalog.error} onPress={() => router.push('/baseline-setup')}/>
   {!catalog.data.baselines.length ? <><View style={s.circle}><Text style={{ fontSize: 48, color: colors.blue }}>☷</Text></View><Text style={[s.title, { textAlign: 'center', fontSize: 24 }]}>No baselines yet</Text><Text style={[s.text, { textAlign: 'center' }]}>Record a reference movement for each exercise. You’ll need your HomeStretch watch.</Text><Button title="Set up your first baseline" disabled={!!catalog.error} onPress={() => router.push('/baseline-setup')}/></> :
                all.map(e => { const recordings = catalog.data.baselines.filter(b => b.exerciseId === e.id).slice().reverse(); return <Card key={e.id}><Text style={s.title}>{e.name}</Text><Badge active={activeBaselines(catalog.data,e.id).length>0} pending={recordings.some(b=>b.status==="awaiting-review")}/>{recordings.map(b => <View key={b.id} style={{ gap: 7, paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.line }}><Text style={s.text}>{sideLabel(b.placement.side)} · watch on {b.placement.wrist} wrist</Text><Text style={s.small}>{date(b.recordedAt)} · {b.reference.acceptedIds.length} reps kept · {isActive(catalog.data,b)?"active":"previous recording"}</Text>{!!b.placement.notes && <Text style={s.small}>{b.placement.notes}</Text>}<Button title="View recording" secondary onPress={() => { setSelected(b.id); setError(''); setTechnical(false); }}/></View>)}<Button title={recordings.length ? 'Record new baseline' : 'Set up baseline'} onPress={() => router.push({ pathname: '/baseline-setup', params: { exerciseId: e.id, ...(recordings.length ? { replaceId: recordings[0].id } : {}) } })}/></Card>; })}
   <Hint>Baselines are saved on this device and approved automatically for prototype live guidance. The latest baseline for each side and watch placement is active.</Hint>
  </> : <>
   <Card><View style={s.row}><Text style={[s.title, { flex: 1 }]}>Your reference recording</Text><Badge active={isActive(catalog.data,record)} pending={record.status==="awaiting-review"} saved={record.status==="approved"}/></View><Text style={s.text}>{sideLabel(record.placement.side)}</Text><Text style={s.text}>Watch: {record.placement.wrist} wrist, face {record.placement.face === 'top' ? 'on top' : 'inside'}</Text><Text style={s.text}>Repetitions kept: {record.reference.acceptedIds.length}</Text><Text style={s.text}>Recorded: {date(record.recordedAt)}</Text><Text style={s.small}>Device: {record.deviceName}</Text><Text style={s.small}>Pain before recording: {catalog.data.surveys.find(v => v.id === record.surveyId)?.pain ?? 'Not available'} / 10</Text></Card>
   <Card><Text style={s.title}>Setup notes</Text>{editing ? <><TextInput style={[s.input, { minHeight: 100 }]} accessibilityLabel="Edit setup notes" multiline maxLength={1000} value={notes} onChangeText={setNotes}/><Button title="Save notes" busy={busy} onPress={() => { setBusy(true); setError(''); void updateNotes(record.id, notes).then(() => setEditing(false)).catch(e => setError(e.message)).finally(() => setBusy(false)); }}/><Button title="Cancel" secondary disabled={busy} onPress={() => setEditing(false)}/></> : <><Text style={s.text}>{record.placement.notes || 'No setup notes added.'}</Text><Button title="Edit notes" secondary onPress={() => { setNotes(record.placement.notes); setEditing(true); }}/></>}</Card>
   <Hint>{isActive(catalog.data,record)?"This baseline is active for live guidance. Approval is automatic for this prototype, not a clinician review.":"This is a previous or incompatible reference. The latest compatible baseline for the same side and watch placement is used for live guidance."} New recordings are saved separately; previous recordings are retained.</Hint>
   <Button title="Exercise with live guidance" onPress={()=>router.push({pathname:"/exercise-detail",params:{id:record.exerciseId,baselineId:record.id}})}/><Button title="Record new baseline" onPress={() => router.push({ pathname: '/baseline-setup', params: { exerciseId: record.exerciseId, replaceId: record.id } })}/>
   <Button title={technical ? 'Hide technical details' : 'Technical details'} secondary onPress={() => setTechnical(!technical)}/>
   {technical && <><Hint>Experimental · for care-team review. A difference from baseline does not establish incorrect or unsafe movement.</Hint><Card><Text style={s.text}>Processing: {record.analysis.rate} Hz</Text><Text style={s.text}>Stillness: {record.analysis.stillness ? 'Passed · gyro bias removed' : 'Failed · no bias correction'}</Text><Text style={s.small}>Version: {record.analysis.version}</Text><Text style={s.small}>Kept repetitions: {record.reference.acceptedIds.join(', ')}</Text>{FEATURES.map(key => <View key={key} style={{ paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.line }}><Text style={s.small}>{LABELS[key]}</Text><Text style={s.text}>{record.reference.stats[key].mean.toFixed(3)} ± {record.reference.stats[key].sd.toFixed(3)}</Text><Text style={s.small}>Reference band: {record.reference.stats[key].lower.toFixed(3)}–{record.reference.stats[key].upper.toFixed(3)}</Text></View>)}</Card>{FEATURES.some(key => record.reference.stats[key].sd < 1e-10) && <Hint>Some features have almost no baseline variation. These limits need review before use.</Hint>}{record.analysis.warnings.map(w => <Hint key={w}>{w}</Hint>)}</>}
  </>}
 </Page>;
}
