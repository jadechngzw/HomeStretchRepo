import React from 'react';
import {Text} from 'react-native';
import {router} from 'expo-router';
import {Page, Card, Button, s} from '../baseline/ui';
import {useWearable} from '../wearable/useWearable';
import {useDailySurveys} from '../baseline/useDailySurveys';
import {useCatalog} from '../baseline/store';
export default function AdherenceScreen(){
  const wearable=useWearable(),daily=useDailySurveys(),catalog=useCatalog();
  const pending=(catalog.data.sessionUploads??[]).filter(row=>row.status!=='synced');
  return <Page title="Before you start">
    <Card><Text style={s.title}>Watch connection</Text><Text style={s.text}>{wearable.phase==='connected'?'Connected':'Not connected'}</Text><Text style={s.small}>The app checks the watch’s recording status when you start a set.</Text><Button title="Watch settings" secondary onPress={()=>router.push('/settings')}/></Card>
    <Card><Text style={s.title}>Today’s surveys</Text><Text style={s.text}>Before exercise: {daily.before?'Complete':'Not completed'}</Text><Text style={s.text}>After exercise: {daily.after?'Complete':'Not completed'}</Text></Card>
    <Card><Text style={s.title}>Recordings</Text><Text style={s.text}>{pending.length?`${pending.length} waiting to upload`:'No uploads waiting'}</Text>{pending.some(row=>row.lastError)&&<Text style={s.small}>An upload failed. Your recording is saved on this phone and will retry.</Text>}</Card>
    <Button title="Go to exercises" onPress={()=>router.push('/exercise')}/>
  </Page>;
}
