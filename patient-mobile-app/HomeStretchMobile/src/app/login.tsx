import {styles} from '../components/authStyles';
import React, {useState} from 'react';
import {Text, TextInput, Pressable, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, View, Image} from 'react-native';
import {LinearGradient} from 'expo-linear-gradient';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import {signInWithEmailAndPassword, createUserWithEmailAndPassword, sendEmailVerification} from 'firebase/auth';
import {auth} from '../firebase/config';
import {rememberProfile, savePatientDetails} from '../firebase/patientProfile';
import {formatBirthInput, profileFields} from '../firebase/profileValidation';

export default function LoginScreen(){
  const inset=useSafeAreaInsets();
  const [creating,setCreating]=useState(false),[name,setName]=useState(''),[dob,setDob]=useState('');
  const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function submit(){
    if(busy)return;setError('');setBusy(true);
    try{
      if(creating){
        profileFields(name,dob);
        rememberProfile(name,dob);
        const result=await createUserWithEmailAndPassword(auth,email.trim(),password);
        await savePatientDetails(name,dob);
        await sendEmailVerification(result.user);
      }else await signInWithEmailAndPassword(auth,email.trim(),password);
    }catch(e){
      const code=(e as {code?:string}).code;
      setError(code==='auth/email-already-in-use'?'An account already uses this email. Please sign in.':code==='auth/weak-password'?'Use a password with at least 6 characters.':code?'Could not sign in. Check your details and connection.':e instanceof Error?e.message:'Please try again.');
    }finally{setBusy(false);}
  }
  const disabled=busy||!email.trim()||!password||(creating&&(!name.trim()||!dob));
  return <LinearGradient colors={['#C4DCEF','#EFF6FB','#FFFFFF']} locations={[0,.55,1]} style={styles.screen}>
    <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS==='ios'?'padding':undefined}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={[styles.content,{paddingTop:inset.top+32,paddingBottom:inset.bottom+24}]}>
        <Image source={require('../../assets/images/logo-blue.png')} style={styles.logo} resizeMode="contain"/>
        <Text style={styles.brand}>HomeStretch</Text>
        <Text style={styles.title}>{creating?'Create your account':'Welcome back'}</Text>
        <Text style={styles.subtitle}>{creating?'A few details to get started.':'Sign in to continue your exercises.'}</Text>
        <View style={styles.form}>
          {creating&&<><Text style={styles.label}>Full name</Text><TextInput accessibilityLabel="Full name" style={styles.input} value={name} onChangeText={setName} autoComplete="name" placeholder="Your full name" editable={!busy}/>
          <Text style={styles.label}>Date of birth</Text><TextInput accessibilityLabel="Date of birth, month day year" style={styles.input} value={dob} onChangeText={v=>setDob(formatBirthInput(v))} placeholder="MM/DD/YYYY" keyboardType="number-pad" maxLength={10} editable={!busy}/></>}
          <Text style={styles.label}>Email</Text><TextInput accessibilityLabel="Email" style={styles.input} value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email" keyboardType="email-address" placeholder="you@example.com" editable={!busy}/>
          <Text style={styles.label}>Password</Text><TextInput accessibilityLabel="Password" style={styles.input} value={password} onChangeText={setPassword} secureTextEntry autoComplete={creating?'new-password':'current-password'} placeholder={creating?'At least 6 characters':'Your password'} editable={!busy} onSubmitEditing={()=>{if(!disabled)void submit();}}/>
          {!!error&&<Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
          <Pressable accessibilityRole="button" disabled={disabled} style={[styles.button,disabled&&{opacity:.5}]} onPress={()=>void submit()}>{busy?<ActivityIndicator color="#367FBD"/>:<Text style={styles.buttonText}>{creating?'Create account':'Sign in'}</Text>}</Pressable>
          <Pressable accessibilityRole="button" disabled={busy} style={styles.link} onPress={()=>{setCreating(!creating);setError('');}}><Text style={styles.linkText}>{creating?'Already have an account? Sign in':'New to HomeStretch? Create an account'}</Text></Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  </LinearGradient>;
}
