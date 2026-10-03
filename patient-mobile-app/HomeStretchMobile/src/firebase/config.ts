import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyDHakg-G1e5XTVGcC2gAl9qrHQ7FR6Z9yk",
  authDomain: "homestretch-pipeline.firebaseapp.com",
  projectId: "homestretch-pipeline",
  storageBucket: "homestretch-pipeline.firebasestorage.app",
  messagingSenderId: "563578060204",
  appId: "1:563578060204:web:8676a02610c1b1402c8e09"
};

const app = initializeApp(firebaseConfig);

export const db = getFirestore(app);