import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  Switch,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { useWearable } from "../wearable/useWearable";

import { useCameraPreference } from "../preferences/camera";

export default function SettingsScreen() {
  const wearable = useWearable();
  const watchStatus = wearable.phase;
  const [pickerOpen, setPickerOpen] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useCameraPreference();
  useFocusEffect(useCallback(() => () => { void wearable.stopScan(); }, [wearable.stopScan]));
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  return (
    <View style={styles.screen}>
      <StatusBar style="dark" />

      {/* =========================================
          HEADER
      ========================================= */}

      <View style={styles.header}>
        <Pressable
          style={styles.backButton}
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons
            name="arrow-back"
            size={29}
            color="#367FBD"
          />
        </Pressable>

        <Text style={styles.headerTitle}>
          Settings
        </Text>
      </View>

      {/* =========================================
          CONTENT
      ========================================= */}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >

        {/* =======================================
            WEARABLE
        ======================================= */}

        <Text style={styles.sectionTitle}>
          Wearable Device
        </Text>

        <View style={styles.card}>

          <View style={styles.row}>
            <View style={styles.iconCircle}>
              <Ionicons
                name="watch-outline"
                size={25}
                color="#367FBD"
              />
            </View>

            <View style={styles.rowText}>
              <Text style={styles.cardTitle}>
                HomeStretch Wearable
              </Text>

              <View style={styles.statusRow}>

                <View
                  style={[
                    styles.statusDot,
                    watchStatus ===
                      "connected"
                      ? styles.connected
                      : styles.checking,
                  ]}
                />

                <Text style={styles.statusText}>
                  {wearable.message}
                </Text>

              </View>
            </View>
          </View>

          {watchStatus === "connected" || watchStatus === "disconnecting" ? (
            <View>
              <Text style={[styles.description, { marginTop: 8 }]}>{wearable.selectedName}</Text>
              <Pressable accessibilityRole="button" disabled={wearable.busy}
                style={styles.connectButton} onPress={() => void wearable.disconnect()}>
                <Text style={styles.connectButtonText}>{wearable.busy ? "Disconnecting…" : "Disconnect"}</Text>
              </Pressable>
            </View>
          ) : (
            <View>
              <Pressable accessibilityRole="button" accessibilityLabel="Choose a watch"
                accessibilityState={{ expanded: pickerOpen, disabled: watchStatus === "connecting" }}
                disabled={watchStatus === "connecting"}
                style={styles.devicePicker}
                onPress={() => {
                  setPickerOpen(!pickerOpen);
                  if (pickerOpen) void wearable.stopScan();
                  else void wearable.scan();
                }}>
                <Text style={styles.deviceName}>{watchStatus === "connecting" ? "Connecting…" : "Choose a watch"}</Text>
                <Ionicons name={pickerOpen ? "chevron-up" : "chevron-down"} size={20} color="#367FBD" />
              </Pressable>
              {pickerOpen && (
                <View style={styles.deviceList}>
                  {wearable.devices.map(device => (
                    <Pressable key={device.id} accessibilityRole="button"
                      accessibilityLabel={`Connect to ${device.name}, ${device.id.slice(-4)}`}
                      disabled={watchStatus === "connecting" || watchStatus === "preparing"}
                      style={styles.deviceOption}
                      onPress={() => { setPickerOpen(false); void wearable.connect(device.id); }}>
                      <Ionicons name="watch-outline" size={22} color="#367FBD" />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.deviceName}>{device.name}</Text>
                        <Text style={styles.description}>Watch ending in {device.id.slice(-4)}</Text>
                      </View>
                      <Ionicons name="chevron-forward" size={18} color="#367FBD" />
                    </Pressable>
                  ))}
                  <Text style={[styles.description, { padding: 12 }]}>
                    {watchStatus === "scanning" || watchStatus === "preparing"
                      ? "Searching for nearby watches…"
                      : wearable.devices.length ? "Select your watch to connect." : "No watches found nearby."}
                  </Text>
                  {watchStatus === "disconnected" && (
                    <Pressable accessibilityRole="button" style={styles.deviceOption} onPress={() => void wearable.scan()}>
                      <Ionicons name="refresh-outline" size={20} color="#367FBD" />
                      <Text style={styles.deviceName}>Search again</Text>
                    </Pressable>
                  )}
                </View>
              )}
            </View>
          )}
          {wearable.error ? (
            <Text accessibilityRole="alert" style={[styles.description, { color: "#A12622", marginTop: 12 }]}>
              {wearable.error}
            </Text>
          ) : null}

        </View>


        {/* =======================================
            CAMERA
        ======================================= */}

        <Text style={styles.sectionTitle}>
          Camera
        </Text>

        <View style={styles.card}>

          <View style={styles.row}>

            <View style={styles.iconCircle}>
              <Ionicons
                name="camera-outline"
                size={25}
                color="#367FBD"
              />
            </View>

            <View style={styles.rowText}>

              <Text style={styles.cardTitle}>
                Exercise Camera
              </Text>

              <Text style={styles.description}>Show your camera during exercises.</Text>
            </View>
            <Switch
              accessibilityLabel="Enable exercise camera"
              value={cameraEnabled}
              onValueChange={setCameraEnabled}
              trackColor={{ false: "#D5E7F3", true: "#76A9D2" }}
              thumbColor="#FFFFFF"
            />
          </View>
        </View>

        {/* =======================================
            NOTIFICATIONS
        ======================================= */}

        <Text style={styles.sectionTitle}>
          Notifications
        </Text>

        <View style={styles.card}>

          <View style={styles.row}>

            <View style={styles.iconCircle}>
              <Ionicons
                name="notifications-outline"
                size={25}
                color="#367FBD"
              />
            </View>

            <View style={styles.rowText}>

              <Text style={styles.cardTitle}>
                Exercise Reminders
              </Text>

              <Text style={styles.description}>
                Receive reminders to complete your
                exercises.
              </Text>

            </View>

            <Switch
              value={notificationsEnabled}
              onValueChange={
                setNotificationsEnabled
              }
              trackColor={{
                false: "#D5E7F3",
                true: "#76A9D2",
              }}
              thumbColor="#FFFFFF"
            />

          </View>

        </View>


        {/* =======================================
            PROFILE
        ======================================= */}

        <Text style={styles.sectionTitle}>
          Profile
        </Text>

        <Pressable
          style={({ pressed }) => [
            styles.card,
            pressed && styles.cardPressed,
          ]}
        >
          <View style={styles.row}>

            <View style={styles.profileCircle}>
              <Text style={styles.profileLetter}>
                J
              </Text>
            </View>

            <View style={styles.rowText}>

              <Text style={styles.cardTitle}>
                Jane
              </Text>

              <Text style={styles.description}>
                Patient profile
              </Text>

            </View>

            <Ionicons
              name="chevron-forward"
              size={23}
              color="#4A8BC3"
            />

          </View>
        </Pressable>


        {/* =======================================
            HELP
        ======================================= */}

        <Text style={styles.sectionTitle}>
          Support
        </Text>

        <Pressable
          style={({ pressed }) => [
            styles.card,
            pressed && styles.cardPressed,
          ]}
        >
          <View style={styles.row}>

            <View style={styles.iconCircle}>
              <Ionicons
                name="help-circle-outline"
                size={25}
                color="#367FBD"
              />
            </View>

            <View style={styles.rowText}>

              <Text style={styles.cardTitle}>
                Help & Support
              </Text>

              <Text style={styles.description}>
                Get help with HomeStretch.
              </Text>

            </View>

            <Ionicons
              name="chevron-forward"
              size={23}
              color="#4A8BC3"
            />

          </View>
        </Pressable>


        {/* =======================================
            ABOUT
        ======================================= */}

        <Pressable
          style={({ pressed }) => [
            styles.card,
            pressed && styles.cardPressed,
          ]}
        >
          <View style={styles.row}>

            <View style={styles.iconCircle}>
              <Ionicons
                name="information-circle-outline"
                size={25}
                color="#367FBD"
              />
            </View>

            <View style={styles.rowText}>

              <Text style={styles.cardTitle}>
                About HomeStretch
              </Text>

              <Text style={styles.description}>
                Version 1.0
              </Text>

            </View>

            <Ionicons
              name="chevron-forward"
              size={23}
              color="#4A8BC3"
            />

          </View>
        </Pressable>


        <Text style={styles.footerText}>
          HomeStretch Rehabilitation
        </Text>

      </ScrollView>

    </View>
  );
}


