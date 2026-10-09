import { useCurlSession } from "../wearable/useCurlSession";
import type { Arm } from "../wearable/curlSession";
import { useCameraPreference } from "../preferences/camera";
import { useWearable } from "../wearable/useWearable";
import React, { useCallback, useState } from "react";
import SettingsButton from "../components/SettingsButton";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  Linking,
} from "react-native";

import {
  CameraView,
  useCameraPermissions,
} from "expo-camera";

import { Ionicons } from "@expo/vector-icons";
import {
  router,
  useFocusEffect,
  useLocalSearchParams,
} from "expo-router";

import { StatusBar } from "expo-status-bar";


/* =====================================================
   EXERCISE INFORMATION
===================================================== */

const exerciseInfo: Record<
  string,
  {
    name: string;
    reps: number;
    sets: number;
  }
> = {
  "shoulder-rolls": {
    name: "Shoulder Rolls",
    reps: 10,
    sets: 1,
  },

  "knee-extensions": {
    name: "Gentle Knee Extensions",
    reps: 10,
    sets: 2,
  },

  "sit-to-stand": {
    name: "Sit to Stand",
    reps: 10,
    sets: 2,
  },

  "bicep-curls": {
    name: "Bicep Curls",
    reps: 10,
    sets: 2,
  },

  "heel-raises": {
    name: "Heel Raises",
    reps: 10,
    sets: 2,
  },

  "seated-arm-raises": {
    name: "Seated Arm Raises",
    reps: 10,
    sets: 2,
  },

  "weight-shifts": {
    name: "Weight Shifts",
    reps: 10,
    sets: 2,
  },
};


/* =====================================================
   EXERCISE DETAIL SCREEN
===================================================== */

