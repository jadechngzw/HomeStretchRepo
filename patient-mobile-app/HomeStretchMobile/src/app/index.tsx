import React from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Image,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function HomeScreen() {
  return (
    <View style={styles.screen}>
      <StatusBar style="dark" />

      <LinearGradient
        colors={["#c4dcef", "#f7fafc", "#ffffff"]}
        locations={[0, 0.55, 1]}
        style={styles.container}
      >

        {/* TOP SECTION */}
        <View style={styles.topSection}>

          <Image
            source={require("../../assets/images/logo-blue.png")}
            style={styles.logo}
            resizeMode="contain"
          />

          <View style={styles.greetingContainer}>
            <Text style={styles.greeting}>
              Good Morning
            </Text>

            <Text style={styles.name}>
              Jane!
            </Text>
          </View>

        </View>


        {/* MIDDLE SECTION */}
        <View style={styles.middleSection}>

          <Text style={styles.goalTitle}>
            Today’s Goal:
          </Text>

          <Text style={styles.goalText}>
            30 minutes + 5 exercises
          </Text>

        </View>


        {/* BOTTOM SECTION */}
        <View style={styles.bottomSection}>

          <Pressable
            style={({ pressed }) => [
              styles.startButton,
              pressed && styles.startButtonPressed,
            ]}
            onPress={() => router.push("/exercise")}
          >

            <Text style={styles.startText}>
              Get Started
            </Text>

            <View style={styles.chevrons}>
              <Ionicons
                name="chevron-forward-outline"
                size={28}
                color="#4A8BC3"
              />

              <Ionicons
                name="chevron-forward-outline"
                size={28}
                color="#4A8BC3"
                style={styles.secondChevron}
              />
            </View>

          </Pressable>

        </View>

      </LinearGradient>
    </View>
  );
}


const styles = StyleSheet.create({

  screen: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },

  container: {
    flex: 1,
  },


  /* ==========================
     TOP THIRD
     ========================== */

  topSection: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",

    // Pushes logo/greeting slightly lower
    paddingTop: 65,
  },

  logo: {
    width: 72,
    height: 72,
    marginBottom: 16,
  },

  greetingContainer: {
    alignItems: "center",
  },

  greeting: {
    fontSize: 25,
    fontWeight: "600",
    color: "#367FBD",
  },

  name: {
    fontSize: 23,
    fontWeight: "400",
    color: "#367FBD",
    marginTop: 3,
  },


  /* ==========================
     MIDDLE THIRD
     ========================== */

  middleSection: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
  },

  goalTitle: {
    fontSize: 24,
    fontWeight: "600",
    color: "#367FBD",
    textAlign: "center",
  },

  goalText: {
    fontSize: 17,
    color: "#367FBD",
    textAlign: "center",
    marginTop: 5,
  },


  /* ==========================
     BOTTOM THIRD
     ========================== */

  bottomSection: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",

    // Moves button slightly upward within bottom third
    paddingBottom: 45,
  },

  startButton: {
    minWidth: 190,
    height: 55,
    backgroundColor: "#D7E8F5",
    borderRadius: 30,

    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",

    paddingHorizontal: 24,
  },

  startButtonPressed: {
    opacity: 0.7,
    transform: [{ scale: 0.98 }],
  },

  startText: {
    fontSize: 18,
    color: "#367FBD",
    fontWeight: "500",
    marginRight: 7,
  },

  chevrons: {
    flexDirection: "row",
    alignItems: "center",
  },

  secondChevron: {
    marginLeft: -15,
  },

});