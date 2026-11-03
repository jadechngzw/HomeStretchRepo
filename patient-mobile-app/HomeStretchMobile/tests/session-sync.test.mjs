import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
const require=createRequire(import.meta.url),ts=require('typescript');
function load(name,dependencies={}){const source=readFileSync(new URL(`../src/sync/${name}.ts`,import.meta.url),'utf8');const exports={};new Function('require','exports',ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText)(id=>dependencies[id],exports);return exports;}
const schema=load('schema');
const make=()=>schema.makeSession({id:'test-session',patient:{id:'test-patient',name:'Test Patient'},exercise:{id:'curl',name:'Curl'},startedAt:1000,endedAt:4000,protocolSessionId:1,durations:[2],complete:true});
test('legacy reps stay unassessed; invalid values rejected',()=>{const d=make();schema.validateSession(d);assert.equal(d.num_unassessed,1);assert.equal(d.num_typical,0);d.rep_assessments[0].duration_sec=NaN;assert.throws(()=>schema.validateSession(d),/invalid value/);});
test('baseline flags and zero pain survive JSON round trip',()=>{const d=schema.makeSession({id:'s',patient:null,exercise:{id:'curl',name:'Curl'},startedAt:1000,endedAt:4000,protocolSessionId:1,complete:true,survey:{pain:0},result:{reps:[{id:1,duration:2,assessable:true,flags:['gyro_mean_deg_s']}],stillness:true,unconfirmedFinal:false,placementWarning:false}});schema.validateSession(d);assert.equal(JSON.parse(JSON.stringify(d)).pre_exercise_pain,0);assert.equal(d.num_atypical,1);assert.deepEqual(d.atypical_rep_ids,[1]);});
test('failed uploads stay pending and retry the same document ID without duplicates',async()=>{
 const entry={document:make(),status:'pending'};let fail=true;const writes=[];
 const upload=load('upload',{'./schema':schema,'../firebase/config':{db:{}},'firebase/firestore':{doc:(_db,c,id)=>`${c}/${id}`,Timestamp:{fromDate:d=>d},setDoc:async(ref,payload)=>{writes.push({ref,payload});if(fail)throw {code:'permission-denied'};}},'../baseline/store':{getCatalog:()=>({ready:true,data:{sessionUploads:[entry]}}),markUpload:async(id,error)=>{entry.status=error?'pending':'synced';entry.error=error;}}});
 await upload.syncSessions();assert.equal(entry.status,'pending');assert.match(entry.error,/permission-denied/);fail=false;await Promise.all([upload.syncSessions(),upload.syncSessions()]);assert.equal(entry.status,'synced');await upload.syncSessions();assert.equal(writes.length,2);assert.ok(writes.every(w=>w.ref==='sessions/test-session'));assert.ok(writes[0].payload.started_at instanceof Date);
});
test('unlinked sessions are never uploaded under a guessed patient',async()=>{let wrote=false;const d=make();d.patient=null;const u=load('upload',{'./schema':schema,'../firebase/config':{db:{}},'firebase/firestore':{setDoc:()=>{wrote=true;}},'../baseline/store':{getCatalog:()=>({ready:true,data:{sessionUploads:[{document:d,status:'pending'}]}})}});await u.syncSessions();assert.equal(wrote,false);});
