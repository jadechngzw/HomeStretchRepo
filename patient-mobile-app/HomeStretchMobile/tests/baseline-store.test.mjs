import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
const require=createRequire(import.meta.url),ts=require('typescript');
function harness(shared={files:new Map(),settings:{},fail:false}){
 const modules=new Map();
 function load(name){if(modules.has(name))return modules.get(name);const source=readFileSync(new URL(`../src/baseline/${name}.ts`,import.meta.url),'utf8'),js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;const exports={};
 const mockRequire=id=>id==='react'?{useSyncExternalStore:()=>{}}:id==='react-native'?{Platform:{OS:'ios'},Settings:{get:k=>shared.settings[k],set:patch=>Object.assign(shared.settings,patch)}}:id==='expo-file-system/legacy'?{documentDirectory:'test/',makeDirectoryAsync:async()=>{},readAsStringAsync:async path=>{if(!shared.files.has(path))throw new Error('Missing file');return shared.files.get(path);},writeAsStringAsync:async(path,text)=>{if(shared.fail)throw new Error('Storage full');shared.files.set(path,text);}}:load(id.startsWith('../')?id:id.replace('./',''));
 new Function('require','exports',js)(mockRequire,exports);modules.set(name,exports);return exports;
 }
 return {store:load('store'),analysis:load('analysis'),shared};
}
const fixture=JSON.parse(readFileSync(new URL('./fixtures/baseline-synthetic.json',import.meta.url),'utf8'));
test('save, restart, and replacement keep both automatically approved records and raw sensor data',async()=>{
 const h=harness(),s=h.store;const id=await s.addExercise('  Test Exercise  ');assert.equal(await s.addExercise('test exercise'),id);
 const surveyId=await s.saveSurvey({phase:'before',exerciseId:id,pain:0,symptoms:'',regions:[],notes:''});
 const analysis=h.analysis.analyze(fixture.frames),input={exerciseId:id,placement:{side:'right',wrist:'right',face:'top',notes:'Test notes'},analysis,ids:[1,2,3],frames:fixture.frames,surveyId,deviceName:'Test watch',protocolSessionId:123,complete:true};
 const first=await s.saveBaseline(input),second=await s.saveBaseline(input);assert.notEqual(first,second);
 const records=s.getCatalog().data.baselines;assert.equal(records.length,2);assert.ok(records.every(b=>b.status==='approved' && b.approvalMode==='automatic-prototype'));assert.ok(h.shared.files.has('test/exercise-baselines/'+records[0].rawFile));
 const restarted=harness(h.shared);await restarted.store.addExercise('Another exercise');assert.equal(restarted.store.getCatalog().data.baselines.length,2);assert.equal(restarted.store.getCatalog().data.surveys[0].pain,0);
 await s.updateNotes(first,'Revised');assert.equal(s.getCatalog().data.baselines[0].placement.notes,'Revised');assert.equal(s.getCatalog().data.baselines[1].placement.notes,'Test notes');
});
test('failed writes preserve the committed catalog and remain retryable',async()=>{const h=harness();await h.store.addExercise('Saved');const pointer=h.shared.settings.HomeStretchBaselineCatalogV1;h.shared.fail=true;await assert.rejects(h.store.addExercise('Unsaved'),/Storage full/);assert.equal(h.shared.settings.HomeStretchBaselineCatalogV1,pointer);assert.equal(h.store.getCatalog().data.customExercises.length,1);h.shared.fail=false;await h.store.addExercise('Retry');assert.equal(h.store.getCatalog().data.customExercises.length,2);});
test('unanswered pain and incomplete recordings cannot be saved',async()=>{const h=harness();await assert.rejects(h.store.saveSurvey({phase:'before',exerciseId:'bicep-curls',pain:null,symptoms:'',regions:[],notes:''}));await assert.rejects(h.store.saveBaseline({complete:false}),/incomplete/);});

