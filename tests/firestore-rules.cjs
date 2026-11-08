const {test,before,after,beforeEach}=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
const {initializeTestEnvironment,assertFails,assertSucceeds}=require('@firebase/rules-unit-testing');
const {doc,setDoc,getDoc,updateDoc,writeBatch,Timestamp,serverTimestamp,collection,query,where,getDocs}=require('firebase/firestore');
let env;
before(async()=>{env=await initializeTestEnvironment({projectId:'demo-homestretch',firestore:{host:'127.0.0.1',port:8088,rules:fs.readFileSync(path.join(__dirname,'../firestore.rules'),'utf8')}});});
after(async()=>{await env.cleanup();});
beforeEach(async()=>{await env.clearFirestore();});
const client=(uid,verified=true)=>env.authenticatedContext(uid,{email_verified:verified}).firestore();
const recording=(uid='p')=>({schema_version:3,session_id:'s',patient_id:uid,patient:{id:uid},status:'completed',started_at:Timestamp.fromMillis(1000),ended_at:Timestamp.fromMillis(2000),num_reps:0,rep_assessments:[],pain:{before:null,after:null},pain_level:null});
async function seed(path,data){await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),path),data));}
async function invite(expired=false){await seed('careInvites/invite',{patient_id:'p',patient_name:'Patient',clinician_id:'c',clinician_name:'Clinician',status:'pending',link_id:'c_p',expires_at:Timestamp.fromMillis(Date.now()+(expired?-10000:60000))});}
function accept(db,overrides={}){const batch=writeBatch(db);batch.update(doc(db,'careInvites/invite'),{status:'accepted',responded_at:serverTimestamp()});batch.set(doc(db,'careLinks/c_p'),{patient_id:'p',patient_name:'Patient',clinician_id:'c',clinician_name:'Clinician',invite_id:'invite',status:'active',created_at:serverTimestamp(),...overrides});return batch.commit();}
test('recording is owned by authenticated patient; retry does not duplicate or change measurements',async()=>{
 const db=client('p');await assertSucceeds(setDoc(doc(db,'sessions/s'),recording()));
 await assertSucceeds(setDoc(doc(db,'sessions/s'),recording()));
 await assertFails(getDoc(doc(client('other'),'sessions/s')));
 await assertFails(setDoc(doc(client('other'),'sessions/s'),recording()));
 await assertFails(updateDoc(doc(db,'sessions/s'),{patient_id:'other'}));
 await assertFails(updateDoc(doc(db,'sessions/s'),{num_reps:99}));
 await assertSucceeds(updateDoc(doc(db,'sessions/s'),{pain_level:0}));
});
test('unsigned users and self-assigned clinician roles are rejected',async()=>{
 await assertFails(setDoc(doc(env.unauthenticatedContext().firestore(),'sessions/s'),recording()));
 await assertFails(setDoc(doc(client('p'),'users/p'),{role:'clinician'}));
});
test('accepting own invitation creates link atomically; another patient cannot accept',async()=>{
 await invite();await assertFails(accept(client('other')));await assertFails(accept(client('p',false)));
 await assertFails(accept(client('p'),{clinician_id:'attacker'}));await assertSucceeds(accept(client('p')));
 await assertSucceeds(getDocs(query(collection(client('p'),'careLinks'),where('patient_id','==','p'))));
});
test('expired invites cannot grant access; revoked connection cannot be replayed',async()=>{
 await invite(true);await assertFails(accept(client('p')));
 await invite();await assertSucceeds(accept(client('p')));
 await seed('careLinks/c_p',{patient_id:'p',clinician_id:'c',status:'revoked'});
 await assertFails(accept(client('p')));
});
test('only active linked participants can read and send messages',async()=>{
 await invite();await assertSucceeds(accept(client('p')));
 const data={sender_id:'p',text:'Hello',created_at:serverTimestamp()};
 await assertSucceeds(setDoc(doc(client('p'),'conversations/c_p/messages/m'),data));
 await assertFails(getDoc(doc(client('other'),'conversations/c_p/messages/m')));
 await assertFails(setDoc(doc(client('p'),'conversations/c_p/messages/forged'),{...data,sender_id:'c'}));
 await updateDoc(doc(client('p'),'careLinks/c_p'),{status:'revoked'});
 await assertFails(getDoc(doc(client('p'),'conversations/c_p/messages/m')));
});
test('daily survey is once per phase and patient; identical retry works',async()=>{
 const db=client('p');const ref=doc(db,'dailySurveys/p_2026-11-07_before');
 const data={patient_id:'p',patientId:'p',local_date:'2026-11-07',phase:'before',pain:0,recorded_at:Timestamp.fromMillis(1000)};
 await assertSucceeds(setDoc(ref,data));await assertSucceeds(setDoc(ref,data));
 await assertFails(updateDoc(ref,{pain:5}));
 await assertFails(getDoc(doc(client('other'),'dailySurveys/p_2026-11-07_before')));
});
test('patient profile accepts own details but never roles or another patient',async()=>{
 const data={full_name:'Jane Smith',date_of_birth:'1990-04-12',updated_at:serverTimestamp()};
 await assertSucceeds(setDoc(doc(client('p'),'patients/p'),data));
 await assertFails(getDoc(doc(client('other'),'patients/p')));
 await assertFails(setDoc(doc(client('other'),'patients/p'),data));
 await assertFails(setDoc(doc(client('p'),'patients/p'),{...data,role:'clinician'}));
 await seed('patients/p',{...data,updated_at:Timestamp.now(),assigned_clinician:'c'});
 await assertSucceeds(updateDoc(doc(client('p'),'patients/p'),{full_name:'Jane Doe',updated_at:serverTimestamp()}));
 await assertFails(updateDoc(doc(client('p'),'patients/p'),{assigned_clinician:'attacker',updated_at:serverTimestamp()}));
 await assertFails(updateDoc(doc(client('p'),'patients/p'),{date_of_birth:'invalid',updated_at:serverTimestamp()}));
});
