import React from "react";
import SettingsButton from "../components/SettingsButton";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

export type Exercise = {
  id: string;
  name: string;
  category?: string;
  instructions: string;
  sets?: number;
  reps?: number;
  duration: string;
};

const exercises: Exercise[] = [
  {
    id: "shoulder-rolls",
    name: "Shoulder Rolls",
    category: "warm up",
    instructions: "Both directions x10",
    reps: 10,
    duration: "~ 1 min",
  },
  {
    id: "knee-extensions",
    name: "Gentle Knee Extensions",
    category: "warm up",
    instructions: "2 sets | 10 reps",
    sets: 2,
    reps: 10,
    duration: "~ 3 min",
  },
  {
    id: "sit-to-stand",
    name: "Sit to Stand",
    instructions: "2 sets | 10 reps",
    sets: 2,
    reps: 10,
    duration: "~ 3 min",
  },
  {
    id: "bicep-curls",
    name: "Bicep Curls",
    instructions: "2 sets | 10 reps",
    sets: 2,
    reps: 10,
    duration: "~ 3 min",
  },
  {
    id: "seated-arm-raises",
    name: "Seated Arm Raises",
    instructions: "2 sets | 10 reps",
    sets: 2,
    reps: 10,
    duration: "~ 3 min",
  },
  {
    id: "weight-shifts",
    name: "Weight Shifts",
    instructions: "2 sets | 10 reps",
    sets: 2,
    reps: 10,
    duration: "~ 2 min",
  },
];

export default function ExerciseScreen() {
  return (
    <View style={styles.screen}>

      {/* HEADER */}
      <View style={styles.header}>
        <SettingsButton />
        <Text style={styles.headerTitle}>
          Session Overview
        </Text>
      </View>

      {/* EXERCISES */}
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {exercises.map((exercise) => (
          <Pressable
            key={exercise.id}
            style={({ pressed }) => [
              styles.exerciseCard,
              pressed && styles.cardPressed,
            ]}
            onPress={() =>
              router.push({
                pathname: "/exercise-detail",
                params: {
                  id: exercise.id,
                },
              })
            }
          >
            <Text style={styles.exerciseName}>
              {exercise.name}

              {exercise.category && (
                <Text style={styles.category}>
                  {" "}({exercise.category})
                </Text>
              )}
            </Text>

            <Text style={styles.instructions}>
              {exercise.instructions}
            </Text>

            <Text style={styles.duration}>
              {exercise.duration}
            </Text>

            <View style={styles.arrowCircle}>
              <Ionicons
                name="chevron-forward"
                size={24}
                color="#367FBD"
              />
            </View>
          </Pressable>
        ))}

        {/* SURVEY */}
        <Pressable
          style={({ pressed }) => [
            styles.surveyButton,
            pressed && styles.surveyPressed,
          ]}
          onPress={() => router.push("/survey")}
        >
          <Text style={styles.surveyButtonText}>
            Post-Exercise Survey
          </Text>

          <Ionicons
            name="arrow-forward"
            size={22}
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
    color: "#367FBD",
    fontSize: 26,
    fontWeight: "400",
    textAlign: "center",
  },

  /* CONTENT */

  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 20,
  },

  /* EXERCISE CARDS */

  exerciseCard: {
    backgroundColor: "#BFD8EC",
    borderRadius: 17,
    minHeight: 92,
    paddingHorizontal: 15,
    paddingVertical: 11,
    marginBottom: 12,
    position: "relative",
  },

  cardPressed: {
    opacity: 0.72,
    transform: [{ scale: 0.99 }],
  },

  exerciseName: {
    fontSize: 18,
    fontWeight: "600",
    color: "#111111",
    marginBottom: 5,
    paddingRight: 42,
  },

  category: {
    fontStyle: "italic",
    fontWeight: "400",
  },

  instructions: {
    fontSize: 16,
    color: "#222222",
    marginBottom: 4,
  },

  duration: {
    fontSize: 16,
    color: "#333333",
  },

  arrowCircle: {
    position: "absolute",
    right: 13,
    top: "50%",
    marginTop: -17,
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "#DDEBF5",
    justifyContent: "center",
    alignItems: "center",
  },

  /* SURVEY */

  surveyButton: {
    minHeight: 55,
    backgroundColor: "#367FBD",
    borderRadius: 17,
    marginTop: 8,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },

  surveyPressed: {
    opacity: 0.75,
  },

  surveyButtonText: {
    fontSize: 17,
    fontWeight: "600",
    color: "#FFFFFF",
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