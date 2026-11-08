import React,{useState} from 'react';
import {Text, TextInput, Pressable, ScrollView, KeyboardAvoidingView, Platform, Image} from 'react-native';
import {LinearGradient} from 'expo-linear-gradient';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import {signOut} from 'firebase/auth';
import {auth} from '../firebase/config';
import {profileDraft,savePatientDetails} from '../firebase/patientProfile';
import {formatBirthInput} from '../firebase/profileValidation';
import {styles} from '../components/authStyles';
export default function ProfileScreen(){
 const inset=useSafeAreaInsets();
 const [name,setName]=useState(profileDraft.name||auth.currentUser?.displayName||''),[dob,setDob]=useState(profileDraft.dob),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function save(){if(busy)return;setBusy(true);setError('');try{await savePatientDetails(name,dob);}catch(e){setError(e instanceof Error?e.message:'Could not save. Please try again.');}finally{setBusy(false);}}
 return <LinearGradient colors={['#C4DCEF','#FFFFFF']} style={styles.screen}><KeyboardAvoidingView style={styles.screen} behavior={Platform.OS==='ios'?'padding':undefined}><ScrollView contentContainerStyle={[styles.content,{paddingTop:inset.top+30,paddingBottom:inset.bottom+24}]} keyboardShouldPersistTaps="handled">
 <Image source={require('../../assets/images/logo-blue.png')} style={styles.logo} resizeMode="contain"/><Text style={styles.title}>Your profile</Text><Text style={styles.subtitle}>Add your details so your care team knows it’s you.</Text>
 <Text style={styles.label}>Full name</Text><TextInput style={[styles.input,styles.form]} value={name} onChangeText={setName} autoComplete="name" accessibilityLabel="Full name"/>
 <Text style={styles.label}>Date of birth</Text><TextInput style={[styles.input,styles.form]} value={dob} onChangeText={v=>setDob(formatBirthInput(v))} placeholder="MM/DD/YYYY" keyboardType="number-pad" maxLength={10} accessibilityLabel="Date of birth"/>
 {!!error&&<Text style={styles.error} accessibilityRole="alert">{error}</Text>}
 <Pressable accessibilityRole="button" disabled={busy} style={[styles.button,styles.form]} onPress={()=>void save()}><Text style={styles.buttonText}>{busy?'Saving…':'Continue'}</Text></Pressable>
 <Pressable style={styles.link} onPress={()=>void signOut(auth)}><Text style={styles.linkText}>Sign out</Text></Pressable>
 </ScrollView></KeyboardAvoidingView></LinearGradient>;
}