export default function ExerciseDetailScreen() {
  const { id } = useLocalSearchParams<{
    id: string;
  }>();

  const exercise =
    exerciseInfo[id || "bicep-curls"] ??
    exerciseInfo["bicep-curls"];

  const isCurl = (id || "bicep-curls") === "bicep-curls";
  const session = useCurlSession();
  const [arm, setArm] = useState<Arm | null>(null);
  const [manualReps, setReps] = useState(0);
  const reps = isCurl ? session.reps : manualReps;
  const [cameraEnabled] = useCameraPreference();
  const [focused, setFocused] = useState(false);
  useFocusEffect(useCallback(() => {
    setFocused(true);
    return () => { setFocused(false); session.interrupt("Set interrupted. Start a new set when you return."); };
  }, [session.interrupt]));

  const [permission, requestPermission] =
    useCameraPermissions();

  const wearable = useWearable();
  const watchStatus = wearable.phase;

  const [manualStarted, setExerciseStarted] = useState(false);
  const exerciseStarted = isCurl ? session.running : manualStarted;
  const transitioning = isCurl && ["starting", "stopping"].includes(session.phase);
  const startDisabled = transitioning || (isCurl && !session.running && (!arm || watchStatus !== "connected"));


  /* ===================================================
     REP CONTROLS
  =================================================== */

  const increaseRep = () => {
    setReps((current) =>
      Math.min(current + 1, exercise.reps)
    );
  };

  const decreaseRep = () => {
    setReps((current) =>
      Math.max(current - 1, 0)
    );
  };


  /* ===================================================
     START / END EXERCISE
  =================================================== */

  const toggleExercise = () => {
    if (isCurl) {
      if (session.running) void session.stop();
      else if (arm) void session.start(arm);
    } else setExerciseStarted((current) => !current);
  };


  /* ===================================================
     COMPLETE EXERCISE
  =================================================== */

  const completeExercise = () => {
    router.replace("/exercise");
  };


  /* ===================================================
     MAIN SCREEN
  =================================================== */

  return (
    <View style={styles.screen}>

      <StatusBar style="dark" />


      {/* =============================================
          HEADER
      ============================================= */}

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
        <SettingsButton />
        <Text style={styles.headerTitle}>
          {exercise.name}
        </Text>

      </View>


      {/* =============================================
          CONTENT
      ============================================= */}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={
          styles.scrollContent
        }
      >

        {/* ==========================================
            WATCH CONNECTION STATUS
        ========================================== */}

        <View style={styles.watchStatusRow}>

          <View
            style={[
              styles.statusDot,

              watchStatus === "connected"
                ? styles.connectedDot
                : styles.checkingDot,
            ]}
          />

          <Text style={styles.watchStatusText}>

            {wearable.message}

          </Text>

        </View>



        {isCurl && (
          <View style={styles.armCard}>
            <Text style={styles.armTitle}>Which arm are you exercising?</Text>
            <View style={styles.armOptions}>
              {(["left", "right"] as const).map(side => (
                <Pressable key={side} accessibilityRole="radio"
                  accessibilityState={{ selected: arm === side, disabled: session.running }}
                  disabled={session.running} onPress={() => setArm(side)}
                  style={[styles.armOption, arm === side && styles.armSelected]}>
                  <Text style={[styles.armText, arm === side && { color: "#FFFFFF" }]}>
                    {side === "left" ? "Left arm" : "Right arm"}
                  </Text>
                </Pressable>
              ))}
            </View>
            <Text style={styles.sessionHint}>Wear your watch on that wrist. Start with your arm relaxed at your side.</Text>
            {watchStatus !== "connected" && (
              <Pressable accessibilityRole="button" onPress={() => router.push("/settings")}>
                <Text style={[styles.armText, { marginTop: 10 }]}>Connect your watch</Text>
              </Pressable>
            )}
          </View>
        )}

        {/* ==========================================
            START / END EXERCISE
        ========================================== */}

        <Pressable
          style={({ pressed }) => [
            styles.startExerciseButton,
            startDisabled && { opacity: 0.5 },

            exerciseStarted &&
              styles.endExerciseButton,

            pressed &&
              styles.startExercisePressed,
          ]}
          onPress={toggleExercise}
          disabled={startDisabled}
          accessibilityRole="button"
          accessibilityState={{ disabled: startDisabled, busy: transitioning }}
        >

          <Ionicons
            name={
              exerciseStarted
                ? "stop-circle-outline"
                : "play-circle-outline"
            }
            size={24}
            color="#FFFFFF"
          />

          <Text style={styles.startExerciseText}>
            {isCurl && session.phase === "starting" ? "Preparing…"
              : isCurl && session.phase === "stopping" ? "Finishing…"
              : exerciseStarted ? "End Exercise"
              : isCurl && session.phase === "ended" ? "Start Next Set" : "Start Exercise"}
          </Text>

        </Pressable>


        {isCurl && session.message ? (
          <View style={styles.setMessage}>
            <Text accessibilityLiveRegion="polite" style={styles.armText}>{session.message}</Text>
            {session.phase === "calibrating" && (
              <Text style={styles.sessionHint}>Keep still for a moment. Begin curling when “Counting your reps” appears.</Text>
            )}
            {(session.phase === "ended" || session.phase === "interrupted") && (
              <Text style={styles.sessionHint}>{session.reps} reps · {session.arm === "left" ? "Left arm" : "Right arm"}</Text>
            )}
          </View>
        ) : null}

        {/* ==========================================
            CAMERA
        ========================================== */}

        {cameraEnabled && permission?.granted && focused ? (
        <View style={styles.cameraCard}>

          <CameraView
            style={styles.camera}
            facing="front"
          />


          {/* Camera label */}
          <View
            style={
              styles.cameraLabelContainer
            }
          >
            <View style={styles.cameraLabel}>

              <View
                style={styles.cameraStatusDot}
              />

              <Text
                style={styles.cameraLabelText}
              >
                Camera active
              </Text>

            </View>
          </View>


          {/* Rep counter over camera */}
          <View style={styles.repOverlay}>

            <Text
              style={styles.repOverlayNumber}
            >
              {reps}
            </Text>

            <Text
              style={styles.repOverlayLabel}
            >
              / {exercise.reps}
            </Text>

          </View>

        </View>
        ) : cameraEnabled ? (
          <View style={[styles.cardPlaceholder]}>
            <Ionicons name="camera-outline" size={28} color="#367FBD" />
            <Text style={{ color: "#555555", textAlign: "center" }}>Allow camera access to see your movement.</Text>
            <Pressable accessibilityRole="button" onPress={() => {
              if (permission?.canAskAgain === false) void Linking.openSettings();
              else void requestPermission();
            }}>
              <Text style={{ color: "#367FBD", fontWeight: "600" }}>
                {permission?.canAskAgain === false ? "Open Settings" : "Allow Camera"}
              </Text>
            </Pressable>
          </View>
        ) : null}

        {/* ==========================================
            REP COUNTER
        ========================================== */}

        <View style={styles.counterCard}>

          <Text style={styles.counterLabel}>
            Reps
          </Text>

          <Text style={styles.counterNumber}>
            {reps}
          </Text>

          <Text style={styles.counterTarget}>
            {isCurl ? `Target: ${exercise.reps}` : `of ${exercise.reps}`}
          </Text>

          {!isCurl && <View
            style={styles.counterControls}
          >

            <Pressable
              style={styles.counterButton}
              onPress={decreaseRep}
            >
              <Ionicons
                name="remove"
                size={26}
                color="#367FBD"
              />
            </Pressable>

            <Pressable
              style={styles.counterButton}
              onPress={increaseRep}
            >
              <Ionicons
                name="add"
                size={26}
                color="#367FBD"
              />
            </Pressable>

          </View>}

        </View>


        {/* ==========================================
            COMPLETE EXERCISE
        ========================================== */}

        <Pressable
          style={({ pressed }) => [
            styles.completeButton,
            isCurl && session.running && { opacity: 0.5 },
            pressed &&
              styles.completePressed,
          ]}
          onPress={completeExercise}
          disabled={isCurl && session.running}
        >

          <Text style={styles.completeText}>
            Exercise Completed
          </Text>

          <Ionicons
            name="checkmark-circle-outline"
            size={24}
            color="#FFFFFF"
          />

        </Pressable>

      </ScrollView>


      {/* =============================================
          BOTTOM NAVIGATION
      ============================================= */}

      <View style={styles.bottomNav}>

        {/* Messages */}
        <Pressable
          style={styles.navItem}
          onPress={() =>
            router.push("/messages")
          }
        >
          <Ionicons
            name="chatbox"
            size={25}
            color="#4A8BC3"
          />

          <Text style={styles.navText}>
            Messages
          </Text>
        </Pressable>


        {/* Exercise */}
        <Pressable
          style={styles.navItem}
          onPress={() =>
            router.replace("/exercise")
          }
        >
          <Ionicons
            name="fitness"
            size={27}
            color="#367FBD"
          />

          <Text
            style={[
              styles.navText,
              styles.activeNavText,
            ]}
          >
            Exercise
          </Text>
        </Pressable>


        {/* Progress */}
        <Pressable
          style={styles.navItem}
          onPress={() =>
            router.push("/progress")
          }
        >
          <Ionicons
            name="bar-chart"
            size={27}
            color="#4A8BC3"
          />

          <Text style={styles.navText}>
            Progress
          </Text>
        </Pressable>

        <Pressable
          style={styles.navItem}
          onPress={() => router.push("/adherence")}
        >
          <Ionicons
            name="shield-checkmark"
            size={24}
            color="#4A8BC3"
          />

          <Text style={styles.navText}>
            Readiness
          </Text>
        </Pressable>
      </View>

    </View>
  );
}


