import { validateSession } from '../sync/schema';
import type { PatientProfile, SessionDocument } from '../sync/schema';
import { useSyncExternalStore } from 'react';
import { Platform, Settings } from 'react-native';
import * as FS from 'expo-file-system/legacy';
import { autoApprove } from './activation';
import { buildReference } from './analysis';
import type { Analysis } from './analysis';
import type { Sample } from '../wearable/protocol';
import { DEFAULT_EXERCISES, uid } from './types';
import type { Baseline, Catalog, Placement, Survey } from './types';
const pointerKey = 'HomeStretchBaselineCatalogV1';
const folder = FS.documentDirectory ? `${FS.documentDirectory}exercise-baselines/` : '';
const empty = (): Catalog => ({ version: 1, customExercises: [], baselines: [], surveys: [] });
let snapshot: {
    ready: boolean;
    error: string | null;
    data: Catalog;
} = { ready: false, error: null, data: empty() };
const listeners = new Set<() => void>();
const emit = () => listeners.forEach(fn => fn());
const subscribe = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn); }; };
function getPointer(): string | null { if (Platform.OS === 'web')
    return globalThis.localStorage.getItem(pointerKey); if (Platform.OS === 'ios')
    return Settings.get(pointerKey) ?? null; throw new Error('Baseline storage currently supports iPhone and web preview.'); }
function setPointer(value: string) { if (Platform.OS === 'web')
    globalThis.localStorage.setItem(pointerKey, value);
else
    Settings.set({ [pointerKey]: value }); }
async function read(name: string) { return Platform.OS === 'web' ? globalThis.localStorage.getItem(name) : FS.readAsStringAsync(folder + name); }
async function write(name: string, value: string) { if (Platform.OS === 'web')
    globalThis.localStorage.setItem(name, value);
else {
    if (!folder)
        throw new Error('Device storage is unavailable.');
    await FS.makeDirectoryAsync(folder, { intermediates: true });
    await FS.writeAsStringAsync(folder + name, value);
} }
// Immutable catalog revisions: update the pointer only after the new file is written.
// Interrupted saves retain the previous catalog. Raw recordings are separate files.
const loading = (async () => { try {
    const pointer = getPointer();
    if (pointer) {
        const content = await read(pointer);
        if (!content)
            throw new Error('Saved baseline catalog is missing.');
        let data = JSON.parse(content) as Catalog;
        if (data.version !== 1 || !Array.isArray(data.baselines) || !Array.isArray(data.surveys) || !Array.isArray(data.customExercises))
            throw new Error('Saved baseline catalog could not be read.');
        const upgraded = autoApprove(data);
        if (upgraded.baselines.some((b, i) => b !== data.baselines[i])) {
            const name = `catalog-${uid()}.json`;
            await write(name, JSON.stringify(upgraded));
            setPointer(name);
            data = upgraded;
        }
        snapshot = { ready: true, error: null, data };
    }
    else
        snapshot = { ready: true, error: null, data: empty() };
}
catch (e) {
    snapshot = { ...snapshot, ready: true, error: e instanceof Error ? e.message : 'Could not read saved baselines.' };
} emit(); })();
let queue: Promise<unknown> = Promise.resolve();
function change<T>(fn: (data: Catalog) => Promise<{
    data: Catalog;
    result: T;
}>): Promise<T> {
    const task = queue.then(async () => { await loading; if (snapshot.error)
        throw new Error(snapshot.error); const { data, result } = await fn(snapshot.data); const name = `catalog-${uid()}.json`; await write(name, JSON.stringify(data)); setPointer(name); snapshot = { ready: true, error: null, data }; emit(); return result; });
    queue = task.catch(() => { });
    return task;
}
export function useCatalog() { return useSyncExternalStore(subscribe, () => snapshot, () => snapshot); }
export const exercises = (data: Catalog) => [...DEFAULT_EXERCISES, ...data.customExercises];
export const getCatalog = () => snapshot;
export async function addExercise(name: string) { return change(async (data) => { const cleaned = name.trim().replace(/\s+/g, ' '); if (!cleaned || cleaned.length > 80)
    throw new Error('Enter an exercise name of 1–80 characters.'); const existing = exercises(data).find(e => e.name.toLocaleLowerCase() === cleaned.toLocaleLowerCase()); if (existing)
    return { data, result: existing.id }; const exercise = { id: `custom-${uid()}`, name: cleaned, sets: 1, reps: 10, duration: 'Your pace', instructions: 'Follow your prescribed routine', custom: true }; return { data: { ...data, customExercises: [...data.customExercises, exercise] }, result: exercise.id }; }); }
