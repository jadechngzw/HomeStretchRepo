import { doc, setDoc, Timestamp } from 'firebase/firestore';
import { auth, db } from '../firebase/config';
import { getCatalog, markUpload, markSurveySynced } from '../baseline/store';
import { uploadError, validateSession } from './schema';
let busy:Promise<void>|null=null;
const inFlight=new Map<string,Promise<void>>();
function timeout<T>(operation:Promise<T>,ms:number):Promise<T>{return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject({code:'timeout'}),ms);operation.then(value=>{clearTimeout(timer);resolve(value);},error=>{clearTimeout(timer);reject(error);});});}
export function syncSessions():Promise<void>{
  if(busy)return busy;
  busy=(async()=>{
    const catalog=getCatalog();const user=auth.currentUser;if(!user||!catalog.ready||catalog.error)return;
    for (const survey of catalog.data.surveys) {
      if (!survey.day || survey.patientId !== user.uid || survey.syncedAt) continue;
      if (auth.currentUser?.uid !== user.uid) return;
      try {
        const id = `${user.uid}_${survey.day}_${survey.phase}`;
        const {syncedAt, ...answers} = survey;
        await timeout(setDoc(doc(db,'dailySurveys',id), {...answers, patient_id:user.uid, local_date:survey.day, recorded_at:Timestamp.fromDate(new Date(survey.recordedAt))}),15000);
        await markSurveySynced(survey.id);
      } catch { /* Keep the persisted survey pending; sessions can still upload. */ }
    }
    for(const entry of catalog.data.sessionUploads??[]){
      if(auth.currentUser?.uid!==user.uid)return;
      if(entry.status==='synced'||!entry.document.patient||entry.document.patient_id!==user.uid)continue;
      const record=entry.document,id=record.session_id;
      try{
        validateSession(record);
        // A stable document ID makes retries idempotent. No anonymous addDoc duplicates.
        const key=JSON.stringify(record);
        let write=inFlight.get(key);
        if(!write){write=setDoc(doc(db,'sessions',id),{...record,started_at:Timestamp.fromDate(new Date(record.started_at)),ended_at:Timestamp.fromDate(new Date(record.ended_at)),timestamp:Timestamp.fromDate(new Date(record.started_at))});inFlight.set(key,write);void write.then(()=>inFlight.delete(key),()=>inFlight.delete(key));}
        await timeout(write,15000);
        await markUpload(id,null,record);
      }catch(e){await markUpload(id,uploadError(e),record);break;}
    }
  })().finally(()=>{busy=null;});return busy;
}