/* =====================================================
   STYLES
===================================================== */

const styles = StyleSheet.create({
  armCard: { padding: 16, backgroundColor: "#EEF4F8", borderRadius: 16, marginBottom: 16 },
  armTitle: { color: "#222222", fontSize: 16, fontWeight: "600", marginBottom: 12 },
  armOptions: { flexDirection: "row", gap: 12 },
  armOption: { flex: 1, alignItems: "center", padding: 13, borderRadius: 12, borderColor: "#367FBD", borderWidth: 1 },
  armSelected: { backgroundColor: "#367FBD" },
  armText: { fontSize: 15, fontWeight: "600", color: "#367FBD" },
  sessionHint: { fontSize: 13, lineHeight: 20, color: "#555555", marginTop: 8 },
  setMessage: { padding: 14, backgroundColor: "#EEF4F8", borderRadius: 12, marginBottom: 16 },
  cardPlaceholder: { padding: 24, gap: 12, alignItems: "center", backgroundColor: "#EEF4F8", borderRadius: 16, marginBottom: 20 },

  /* ==============================================
     SCREEN
  ============================================== */

  screen: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },


  /* ==============================================
     HEADER
  ============================================== */

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
    fontSize: 25,
    color: "#367FBD",
    fontWeight: "400",
    textAlign: "center",
    paddingHorizontal: 65,
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


  /* ==============================================
     CONTENT
  ============================================== */

  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 22,
  },


  /* ==============================================
     WATCH STATUS
  ============================================== */

  watchStatusRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },

  statusDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    marginRight: 7,
  },

  checkingDot: {
    backgroundColor: "#E5B84B",
  },

  connectedDot: {
    backgroundColor: "#55B96A",
  },

  watchStatusText: {
    fontSize: 13,
    color: "#555555",
  },


  /* ==============================================
     START / END BUTTON
  ============================================== */

  startExerciseButton: {
    height: 50,
    backgroundColor: "#367FBD",
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 7,
    marginBottom: 12,
  },

  endExerciseButton: {
    backgroundColor: "#C95D62",
  },

  startExercisePressed: {
    opacity: 0.75,
    transform: [{ scale: 0.99 }],
  },

  startExerciseText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "600",
  },


  /* ==============================================
     CAMERA CARD
  ============================================== */

  cameraCard: {
    height: 390,
    width: "100%",
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: "#BFD8EC",
    position: "relative",
  },

  camera: {
    flex: 1,
  },


  /* ==============================================
     CAMERA LABEL
  ============================================== */

  cameraLabelContainer: {
    position: "absolute",
    top: 14,
    left: 0,
    right: 0,
    alignItems: "center",
  },

  cameraLabel: {
    backgroundColor:
      "rgba(255,255,255,0.90)",
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },

  cameraStatusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#55B96A",
  },

  cameraLabelText: {
    color: "#367FBD",
    fontSize: 15,
    fontWeight: "500",
  },


  /* ==============================================
     REP OVERLAY
  ============================================== */

  repOverlay: {
    position: "absolute",
    right: 14,
    bottom: 14,
    minWidth: 78,
    backgroundColor:
      "rgba(255,255,255,0.92)",
    borderRadius: 17,
    paddingHorizontal: 12,
    paddingVertical: 9,
    alignItems: "center",
  },

  repOverlayNumber: {
    fontSize: 32,
    fontWeight: "600",
    color: "#367FBD",
  },

  repOverlayLabel: {
    fontSize: 13,
    color: "#444444",
  },


  /* ==============================================
     REP COUNTER
  ============================================== */

  counterCard: {
    minHeight: 165,
    backgroundColor: "#BFD8EC",
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 14,
    marginBottom: 14,
    paddingVertical: 12,
  },

  counterLabel: {
    fontSize: 18,
    color: "#222222",
  },

  counterNumber: {
    fontSize: 68,
    lineHeight: 74,
    color: "#222222",
    fontWeight: "400",
  },

  counterTarget: {
    fontSize: 15,
    color: "#555555",
  },

  counterControls: {
    flexDirection: "row",
    gap: 15,
    marginTop: 7,
  },

  counterButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "#FFFFFF",
    alignItems: "center",
    justifyContent: "center",
  },


  /* ==============================================
     COMPLETE
  ============================================== */

  completeButton: {
    minHeight: 55,
    backgroundColor: "#367FBD",
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },

  completePressed: {
    opacity: 0.75,
  },

  completeText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "600",
  },


  /* ==============================================
     BOTTOM NAV
  ============================================== */

  bottomNav: {
    height: 88,
    paddingBottom: 18,
    flexDirection: "row",
    backgroundColor: "#D9E8F4",
    borderTopWidth: 1,
    borderTopColor: "#78ABD2",
  },

  navItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRightWidth: 1,
    borderRightColor: "#78ABD2",
  },

  navText: {
    color: "#4A8BC3",
    fontSize: 12,
    marginTop: 3,
  },

  activeNavText: {
    fontWeight: "600",
  },


  /* ==============================================
     PERMISSION SCREEN
  ============================================== */

  permissionScreen: {
    flex: 1,
    backgroundColor: "#EAF4FA",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 25,
  },

  permissionCard: {
    width: "100%",
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 25,
    alignItems: "center",
  },

  permissionTitle: {
    fontSize: 24,
    fontWeight: "600",
    color: "#367FBD",
    marginTop: 15,
    marginBottom: 10,
    textAlign: "center",
  },

  permissionText: {
    fontSize: 16,
    color: "#444444",
    lineHeight: 23,
    textAlign: "center",
    marginBottom: 20,
  },

  permissionButton: {
    width: "100%",
    height: 52,
    backgroundColor: "#367FBD",
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
  },

  permissionButtonText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "600",
  },

  permissionBackButton: {
    paddingVertical: 15,
  },

  permissionBackText: {
    color: "#367FBD",
    fontSize: 15,
  },

});