test('existing pending baselines are auto-approved once and latest matching placement wins',async()=>{
 const h=harness(),s=h.store;
 const surveyId=await s.saveSurvey({phase:'before',exerciseId:'bicep-curls',pain:2,symptoms:'',regions:[],notes:''});
 const analysis=h.analysis.analyze(fixture.frames),input={exerciseId:'bicep-curls',placement:{side:'right',wrist:'right',face:'top',notes:''},analysis,ids:[1,2,3],frames:fixture.frames,surveyId,deviceName:'Test',protocolSessionId:123,complete:true};
 await s.saveBaseline(input);await s.saveBaseline(input);
 const pointer=h.shared.settings.HomeStretchBaselineCatalogV1,path='test/exercise-baselines/'+pointer;
 const old=JSON.parse(h.shared.files.get(path));old.baselines.forEach(b=>{b.status='awaiting-review';delete b.approvalMode;});h.shared.files.set(path,JSON.stringify(old));
 const restarted=harness(h.shared);await restarted.store.addExercise('Wake loading');
 assert.ok(restarted.store.getCatalog().data.baselines.every(b=>b.status==='approved'));
 assert.notEqual(h.shared.settings.HomeStretchBaselineCatalogV1,pointer);
});

test('sessions persist through restart; post-survey updates cannot be acknowledged by an older upload',async()=>{
 const h=harness(),s=h.store;await s.savePatientProfile({id:'test-1',name:'Test Patient'});
 const doc={schema_version:2,session_id:'session-test',exercise:{id:'bicep-curls',name:'Bicep Curls'},started_at:'2026-10-30T12:00:00Z',ended_at:'2026-10-30T12:01:00Z',num_reps:0,num_typical:0,num_atypical:0,num_unassessed:0,rep_assessments:[],patient:null,patient_id:null,patient_name:null,pain:{before:null,after:null},raw_file:null};
 await s.saveSession(doc);await s.saveSession(doc);assert.equal(s.getCatalog().data.sessionUploads.length,1);
 await s.linkUnassignedSessions();const before=s.getCatalog().data.sessionUploads[0].document;assert.equal(before.patient.id,'test-1');
 await s.markUpload(doc.session_id,'permission-denied',before);assert.equal(s.getCatalog().data.sessionUploads[0].status,'pending');
 const id=await s.saveSurvey({phase:'after',exerciseId:'bicep-curls',pain:4,symptoms:'',regions:[],notes:''});await s.attachPostSurvey(doc.session_id,id);
 await s.markUpload(doc.session_id,null,before);assert.equal(s.getCatalog().data.sessionUploads[0].status,'pending');
 const restarted=harness(h.shared);await restarted.store.addExercise('Load');const row=restarted.store.getCatalog().data.sessionUploads[0];assert.equal(row.document.pain.after.pain,4);assert.equal(row.document.pain_level,4);
 await restarted.store.markUpload(doc.session_id,null,row.document);assert.equal(restarted.store.getCatalog().data.sessionUploads[0].status,'synced');
});

