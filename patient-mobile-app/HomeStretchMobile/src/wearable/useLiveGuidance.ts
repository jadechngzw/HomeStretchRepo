import { useEffect, useState } from 'react';
import { session } from './useCurlSession';
import { paceCue } from '../baseline/liveGuidance';
export type GuidanceState = 'IDLE_PRE' | 'EXERCISING' | 'PAUSED' | 'IDLE_POST';
export interface GuidanceSnapshot { state: GuidanceState; message: string; pauseReason: string | null; atypicalFlags: string[]; repCount: number }
const initial = (): GuidanceSnapshot => ({state:'IDLE_PRE',message:'Ready to begin',pauseReason:null,atypicalFlags:[],repCount:0});
export function useLiveGuidance() {
  const [guidance,setGuidance]=useState< GuidanceSnapshot >(initial);
  useEffect(()=>{
    let sessionId=session.getSnapshot().sessionId;
    let durations:number[]=[];
    const unsubscribe=session.subscribe(()=>{
      const state=session.getSnapshot();
      if(state.sessionId!==sessionId){sessionId=state.sessionId;durations=[];setGuidance(initial());}
      if(state.phase==='ended'||state.phase==='interrupted')setGuidance(current=>({...current,state:'IDLE_POST',message:state.phase==='ended'?'Set complete':'Set interrupted',pauseReason:null}));
    });
    const unsubscribeRep=session.onRep(rep=>{
      durations.push(rep.durationSec);
      const pace=paceCue(durations);
      setGuidance({state:'EXERCISING',repCount:rep.count,atypicalFlags:[],pauseReason:null,
        message:pace==='slow'?'Try a slightly quicker, steady pace':pace==='fast'?'Slow down a little':rep.count>=10?'Target reached. End the set when you’re ready.':`Rep ${rep.count} of 10 — steady pace`});
    });
    return()=>{unsubscribe();unsubscribeRep();};
  },[]);
  return guidance;
}
