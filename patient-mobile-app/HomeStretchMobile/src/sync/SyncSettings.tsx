import React,{useEffect,useState} from 'react';
import {Text,TextInput,View} from 'react-native';
import {linkUnassignedSessions,savePatientProfile,useCatalog} from '../baseline/store';
import {Button,Card,Hint,s} from '../baseline/ui';
import {syncSessions} from './upload';
export default function SyncSettings(){
 const catalog=useCatalog();const [name,setName]=useState(catalog.data.patientProfile?.name??''),[id,setId]=useState(catalog.data.patientProfile?.id??'');
 useEffect(()=>{if(catalog.ready){setName(catalog.data.patientProfile?.name??'');setId(catalog.data.patientProfile?.id??'');}},[catalog.ready]);
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 const uploads=catalog.data.sessionUploads??[],pending=uploads.filter(s=>s.status==='pending'),unassigned=pending.filter(s=>!s.document.patient);
 async function run(action:()=>Promise<unknown>){if(busy)return;setBusy(true);setError('');try{await action();}catch(e){setError(e instanceof Error?e.message:'Could not save this change.');}finally{setBusy(false);}}
 return <View style={{gap:12,marginVertical:16}}><Text style={s.title}>Patient &amp; session sync</Text><Card>
 <Text style={s.small}>Use the same patient ID and name as the clinician dashboard. New sessions use this saved profile.</Text>
 <TextInput style={s.input} accessibilityLabel="Patient ID" placeholder="Patient ID" value={id} onChangeText={setId} maxLength={100} autoCapitalize="none"/>
 <TextInput style={s.input} accessibilityLabel="Patient name" placeholder="Patient name" value={name} onChangeText={setName} maxLength={100}/>
 <Button title="Save patient" disabled={!catalog.ready||!!catalog.error||!id.trim()||!name.trim()} busy={busy} onPress={()=>void run(()=>savePatientProfile({id,name}))}/>
 {catalog.data.patientProfile&&<Text style={s.small}>Saved patient: {catalog.data.patientProfile.name} ({catalog.data.patientProfile.id})</Text>}
 </Card>
 <Card><Text style={s.title}>{pending.length} sessions waiting to sync</Text><Text style={s.small}>{uploads.filter(s=>s.status==='synced').length} synced · raw sensor files stay on this phone</Text>
 {unassigned.length>0&&<><Text style={s.small}>{unassigned.length} sessions have no patient assigned.</Text><Button title={`Assign unlinked sessions to ${catalog.data.patientProfile?.name??'saved patient'}`} secondary disabled={!catalog.data.patientProfile} busy={busy} onPress={()=>void run(async()=>{await linkUnassignedSessions();await syncSessions();})}/></>}
 <Button title="Retry uploads" secondary busy={busy} disabled={!pending.some(s=>s.document.patient)} onPress={()=>void run(syncSessions)}/>
 {pending.slice(-5).reverse().map(session=><View key={session.document.session_id}><Text style={s.small}>{session.document.exercise.name} · {session.document.num_reps} reps · {session.document.patient_name??'No patient'}</Text>{session.lastError&&<Text selectable style={s.small}>{session.lastError}</Text>}</View>)}
 </Card>{(error||catalog.error)&&<Hint error>{error||catalog.error}</Hint>}</View>;
}
