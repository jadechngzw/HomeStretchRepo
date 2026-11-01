import { initializeApp, getApps, getApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
// getReactNativePersistence exists only in firebase/auth's React Native build,
// which Metro picks automatically; the web type definitions don't list it.
// @ts-ignore
import { initializeAuth, getAuth, getReactNativePersistence } from "firebase/auth";
import AsyncStorage from "@react-native-async-storage/async-storage";

const firebaseConfig = {
  apiKey: "AIzaSyDHakg-G1e5XTVGcC2gAl9qrHQ7FR6Z9yk",
  authDomain: "homestretch-pipeline.firebaseapp.com",
  projectId: "homestretch-pipeline",
  storageBucket: "homestretch-pipeline.firebasestorage.app",
  messagingSenderId: "563578060204",
  appId: "1:563578060204:web:8676a02610c1b1402c8e09"
};

const isFirstInit = getApps().length === 0;
const app = isFirstInit ? initializeApp(firebaseConfig) : getApp();

export const db = getFirestore(app);

// Keep the patient signed in between app launches.
export const auth = isFirstInit
  ? initializeAuth(app, { persistence: getReactNativePersistence(AsyncStorage) })
  : getAuth(app);
