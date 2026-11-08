import { openPatientAccount } from '../baseline/store';
import { useSessionSync } from "../sync/useSessionSync";
import { useEffect, useState } from "react";
import { ActivityIndicator, View, Text, Pressable } from "react-native";
import { Stack, router, useSegments } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { onAuthStateChanged, User } from "firebase/auth";

import {doc, onSnapshot} from "firebase/firestore";
import { auth, db } from "../firebase/config";

export default function RootLayout() {
  useSessionSync();
  const segments = useSegments();
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [profileReady,setProfileReady]=useState(false),[complete,setComplete]=useState(false),[profileError,setProfileError]=useState(''),[retry,setRetry]=useState(0);

  useEffect(() => {
    let generation = 0;
    const unsubscribe = onAuthStateChanged(auth, async (next) => {
      const current = ++generation;
      setAuthReady(false);
      setProfileReady(false);
      await openPatientAccount(next ? {id:next.uid,name:next.displayName || next.email || 'Patient'} : null);
      if (current !== generation) return;
      setUser(next);
      setAuthReady(true);
    });
    return () => { generation++; unsubscribe(); };
  }, []);

  useEffect(()=>{
    if(!user){setProfileReady(true);return;}
    setProfileReady(false);setProfileError('');
    return onSnapshot(doc(db,'patients',user.uid),snapshot=>{
      const data=snapshot.data();
      setComplete(!!data?.full_name && !!data?.date_of_birth);
      setProfileReady(true);
    },()=>{setProfileError('Could not load your profile. Please try again.');});
  },[user?.uid,retry]);

  // Send signed-out patients to /login, and signed-in patients away from it.
  useEffect(() => {
    if (!authReady || !profileReady) return;
    const onLogin = segments[0] === "login";
    if (!user && !onLogin) router.replace("/login");
    else if (user && !complete && segments[0] !== "profile") router.replace("/profile");
    else if (user && complete && (onLogin || segments[0] === "profile")) router.replace("/");
  }, [authReady, profileReady, complete, user, segments]);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />

      {authReady && profileReady ? (
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: {
              backgroundColor: "#FFFFFF",
            },
            animation: "fade",
          }}
        />
      ) : (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF" }}>
          {profileError ? <><Text>{profileError}</Text><Pressable onPress={()=>setRetry(v=>v+1)}><Text style={{padding:20,color:"#367FBD"}}>Try again</Text></Pressable></> : <ActivityIndicator size="large" />}
        </View>
      )}
    </SafeAreaProvider>
  );
}