/* =====================================================
   STYLES
===================================================== */

const styles = StyleSheet.create({
  devicePicker: { marginTop: 14, padding: 13, borderWidth: 1, borderColor: "#BFD8EC", borderRadius: 12, backgroundColor: "#FFFFFF", flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  deviceList: { marginTop: 6, borderRadius: 12, backgroundColor: "#FFFFFF", overflow: "hidden" },
  deviceOption: { padding: 13, flexDirection: "row", alignItems: "center", gap: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: "#D5E7F3" },
  deviceName: { color: "#367FBD", fontSize: 15, fontWeight: "500" },

  screen: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },

  /* HEADER */

  header: {
    height: 120,
    paddingTop: 52,
    backgroundColor: "#C4DCEF",
    borderBottomWidth: 1,
    borderBottomColor: "#76A9D2",
    alignItems: "center",
    justifyContent: "center",
  },

  headerTitle: {
    fontSize: 26,
    color: "#367FBD",
    fontWeight: "400",
  },

  backButton: {
    position: "absolute",
    left: 15,
    top: 66,
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 10,
  },

  /* CONTENT */

  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 18,
    paddingBottom: 40,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#222222",
    marginBottom: 9,
    marginTop: 7,
  },

  /* CARDS */

  card: {
    backgroundColor: "#EEF4F8",
    borderRadius: 17,
    padding: 15,
    marginBottom: 16,
  },

  cardPressed: {
    opacity: 0.7,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
  },

  rowText: {
    flex: 1,
    marginLeft: 11,
  },

  cardTitle: {
    fontSize: 16,
    fontWeight: "500",
    color: "#111111",
    marginBottom: 3,
  },

  description: {
    fontSize: 13,
    lineHeight: 19,
    color: "#666666",
  },

  /* ICONS */

  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#D9E8F4",
    alignItems: "center",
    justifyContent: "center",
  },

  profileCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#BFD8EC",
    alignItems: "center",
    justifyContent: "center",
  },

  profileLetter: {
    fontSize: 21,
    fontWeight: "600",
    color: "#367FBD",
  },

  /* STATUS */

  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 2,
  },

  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },

  connected: {
    backgroundColor: "#55B96A",
  },

  checking: {
    backgroundColor: "#E3B84B",
  },

  statusText: {
    fontSize: 13,
    color: "#555555",
  },

  /* CONNECT BUTTON */

  connectButton: {
    height: 46,
    backgroundColor: "#367FBD",
    borderRadius: 13,
    marginTop: 13,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },

  connectButtonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "600",
  },

  buttonPressed: {
    opacity: 0.75,
  },

  /* FOOTER */

  footerText: {
    textAlign: "center",
    color: "#A0A0A0",
    fontSize: 12,
    marginTop: 14,
  },
});