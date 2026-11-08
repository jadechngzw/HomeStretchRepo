import React, {useEffect, useState} from 'react';
import {Text, TextInput, View, Pressable, ScrollView, StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator} from 'react-native';
import {Ionicons} from '@expo/vector-icons';
import {router} from 'expo-router';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import {collection, doc, onSnapshot, query, where, writeBatch, serverTimestamp, setDoc, orderBy, limit} from 'firebase/firestore';
import {sendEmailVerification} from 'firebase/auth';
import {auth, db} from '../firebase/config';
import {Button} from '../baseline/ui';

type Row = {id:string; [key:string]:any};
export default function MessagesScreen() {
  const user=auth.currentUser;
  const inset=useSafeAreaInsets();
  const [loading,setLoading]=useState(true),[chatLoading,setChatLoading]=useState(false);
  const [invites,setInvites]=useState<Row[]>([]),[links,setLinks]=useState<Row[]>([]),[messages,setMessages]=useState<Row[]>([]);
  const [selected,setSelected]=useState(''),[text,setText]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  useEffect(()=>{
    if(!user)return;
    const fail=(e:Error)=>setError(e.message);
    const a=onSnapshot(query(collection(db,'careInvites'),where('patient_id','==',user.uid)),snap=>setInvites(snap.docs.map(d=>({...d.data(),id:d.id} as Row)).filter(d=>d.status==='pending')),fail);
    const b=onSnapshot(query(collection(db,'careLinks'),where('patient_id','==',user.uid)),snap=>{setLinks(snap.docs.map(d=>({...d.data(),id:d.id} as Row)).filter(d=>d.status==='active'));setLoading(false);},fail);
    return()=>{a();b();};
  },[user?.uid]);
  const active=links.find(l=>l.id===selected);
  useEffect(()=>{
    setMessages([]);setText('');setChatLoading(!!active);
    if(!active)return;
    return onSnapshot(query(collection(db,'conversations',active.id,'messages'),orderBy('created_at','desc'),limit(100)),snap=>{setMessages(snap.docs.map(d=>({...d.data(),id:d.id} as Row)).reverse());setChatLoading(false);},e=>setError(e.message));
  },[active?.id]);
  async function run(action:()=>Promise<void>){if(busy)return;setBusy(true);setError('');try{await action();}catch(e){setError(e instanceof Error?e.message:'Please try again.');}finally{setBusy(false);}}
  async function respond(invite:Row,accept:boolean){
    if(!user)return;
    if(accept){await user.reload();await user.getIdToken(true);if(!user.emailVerified)throw new Error('Verify your email before accepting. Check your inbox or use the button below.');}
    const batch=writeBatch(db);
    batch.update(doc(db,'careInvites',invite.id),{status:accept?'accepted':'declined',responded_at:serverTimestamp()});
    if(accept)batch.set(doc(db,'careLinks',invite.link_id),{patient_id:user.uid,clinician_id:invite.clinician_id,clinician_name:invite.clinician_name,patient_name:invite.patient_name,invite_id:invite.id,status:'active',created_at:serverTimestamp()});
    await batch.commit();
  }
  return <View style={ui.screen}>
    <View style={[ui.header,{paddingTop:inset.top+12}]}>
      {active?<Pressable accessibilityLabel="Back to messages" style={ui.headerButton} onPress={()=>setSelected('')}><Ionicons name="arrow-back" size={28} color="#367FBD"/></Pressable>:<View style={ui.headerButton}/>}
      <Text style={ui.heading} numberOfLines={2}>{active?active.clinician_name:'Messages'}</Text>
      <Pressable accessibilityLabel="Settings" style={[ui.headerButton,ui.settings]} onPress={()=>router.push('/settings')}><Ionicons name="settings-outline" size={25} color="#367FBD"/></Pressable>
    </View>
    <KeyboardAvoidingView style={ui.body} behavior={Platform.OS==='ios'?'padding':undefined}>
      {!!error&&<Text accessibilityRole="alert" style={ui.error}>{error}</Text>}
      {!active?<ScrollView contentContainerStyle={ui.list}>
        {!user?.emailVerified&&<Button title="Send verification email" secondary busy={busy} onPress={()=>void run(async()=>{if(user)await sendEmailVerification(user);})}/>}
        {invites.map(invite=><View style={ui.invite} key={invite.id}><Text style={ui.name}>{invite.clinician_name}</Text><Text style={ui.subtitle}>Would like to join your care team and view your recordings and surveys.</Text><Button title="Accept invitation" busy={busy} onPress={()=>void run(()=>respond(invite,true))}/><Button title="Decline" secondary disabled={busy} onPress={()=>void run(()=>respond(invite,false))}/></View>)}
        {loading?<ActivityIndicator color="#367FBD"/>:!links.length&&!invites.length?<View style={ui.empty}><Ionicons name="people-outline" size={38} color="#98A1AB"/><Text style={ui.emptyTitle}>Your care team</Text><Text style={ui.emptyText}>Give your clinician the email you use to sign in. Their invitation will appear here.</Text></View>:null}
        {links.map(link=><Pressable accessibilityRole="button" key={link.id} style={ui.provider} onPress={()=>{setError('');setSelected(link.id);}}><View style={{flex:1}}><Text style={ui.name}>{link.clinician_name}</Text><Text style={ui.subtitle}>Your care team</Text></View><Ionicons name="chevron-forward" size={25} color="#367FBD"/></Pressable>)}
      </ScrollView>:<>
        <ScrollView contentContainerStyle={[ui.chat,!messages.length&&{flexGrow:1,justifyContent:'center'}]} keyboardShouldPersistTaps="handled">
          {chatLoading?<ActivityIndicator color="#367FBD"/>:!messages.length?<View style={ui.empty}><Ionicons name="chatbubble-outline" size={38} color="#98A1AB"/><Text style={ui.emptyTitle}>No messages yet</Text><Text style={ui.emptyText}>Send a message to your care team.</Text></View>:null}
          {messages.map(message=><View key={message.id} style={[ui.bubble,message.sender_id===user?.uid?ui.outgoing:ui.incoming]}><Text style={ui.message}>{message.text}</Text></View>)}
        </ScrollView>
        <View style={ui.composer}><TextInput accessibilityLabel="Message" value={text} onChangeText={setText} placeholder="Send message…" placeholderTextColor="#498AC2" multiline maxLength={2000} style={ui.input}/><Pressable accessibilityLabel="Send message" accessibilityRole="button" disabled={busy||!text.trim()} style={[ui.send,(busy||!text.trim())&&{opacity:.45}]} onPress={()=>void run(async()=>{const ref=doc(collection(db,'conversations',active.id,'messages'));await setDoc(ref,{sender_id:user!.uid,text:text.trim(),created_at:serverTimestamp()});setText('');})}>{busy?<ActivityIndicator color="#367FBD"/>:<Ionicons name="paper-plane-outline" size={25} color="#367FBD"/>}</Pressable></View>
      </>}
    </KeyboardAvoidingView>
    <View style={[ui.tabs,{paddingBottom:Math.max(inset.bottom,12)}]}>{([{label:'Messages',icon:'chatbubble',path:'/messages'},{label:'Exercise',icon:'fitness',path:'/exercise'},{label:'Progress',icon:'bar-chart',path:'/progress'},{label:'Readiness',icon:'shield-checkmark',path:'/adherence'}] as const).map(tab=><Pressable key={tab.label} accessibilityRole="button" accessibilityState={{selected:tab.label==='Messages'}} style={ui.tab} onPress={()=>router.replace(tab.path)}><Ionicons name={tab.icon} size={24} color="#367FBD"/><Text style={[ui.tabText,tab.label==='Messages'&&{fontWeight:'700'}]}>{tab.label}</Text></Pressable>)}</View>
  </View>;
}
const ui=StyleSheet.create({
 screen:{flex:1,backgroundColor:'#FFFFFF'},body:{flex:1},header:{backgroundColor:'#C4DCEF',paddingHorizontal:16,paddingBottom:14,flexDirection:'row',alignItems:'center',gap:10},headerButton:{width:44,height:44,alignItems:'center',justifyContent:'center'},settings:{backgroundColor:'white',borderRadius:22},heading:{flex:1,textAlign:'center',fontSize:27,fontWeight:'700',color:'#367FBD'},list:{padding:18,gap:14},provider:{backgroundColor:'#C2DAEC',borderRadius:23,padding:18,flexDirection:'row',alignItems:'center',gap:12},name:{fontSize:21,fontWeight:'700',color:'#202B33'},subtitle:{fontSize:16,color:'#56626B',marginTop:4,lineHeight:23},invite:{backgroundColor:'#EFF6FB',padding:18,borderRadius:23,gap:10},empty:{alignItems:'center',padding:26,gap:10},emptyTitle:{fontSize:21,color:'#8B949E',fontWeight:'600'},emptyText:{fontSize:16,color:'#8B949E',textAlign:'center',lineHeight:24},chat:{padding:18,gap:12},bubble:{borderRadius:20,paddingHorizontal:16,paddingVertical:12,maxWidth:'85%'},outgoing:{alignSelf:'flex-end',backgroundColor:'#D5E5F5',borderBottomRightRadius:5},incoming:{alignSelf:'flex-start',backgroundColor:'#F0F3F6',borderBottomLeftRadius:5},message:{fontSize:17,lineHeight:24,color:'#202B33'},composer:{flexDirection:'row',alignItems:'flex-end',padding:12,gap:9},input:{flex:1,backgroundColor:'#D5E5F5',borderRadius:27,paddingHorizontal:18,paddingTop:14,paddingBottom:14,fontSize:17,color:'#202B33',maxHeight:130},send:{width:50,height:50,borderRadius:25,backgroundColor:'#D5E5F5',alignItems:'center',justifyContent:'center'},tabs:{flexDirection:'row',backgroundColor:'#D8E7F3',paddingTop:14,borderTopWidth:1,borderTopColor:'#B1CEE5'},tab:{flex:1,alignItems:'center',gap:6,borderRightWidth:1,borderRightColor:'#B1CEE5',paddingVertical:3},tabText:{fontSize:13,color:'#367FBD'},error:{color:'#A53535',padding:14,backgroundColor:'#FFF0F0'}
});
