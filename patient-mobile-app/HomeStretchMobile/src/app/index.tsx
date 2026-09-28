import React from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
      <LinearGradient
        colors={["#c4dcef", "#f7fafc", "#ffffff"]}
        locations={[0, 0.55, 1]}
        style={styles.container}
      >
        {/* Main content */}
        <View style={styles.content}>

          {/* HomeStretch logo */}
          <View style={styles.logoCircle}>
            <Ionicons
              name="accessibility-outline"
              size={38}
              color="#367fbd"
            />
          </View>

          {/* Greeting */}
          <View style={styles.greetingContainer}>
            <Text style={styles.greeting}>Good Morning</Text>
            <Text style={styles.name}>Jane!</Text>
          </View>

          {/* Today's goal */}
          <View style={styles.goalContainer}>
            <Text style={styles.goalTitle}>Today’s Goal:</Text>
            <Text style={styles.goalText}>
              30 minutes + 5 exercises
            </Text>
          </View>

          {/* Get Started button */}
          <Pressable
            style={({ pressed }) => [
              styles.startButton,
              pressed && styles.startButtonPressed,
            ]}
            onPress={() => {
              router.push("/session");
            }}
          >
            <Text style={styles.startText}>Get Started</Text>

            <Ionicons
              name="chevron-forward-outline"
              size={30}
              color="#4a8bc3"
            />

            <Ionicons
              name="chevron-forward-outline"
              size={30}
              color="#4a8bc3"
              style={styles.secondChevron}
            />
          </Pressable>

        </View>

        {/* Bottom navigation */}
        <View style={styles.bottomNav}>

          {/* Messages */}
          <Pressable
            style={styles.navItem}
            onPress={() => router.push("/messages")}
          >
            <Ionicons
              name="chatbox"
              size={25}
              color="#4a8bc3"
            />
            <Text style={styles.navText}>Messages</Text>
          </Pressable>

          {/* Exercise */}
          <Pressable
            style={styles.navItem}
            onPress={() => router.push("/exercise")}
          >
            <Ionicons
              name="fitness"
              size={27}
              color="#4a8bc3"
            />
            <Text style={styles.navText}>Exercise</Text>
          </Pressable>

          {/* Progress */}
          <Pressable
            style={styles.navItem}
            onPress={() => router.push("/progress")}
          >
            <Ionicons
              name="bar-chart"
              size={27}
              color="#4a8bc3"
            />
            <Text style={styles.navText}>Progress</Text>
          </Pressable>

        </View>

      </LinearGradient>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#ffffff",
  },

  container: {
    flex: 1,
  },

  content: {
    flex: 1,
    alignItems: "center",
    paddingTop: 55,
  },

  logoCircle: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: "#e8f1f8",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },

  greetingContainer: {
    alignItems: "center",
  },

  greeting: {
    fontSize: 25,
    fontWeight: "600",
    color: "#367fbd",
  },

  name: {
    fontSize: 23,
    fontWeight: "400",
    color: "#367fbd",
    marginTop: 2,
  },

  goalContainer: {
    alignItems: "center",
    marginTop: 92,
  },

  goalTitle: {
    fontSize: 23,
    fontWeight: "600",
    color: "#367fbd",
  },

  goalText: {
    fontSize: 16,
    color: "#367fbd",
    marginTop: 2,
  },

  startButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#d7e8f5",
    borderRadius: 30,
    paddingVertical: 10,
    paddingLeft: 25,
    paddingRight: 18,
    marginTop: 88,
    minWidth: 176,
  },

  startButtonPressed: {
    opacity: 0.7,
    transform: [{ scale: 0.98 }],
  },

  startText: {
    fontSize: 18,
    color: "#367fbd",
    marginRight: 4,
  },

  secondChevron: {
    marginLeft: -15,
  },

  bottomNav: {
    height: 68,
    flexDirection: "row",
    backgroundColor: "#d9e8f4",
    borderTopWidth: 1,
    borderTopColor: "#7aaed5",
  },

  navItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRightWidth: 1,
    borderRightColor: "#7aaed5",
  },

  navText: {
    color: "#4a8bc3",
    fontSize: 12,
    marginTop: 3,
  },
});