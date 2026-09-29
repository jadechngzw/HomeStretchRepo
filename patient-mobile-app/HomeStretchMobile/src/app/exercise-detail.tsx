import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";

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

export default function ExerciseDetailScreen() {
  const { id } = useLocalSearchParams<{
    id: string;
  }>();

  const exercise =
    exerciseInfo[id || "sit-to-stand"] ??
    exerciseInfo["sit-to-stand"];

  const [reps, setReps] = useState(0);

  const increaseRep = () => {
    setReps((current) =>
      Math.min(
        current + 1,
        exercise.reps
      )
    );
  };

  const decreaseRep = () => {
    setReps((current) =>
      Math.max(current - 1, 0)
    );
  };

  const completeExercise = () => {
    router.replace("/exercise");
  };

  return (
    <View style={styles.screen}>

      {/* HEADER */}
      <View style={styles.header}>

        {/* BACK ARROW */}
        <Pressable
          style={styles.backButton}
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons
            name="arrow-back-circle-outline"
            size={29}
            color="#367FBD"
          />
        </Pressable>

        <Text style={styles.headerTitle}>
          {exercise.name}
        </Text>

      </View>

      {/* CONTENT */}
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >

        {/* DEMO VIDEO */}
        <View style={styles.videoContainer}>

          <Ionicons
            name="play-circle-outline"
            size={58}
            color="#367FBD"
          />

          <Text style={styles.videoLabel}>
            Stickman Demo Video
          </Text>

          <Text style={styles.videoPlaceholder}>
            Video placeholder
          </Text>

        </View>


        {/* VIDEO CONTROLS */}
        <View style={styles.videoControls}>

          <Pressable>
            <Ionicons
              name="play-skip-back"
              size={29}
              color="#4A8BC3"
            />
          </Pressable>

          <Pressable>
            <Ionicons
              name="play-circle"
              size={42}
              color="#4A8BC3"
            />
          </Pressable>

          <Pressable>
            <Ionicons
              name="play-skip-forward"
              size={29}
              color="#4A8BC3"
            />
          </Pressable>

        </View>


        {/* PATIENT CAMERA */}
        <View style={styles.cameraContainer}>

          <View style={styles.cameraIconCircle}>
            <Ionicons
              name="camera-outline"
              size={34}
              color="#367FBD"
            />
          </View>

          <Text style={styles.videoLabel}>
            Patient Camera
          </Text>

          <Text style={styles.videoPlaceholder}>
            Live camera placeholder
          </Text>

        </View>


        {/* REP COUNTER */}
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


        {/* COMPLETE */}
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


      {/* BOTTOM NAV */}
      <BottomNavigation />

    </View>
  );
}

function BottomNavigation() {
  return (
    <View style={styles.bottomNav}>

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
  );
}

const styles = StyleSheet.create({
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

  /* CONTENT */

  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 20,
  },

  /* DEMO VIDEO */

  videoContainer: {
    height: 210,
    backgroundColor: "#BFD8EC",
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },

  videoLabel: {
    fontSize: 18,
    color: "#111111",
    marginTop: 8,
    fontWeight: "500",
  },

  videoPlaceholder: {
    fontSize: 13,
    color: "#5C7182",
    marginTop: 4,
  },

  /* VIDEO CONTROLS */

  videoControls: {
    height: 60,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 65,
  },

  /* CAMERA */

  cameraContainer: {
    height: 210,
    backgroundColor: "#BFD8EC",
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
  },

  cameraIconCircle: {
    width: 58,
    height: 58,
    backgroundColor: "#DDEBF5",
    borderRadius: 29,
    alignItems: "center",
    justifyContent: "center",
  },

  /* REP COUNTER */

  counterCard: {
    minHeight: 180,
    backgroundColor: "#BFD8EC",
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
    paddingVertical: 15,
  },

  counterLabel: {
    fontSize: 18,
    color: "#222222",
  },

  counterNumber: {
    fontSize: 70,
    color: "#222222",
    fontWeight: "400",
    lineHeight: 78,
  },

  counterTarget: {
    fontSize: 15,
    color: "#555555",
  },

  counterControls: {
    flexDirection: "row",
    gap: 15,
    marginTop: 8,
  },

  counterButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "#FFFFFF",
    alignItems: "center",
    justifyContent: "center",
  },

  /* COMPLETE */

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

  /* BOTTOM NAV */

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
});