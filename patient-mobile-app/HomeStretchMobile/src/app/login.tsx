import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { signInWithEmailAndPassword } from "firebase/auth";

import { auth } from "../firebase/config";

/*
 * Patient sign-in. Accounts are created by the care team in the
 * Firebase console (Authentication -> Users); there is no self sign-up.
 * The account's uid is the patient_id used in Firestore.
 */
export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signIn = async () => {
    setBusy(true);
    setError(null);
    try {
      await signInWithEmailAndPassword(auth, email.trim(), password);
      // _layout.tsx redirects to the home screen once signed in.
    } catch {
      setError("Email or password is incorrect. Please check with your care team.");
    } finally {
      setBusy(false);
    }
  };

  const disabled = busy || !email.trim() || !password;

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <StatusBar style="dark" />
      <Text style={styles.title}>HomeStretch</Text>
      <Text style={styles.subtitle}>Sign in with the account from your care team</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        autoComplete="password"
        value={password}
        onChangeText={setPassword}
        onSubmitEditing={() => { if (!disabled) void signIn(); }}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable
        style={[styles.button, disabled && styles.buttonDisabled]}
        onPress={signIn}
        disabled={disabled}
      >
        {busy ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.buttonText}>Sign In</Text>}
      </Pressable>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
    backgroundColor: "#FFFFFF",
  },
  title: {
    fontSize: 34,
    fontWeight: "700",
    color: "#1D4E89",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 17,
    color: "#555555",
    textAlign: "center",
    marginTop: 8,
    marginBottom: 32,
  },
  input: {
    borderWidth: 1,
    borderColor: "#C9D3DF",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 18,
    marginBottom: 14,
  },
  error: {
    color: "#B3261E",
    fontSize: 15,
    marginBottom: 12,
  },
  button: {
    backgroundColor: "#1D4E89",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 6,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 19,
    fontWeight: "600",
  },
});
