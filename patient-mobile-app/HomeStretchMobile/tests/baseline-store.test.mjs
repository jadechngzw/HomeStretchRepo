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
