import type { Baseline, Exercise, Survey } from '../baseline/types';
import type { LiveResult } from '../baseline/liveGuidance';
export type PatientProfile = { id: string; name: string };
export type SessionDocument = {
  schema_version: 2 | 3; status?: 'completed' | 'interrupted'; local_date?: string; timezone?: string; analysis_version?: string | null; pre_survey_id?: string | null; source: 'homestretch-mobile'; session_id: string;
  patient: PatientProfile | null; patient_id: string | null; patient_name: string | null;
  exercise: {id:string;name:string}; started_at: string; ended_at: string; duration_sec:number;
  complete:boolean; protocol_session_id:number; num_reps:number; num_typical:number; num_atypical:number; num_unassessed:number;
  atypical_rep_ids:number[]; rep_durations:(number|null)[];
  rep_assessments:{rep:number;duration_sec:number|null;assessable:boolean;classification:'typical'|'atypical'|'unassessed';features_outside_baseline:string[];metrics?:Record<string,number>|null}[];
  pain:{before:Survey|null;after:Survey|null}; pre_exercise_pain:number|null; pain_level:number|null;
  baseline: {id:string;version:string;placement:Baseline['placement'];reference:Baseline['reference']} | null;
  guidance:{flags:string[]}; quality:{stillness_passed:boolean|null;unconfirmed_final:boolean;placement_warning:boolean};
  raw_file:string|null;
};
export type PendingSession = { document:SessionDocument; status:'pending'|'synced'; attempts:number; lastError:string|null; syncedAt:string|null };
export function makeSession(input:{id:string;patient:PatientProfile|null;exercise:Pick<Exercise,'id'|'name'>;startedAt:number;endedAt:number;protocolSessionId:number;survey?:Survey;baseline?:Baseline;result?:LiveResult;durations?:number[];manualReps?:number;complete:boolean}):SessionDocument {
  const reps=input.result?.reps ?? (input.manualReps!==undefined?Array.from({length:input.manualReps},()=>null):(input.durations??[])).map((duration,i)=>({id:i+1,duration,assessable:false,flags:[]}));
  const rows=reps.map(r=>({rep:r.id,duration_sec:r.duration,assessable:input.complete&&r.assessable,
    classification:(!input.complete||!r.assessable?'unassessed':r.flags.length?'atypical':'typical') as 'typical'|'atypical'|'unassessed',
    metrics:input.complete&&r.assessable&&'metrics' in r?(r.metrics??null):null,
    features_outside_baseline:input.complete&&r.assessable?[...r.flags]:[]}));
  const atypical=rows.filter(r=>r.classification==='atypical');
  const started = new Date(input.startedAt);
  const local_date = `${started.getFullYear()}-${String(started.getMonth()+1).padStart(2,'0')}-${String(started.getDate()).padStart(2,'0')}`;
  return {schema_version:3,status:input.complete?'completed':'interrupted',local_date,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,analysis_version:input.baseline?.reference.version??null,pre_survey_id:input.survey?.id??null,source:'homestretch-mobile',session_id:input.id,patient:input.patient?{...input.patient}:null,
    patient_id:input.patient?.id??null,patient_name:input.patient?.name??null,exercise:{...input.exercise},
    started_at:new Date(input.startedAt).toISOString(),ended_at:new Date(input.endedAt).toISOString(),duration_sec:Math.max(0,(input.endedAt-input.startedAt)/1000),
    protocol_session_id:input.protocolSessionId,complete:input.complete,num_reps:rows.length,num_typical:rows.filter(r=>r.classification==='typical').length,
    num_atypical:atypical.length,num_unassessed:rows.filter(r=>r.classification==='unassessed').length,atypical_rep_ids:atypical.map(r=>r.rep),
    rep_durations:rows.map(r=>r.duration_sec),rep_assessments:rows,
    pain:{before:input.survey?{...input.survey}:null,after:null},pre_exercise_pain:input.survey?.pain??null,pain_level:input.survey?.pain??null,
    baseline:input.baseline?{id:input.baseline.id,version:input.baseline.reference.version,placement:{...input.baseline.placement},reference:input.baseline.reference}:null,
    guidance:{flags:atypical.map(r=>`Rep ${r.rep}: ${r.features_outside_baseline.join(', ')}`)},
    quality:{stillness_passed:input.result?.stillness??null,unconfirmed_final:input.result?.unconfirmedFinal??false,placement_warning:input.result?.placementWarning??false},raw_file:null};
}
export function validateSession(value:SessionDocument) {
  if(![2,3].includes(value.schema_version)||!value.session_id||!value.exercise?.id||!value.exercise.name)throw new Error('Invalid session identity.');
  if(!Number.isFinite(Date.parse(value.started_at))||!Number.isFinite(Date.parse(value.ended_at)))throw new Error('Invalid session time.');
  if(value.num_reps!==value.rep_assessments.length||value.num_reps!==value.num_typical+value.num_atypical+value.num_unassessed)throw new Error('Session repetition totals do not match.');
  const walk=(v:unknown):void=>{if(v===undefined||typeof v==='number'&&!Number.isFinite(v))throw new Error('Session contains an invalid value.');if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')Object.values(v).forEach(walk);};walk(value);
}
export function uploadError(error:unknown):string {
  const e=error as {code?:string;message?:string};const code=e?.code??'unknown';
  const reason=code.includes('permission-denied')?'Firestore rejected access. Check Firebase sign-in and database rules.':code.includes('unauthenticated')?'Firebase requires sign-in.':code.includes('unavailable')||code==='timeout'?'The server could not be reached. The session remains saved for retry.':e?.message??'Upload failed.';
  return `${code}: ${reason}`;
}
