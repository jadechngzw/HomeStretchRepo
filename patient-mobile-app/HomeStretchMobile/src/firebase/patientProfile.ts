import {doc, serverTimestamp, setDoc} from 'firebase/firestore';
import {updateProfile} from 'firebase/auth';
import {auth, db} from './config';
import {profileFields} from './profileValidation';
export let profileDraft = {name:'',dob:''};
export function rememberProfile(name:string,dob:string){profileDraft={name,dob};}
export async function savePatientDetails(name:string,dob:string) {
  const user=auth.currentUser;
  if(!user)throw new Error('Please sign in again.');
  const fields=profileFields(name,dob);
  await updateProfile(user,{displayName:fields.full_name});
  await setDoc(doc(db,'patients',user.uid),{...fields,updated_at:serverTimestamp()}, {merge:true});
  profileDraft={name:'',dob:''};
}
