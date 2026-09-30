import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
} from "react-native";

import {
  CameraView,
  useCameraPermissions,
} from "expo-camera";

import { Ionicons } from "@expo/vector-icons";
import {
  router,
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

  const [reps, setReps] = useState(0);

  const [permission, requestPermission] =
    useCameraPermissions();


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
     COMPLETE EXERCISE
  =================================================== */

  const completeExercise = () => {
    router.replace("/exercise");
  };


  /* ===================================================
     CAMERA PERMISSION LOADING
  =================================================== */

  if (!permission) {
    return (
      <View style={styles.permissionScreen}>
        <StatusBar style="dark" />

        <Text style={styles.permissionTitle}>
          Loading camera...
        </Text>
      </View>
    );
  }


  /* ===================================================
     CAMERA PERMISSION REQUEST
  =================================================== */

  if (!permission.granted) {
    return (
      <View style={styles.permissionScreen}>
        <StatusBar style="dark" />

        <View style={styles.permissionCard}>

          <Ionicons
            name="camera-outline"
            size={55}
            color="#367FBD"
          />

          <Text style={styles.permissionTitle}>
            Camera Access
          </Text>

          <Text style={styles.permissionText}>
            HomeStretch uses your camera to show
            your movement while you exercise.
          </Text>

          <Pressable
            style={styles.permissionButton}
            onPress={requestPermission}
          >
            <Text style={styles.permissionButtonText}>
              Allow Camera
            </Text>
          </Pressable>

          <Pressable
            style={styles.permissionBackButton}
            onPress={() => router.back()}
          >
            <Text style={styles.permissionBackText}>
              Go Back
            </Text>
          </Pressable>

        </View>
      </View>
    );
  }


  /* ===================================================
     MAIN SCREEN
  =================================================== */

  return (
    <View style={styles.screen}>

      <StatusBar style="dark" />


      {/* =================================================
          HEADER
      ================================================= */}

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
          {exercise.name}
        </Text>

      </View>


      {/* =================================================
          CONTENT
      ================================================= */}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >

        {/* =================================================
            CAMERA CARD
        ================================================= */}

        <View style={styles.cameraCard}>

          <CameraView
            style={styles.camera}
            facing="front"
          />

          {/* Camera label */}
          <View
            style={styles.cameraLabelContainer}
          >
            <View style={styles.cameraLabel}>
              <Ionicons
                name="camera-outline"
                size={20}
                color="#367FBD"
              />

              <Text
                style={styles.cameraLabelText}
              >
                Exercise Camera
              </Text>
            </View>
          </View>


          {/* Rep counter overlay */}
          <View style={styles.repOverlay}>

            <Text style={styles.repOverlayNumber}>
              {reps}
            </Text>

            <Text style={styles.repOverlayLabel}>
              / {exercise.reps}
            </Text>

          </View>

        </View>


        {/* =================================================
            CAMERA STATUS
        ================================================= */}

        <View style={styles.connectionRow}>

          <View style={styles.connectionDot} />

          <Text style={styles.connectionText}>
            Camera active
          </Text>

        </View>


        {/* =================================================
            REP COUNTER
        ================================================= */}

        <View style={styles.counterCard}>

          <Text style={styles.counterLabel}>
            Reps
          </Text>

          <Text style={styles.counterNumber}>
            {reps}
          </Text>

          <Text style={styles.counterTarget}>
            of {exercise.reps}
          </Text>

          <View style={styles.counterControls}>

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

          </View>

        </View>


        {/* =================================================
            COMPLETE
        ================================================= */}

        <Pressable
          style={({ pressed }) => [
            styles.completeButton,
            pressed && styles.completePressed,
          ]}
          onPress={completeExercise}
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


      {/* =================================================
          BOTTOM NAVIGATION
      ================================================= */}

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

      </View>

    </View>
  );
}


/* =====================================================
   STYLES
===================================================== */

const styles = StyleSheet.create({

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
    paddingTop: 14,
    paddingBottom: 22,
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
    paddingHorizontal: 15,
    paddingVertical: 7,
    borderRadius: 20,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },

  cameraLabelText: {
    color: "#367FBD",
    fontSize: 16,
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
     CAMERA STATUS
  ============================================== */

  connectionRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 9,
    marginBottom: 10,
  },

  connectionDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: "#6BBF72",
    marginRight: 6,
  },

  connectionText: {
    color: "#555555",
    fontSize: 13,
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
     COMPLETE BUTTON
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
     CAMERA PERMISSION
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