const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const dailyInput = (phase='before') => ({phase,exerciseId:'bicep-curls',pain:0,symptoms:'Staying the Same',regions:[],notes:'Original answers'});
test('daily surveys are shared across exercises, deduplicated and retained after restart', async()=>{
 const h=harness(),s=h.store;
 const ids=await Promise.all([s.saveDailySurvey(dailyInput(),today(),null),s.saveDailySurvey({...dailyInput(),exerciseId:'shoulder-rolls'},today(),null)]);
 assert.equal(ids[0],ids[1]);assert.equal(s.getCatalog().data.surveys.length,1);
 const saved=s.getCatalog().data.surveys[0];assert.equal(saved.exerciseId,null);assert.equal(saved.pain,0);
 const restarted=harness(h.shared);assert.equal(await restarted.store.saveDailySurvey(dailyInput(),today(),null),saved.id);
 await s.savePatientProfile({id:'another',name:'Another Patient'});
 await s.saveDailySurvey(dailyInput(),today(),'another');assert.equal(s.getCatalog().data.surveys.length,2);
});
test('daily survey rejects stale day or patient, missing pre-survey, and retries failed storage',async()=>{
 const h=harness(),s=h.store;
 await assert.rejects(s.saveDailySurvey(dailyInput(), '2000-01-01',null),/changed/);
 await assert.rejects(s.saveDailySurvey(dailyInput(),today(),'wrong'),/changed/);
 await assert.rejects(s.saveDailySurvey(dailyInput('after'),today(),null),/pre-exercise/);
 h.shared.fail=true;await assert.rejects(s.saveDailySurvey(dailyInput(),today(),null),/Storage full/);
 assert.equal(s.getCatalog().data.surveys.length,0);h.shared.fail=false;
 await s.saveDailySurvey(dailyInput(),today(),null);assert.equal(s.getCatalog().data.surveys.length,1);
});
test('daily post-survey updates all of this patient’s exercises only for today',async()=>{
 const h=harness(),s=h.store;await s.savePatientProfile({id:'p',name:'Patient'});
 await s.saveDailySurvey(dailyInput(),today(),'p');
 const doc={schema_version:2,exercise:{id:'bicep-curls',name:'Bicep Curls'},started_at:new Date().toISOString(),ended_at:new Date().toISOString(),num_reps:0,num_typical:0,num_atypical:0,num_unassessed:0,rep_assessments:[],patient:{id:'p',name:'Patient'},patient_id:'p',patient_name:'Patient',pain:{before:null,after:null},raw_file:null};
 await s.saveSession({...doc,session_id:'first'});
 await s.saveSession({...doc,session_id:'second',exercise:{id:'shoulder-rolls',name:'Shoulder Rolls'}});
 await s.saveSession({...doc,session_id:'other-patient',patient_id:'other'});
 await s.saveSession({...doc,session_id:'yesterday',ended_at:'2000-01-01T12:00:00Z'});
 const id=await s.saveDailySurvey({...dailyInput('after'),pain:4},today(),'p');
 const rows=s.getCatalog().data.sessionUploads;
 assert.equal(rows[0].document.pain.after.id,id);assert.equal(rows[1].document.pain.after.id,id);
 assert.equal(rows[2].document.pain.after,null);assert.equal(rows[3].document.pain.after,null);
 assert.equal(await s.saveDailySurvey(dailyInput('after'),today(),'p'),id);
});
test('daily lookup resets at local midnight and ignores older exercise-specific surveys',()=>{
 const source=readFileSync(new URL('../src/baseline/dailySurveys.ts',import.meta.url),'utf8');const exports={};
 new Function('exports',ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText)(exports);
 const day=exports.localDay(new Date(2026,10,7,23,59));assert.equal(day,'2026-11-07');
 const data={surveys:[{id:'old',phase:'before',recordedAt:new Date().toISOString()},{id:'daily',phase:'before',day,patientId:null}]};
 assert.equal(exports.dailySurvey(data,'before',day).id,'daily');
 assert.equal(exports.dailySurvey(data,'before',exports.localDay(new Date(2026,10,8,0,0))),undefined);
});

test('switching patient accounts isolates saved surveys and restores the right patient on return',async()=>{
 const h=harness(),s=h.store;
 await s.openPatientAccount({id:'a',name:'Patient A'});
 await s.saveDailySurvey(dailyInput(),today(),'a');
 await s.openPatientAccount({id:'b',name:'Patient B'});
 assert.equal(s.getCatalog().data.surveys.length,0);
 await s.saveDailySurvey(dailyInput(),today(),'b');
 await s.openPatientAccount(null);assert.equal(s.getCatalog().data.surveys.length,0);
 await s.openPatientAccount({id:'a',name:'Patient A'});
 assert.equal(s.getCatalog().data.surveys.length,1);assert.equal(s.getCatalog().data.surveys[0].patientId,'a');
});


test('a late save from the previous account cannot enter the new patient catalog',async()=>{
 const h=harness(),s=h.store;
 await s.openPatientAccount({id:'b',name:'Patient B'});
 const doc={schema_version:3,session_id:'old-a',exercise:{id:'x',name:'X'},started_at:'2026-11-07T12:00:00Z',ended_at:'2026-11-07T12:01:00Z',patient_id:'a',num_reps:0,num_typical:0,num_atypical:0,num_unassessed:0,rep_assessments:[]};
 await assert.rejects(s.saveSession(doc),/account changed/);
 assert.equal(s.getCatalog().data.sessionUploads,undefined);
});