export async function saveSurvey(survey: Omit<Survey, 'id' | 'recordedAt'>) { return change(async (data) => { if (!Number.isInteger(survey.pain) || survey.pain < 0 || survey.pain > 10)
    throw new Error('Select a pain rating from 0 to 10.'); const record = { ...survey, id: uid(), recordedAt: new Date().toISOString() }; return { data: { ...data, surveys: [...data.surveys, record] }, result: record.id }; }); }
export async function saveBaseline(input: {
    exerciseId: string;
    placement: Placement;
    analysis: Analysis;
    ids: number[];
    frames: Sample[];
    surveyId: string;
    deviceName: string;
    protocolSessionId: number;
    complete: boolean;
}) {
    return change(async (data) => {
        if (!input.complete)
            throw new Error('An interrupted or incomplete recording cannot be saved as a baseline.');
        if (!exercises(data).some(e => e.id === input.exerciseId))
            throw new Error('Exercise was not found.');
        const survey = data.surveys.find(s => s.id === input.surveyId && s.phase === 'before' && s.exerciseId === input.exerciseId);
        if (!survey)
            throw new Error('Complete the pre-exercise survey before recording.');
        const reference = buildReference(input.analysis, input.ids), id = uid(), rawFile = `recording-${id}.json`;
        const record: Baseline = { id, exerciseId: input.exerciseId, placement: { ...input.placement }, recordedAt: new Date().toISOString(), status: 'approved', approvalMode: 'automatic-prototype', analysis: input.analysis, reference, surveyId: input.surveyId, rawFile, deviceName: input.deviceName, protocolSessionId: input.protocolSessionId };
        await write(rawFile, JSON.stringify({ version: 1, analysisVersion: input.analysis.version, frames: input.frames }));
        return { data: { ...data, baselines: [...data.baselines, record] }, result: id };
    });
}
export async function updateNotes(id: string, notes: string) { return change(async (data) => { if (!data.baselines.some(b => b.id === id))
    throw new Error('Recording not found.'); return { data: { ...data, baselines: data.baselines.map(b => b.id === id ? { ...b, placement: { ...b.placement, notes: notes.trim() } } : b) }, result: undefined }; }); }

export async function savePatientProfile(profile: PatientProfile) {
  return change(async data => {
    const patient = {id:profile.id.trim(),name:profile.name.trim().replace(/\s+/g,' ')};
    if(!patient.id||!patient.name||patient.id.length>100||patient.name.length>100)throw new Error('Enter a patient ID and name (up to 100 characters each).');
    return {data:{...data,patientProfile:patient},result:undefined};
  });
}
export async function saveSession(document: SessionDocument, frames?: Sample[]) {
  validateSession(document);
  return change(async data => {
    if((data.sessionUploads??[]).some(s=>s.document.session_id===document.session_id))return {data,result:document.session_id};
    let rawFile:string|null=null;
    if(frames?.length){rawFile=`session-${document.session_id}.json`;await write(rawFile,JSON.stringify({schema_version:2,session_id:document.session_id,frames}));}
    const entry={document:{...document,raw_file:rawFile},status:'pending' as const,attempts:0,lastError:null,syncedAt:null};
    return {data:{...data,sessionUploads:[...(data.sessionUploads??[]),entry]},result:document.session_id};
  });
}
export async function markUpload(id:string,error:string|null,expectedDocument:SessionDocument) {
  return change(async data=>({data:{...data,sessionUploads:(data.sessionUploads??[]).map(s=>s.document.session_id!==id||JSON.stringify(s.document)!==JSON.stringify(expectedDocument)?s:{...s,status:error?'pending' as const:'synced' as const,attempts:s.attempts+1,lastError:error,syncedAt:error?null:new Date().toISOString()})},result:undefined}));
}
export async function linkUnassignedSessions() {
  return change(async data=>{
    if(!data.patientProfile)throw new Error('Save a patient profile first.');
    return {data:{...data,sessionUploads:(data.sessionUploads??[]).map(s=>s.document.patient? s : {...s,status:'pending' as const,lastError:null,document:{...s.document,patient:{...data.patientProfile!},patient_id:data.patientProfile!.id,patient_name:data.patientProfile!.name}})},result:undefined};
  });
}
export async function attachPostSurvey(sessionId:string,surveyId:string) {
  return change(async data=>{
    const survey=data.surveys.find(s=>s.id===surveyId&&s.phase==='after');
    const session=data.sessionUploads?.find(s=>s.document.session_id===sessionId);
    if(!survey||!session||survey.exerciseId!==session.document.exercise.id)throw new Error('The survey does not match this session.');
    return {data:{...data,sessionUploads:(data.sessionUploads??[]).map(s=>s!==session?s:{...s,status:'pending' as const,lastError:null,document:{...s.document,pain:{...s.document.pain,after:survey},pain_level:survey.pain}})},result:undefined};
  });
}
