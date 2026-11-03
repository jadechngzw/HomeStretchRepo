import { useEffect } from 'react';
import { AppState } from 'react-native';
import { useCatalog } from '../baseline/store';
import { syncSessions } from './upload';
export function useSessionSync(){
 const {ready}=useCatalog();
 useEffect(()=>{
  if(!ready)return;
  const run=()=>{if(AppState.currentState==='active'||AppState.currentState===null)void syncSessions().catch(()=>{});};
  run();const timer=setInterval(run,60000);const listener=AppState.addEventListener('change',state=>{if(state==='active')run();});
  return()=>{clearInterval(timer);listener.remove();};
 },[ready]);
}
