import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { Stack, router, useSegments } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { onAuthStateChanged, User } from "firebase/auth";

import { auth } from "../firebase/config";

export default function RootLayout() {
  const segments = useSegments();
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    return onAuthStateChanged(auth, (next) => {
      setUser(next);
      setAuthReady(true);
    });
  }, []);

  // Send signed-out patients to /login, and signed-in patients away from it.
  useEffect(() => {
    if (!authReady) return;
    const onLogin = segments[0] === "login";
    if (!user && !onLogin) router.replace("/login");
    else if (user && onLogin) router.replace("/");
  }, [authReady, user, segments]);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />

      {authReady ? (
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
          <ActivityIndicator size="large" />
        </View>
      )}
    </SafeAreaProvider>
  );
}
