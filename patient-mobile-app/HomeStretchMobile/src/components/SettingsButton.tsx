import React from "react";
import { Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

type SettingsButtonProps = {
  color?: string;
};

export default function SettingsButton({
  color = "#367FBD",
}: SettingsButtonProps) {
  return (
    <Pressable
      style={({ pressed }) => [
        styles.button,
        pressed && styles.pressed,
      ]}
      onPress={() => router.push("/settings")}
      hitSlop={10}
    >
      <Ionicons
        name="settings-outline"
        size={23}
        color={color}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    position: "absolute",
    right: 15,
    top: 64,
    width: 43,
    height: 43,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.88)",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 20,
  },

  pressed: {
    opacity: 0.65,
    transform: [{ scale: 0.95 }],
  },
});