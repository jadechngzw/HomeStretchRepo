import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import SettingsButton from "../components/SettingsButton";

type StatusType = "green" | "yellow" | "red";

const statusInfo = {
  green: {
    title: "You're ready to exercise!",
    message:
      "Your recent activity and sensor data look good.",
    color: "#55C878",
    lightColor: "#E4F7E9",
    icon: "checkmark-circle",
  },

  yellow: {
    title: "Let's check your wearable.",
    message:
      "We couldn't fully record your last session. Let's check your wearable before starting.",
    color: "#E8C84A",
    lightColor: "#FFF8D9",
    icon: "warning",
  },

  red: {
    title: "Please check in with your care team.",
    message:
      "Your recent activity or session data needs follow-up before restarting.",
    color: "#E85B68",
    lightColor: "#FFE5E8",
    icon: "alert-circle",
  },
};

export default function AdherenceScreen() {
  const [status, setStatus] =
    useState<StatusType>("green");

  const [missedSessions, setMissedSessions] =
    useState(0);

  const [sensorIssue, setSensorIssue] =
    useState(false);

  const [symptomFlag, setSymptomFlag] =
    useState(false);

  const [difficultSession, setDifficultSession] =
    useState(false);

  /*
   * Prototype simulation:
   *
   * This lets you demonstrate the different
   * green/yellow/red states without having
   * the actual adherence pipeline connected yet.
   */

  const updateStatus = (
    nextStatus: StatusType
  ) => {
    setStatus(nextStatus);

    if (nextStatus === "green") {
      setMissedSessions(0);
      setSensorIssue(false);
      setSymptomFlag(false);
      setDifficultSession(false);
    }

    if (nextStatus === "yellow") {
      setMissedSessions(0);
      setSensorIssue(true);
      setSymptomFlag(false);
      setDifficultSession(false);
    }

    if (nextStatus === "red") {
      setMissedSessions(3);
      setSensorIssue(false);
      setSymptomFlag(true);
      setDifficultSession(false);
    }
  };

  const currentStatus = statusInfo[status];

  const completedSessions =
    Math.max(0, 5 - missedSessions);

  return (
    <View style={styles.screen}>

      <StatusBar style="dark" />

      {/* =========================================
          HEADER
      ========================================= */}

      <View style={styles.header}>

        <SettingsButton />

        <Text style={styles.headerTitle}>
          Readiness
        </Text>

      </View>


      {/* =========================================
          CONTENT
      ========================================= */}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={
          styles.scrollContent
        }
      >

        {/* =======================================
            STATUS CARD
        ======================================= */}

        <View
          style={[
            styles.statusCard,
            {
              backgroundColor:
                currentStatus.lightColor,
            },
          ]}
        >

          {/* Light */}
          <View
            style={[
              styles.statusLight,
              {
                backgroundColor:
                  currentStatus.color,
              },
            ]}
          >
            <Ionicons
              name={currentStatus.icon as any}
              size={48}
              color="#FFFFFF"
            />
          </View>


          <Text style={styles.statusTitle}>
            {currentStatus.title}
          </Text>

          <Text style={styles.statusMessage}>
            {currentStatus.message}
          </Text>

        </View>


        {/* =======================================
            ACTIVITY SUMMARY
        ======================================= */}

        <Text style={styles.sectionTitle}>
          Your Recent Activity
        </Text>

        <View style={styles.summaryCard}>

          <View style={styles.summaryItem}>

            <Text style={styles.summaryNumber}>
              {completedSessions}
            </Text>

            <Text style={styles.summaryLabel}>
              sessions completed
            </Text>

          </View>


          <View style={styles.divider} />


          <View style={styles.summaryItem}>

            <Text style={styles.summaryNumber}>
              {missedSessions}
            </Text>

            <Text style={styles.summaryLabel}>
              missed in a row
            </Text>

          </View>

        </View>


        {/* =======================================
            WHAT WE'RE CHECKING
        ======================================= */}

        <Text style={styles.sectionTitle}>
          What we're checking
        </Text>

        <View style={styles.checkCard}>

          <CheckRow
            label="Following your exercise plan"
            status={
              missedSessions > 0
                ? "warning"
                : "good"
            }
          />

          <CheckRow
            label="Wearable sensor data"
            status={
              sensorIssue
                ? "warning"
                : "good"
            }
          />

          <CheckRow
            label="Symptoms / care team review"
            status={
              symptomFlag
                ? "warning"
                : "good"
            }
          />

          <CheckRow
            label="Recent exercise session"
            status={
              difficultSession
                ? "warning"
                : "good"
            }
          />

        </View>


        {/* =======================================
            ACTION
        ======================================= */}

        {status === "green" && (
          <Pressable
            style={({ pressed }) => [
              styles.startButton,
              pressed &&
                styles.startButtonPressed,
            ]}
            onPress={() =>
              router.push("/exercise")
            }
          >
            <Ionicons
              name="play-circle-outline"
              size={23}
              color="#FFFFFF"
            />

            <Text style={styles.startButtonText}>
              Start Exercise
            </Text>
          </Pressable>
        )}

        {status === "yellow" && (
          <Pressable
            style={({ pressed }) => [
              styles.yellowButton,
              pressed &&
                styles.startButtonPressed,
            ]}
            onPress={() =>
              router.push("/settings")
            }
          >
            <Ionicons
              name="watch-outline"
              size={23}
              color="#FFFFFF"
            />

            <Text style={styles.startButtonText}>
              Check Wearable
            </Text>
          </Pressable>
        )}

        {status === "red" && (
          <Pressable
            style={({ pressed }) => [
              styles.redButton,
              pressed &&
                styles.startButtonPressed,
            ]}
            onPress={() =>
              router.push("/messages")
            }
          >
            <Ionicons
              name="chatbubble-outline"
              size={23}
              color="#FFFFFF"
            />

            <Text style={styles.startButtonText}>
              Contact Care Team
            </Text>
          </Pressable>
        )}


        {/* =======================================
            PROTOTYPE CONTROLS
        ======================================= */}

        <View style={styles.prototypeCard}>

          <Text style={styles.prototypeTitle}>
            Prototype Simulation
          </Text>

          <Text style={styles.prototypeDescription}>
            Simulate the conditions used to test
            the readiness indicator.
          </Text>


          <View style={styles.prototypeButtons}>

            <Pressable
              style={[
                styles.prototypeButton,
                status === "green" &&
                  styles.selectedPrototypeGreen,
              ]}
              onPress={() =>
                updateStatus("green")
              }
            >
              <View
                style={[
                  styles.prototypeDot,
                  {
                    backgroundColor:
                      "#55C878",
                  },
                ]}
              />

              <Text
                style={styles.prototypeButtonText}
              >
                Green
              </Text>
            </Pressable>


            <Pressable
              style={[
                styles.prototypeButton,
                status === "yellow" &&
                  styles.selectedPrototypeYellow,
              ]}
              onPress={() =>
                updateStatus("yellow")
              }
            >
              <View
                style={[
                  styles.prototypeDot,
                  {
                    backgroundColor:
                      "#E8C84A",
                  },
                ]}
              />

              <Text
                style={styles.prototypeButtonText}
              >
                Yellow
              </Text>
            </Pressable>


            <Pressable
              style={[
                styles.prototypeButton,
                status === "red" &&
                  styles.selectedPrototypeRed,
              ]}
              onPress={() =>
                updateStatus("red")
              }
            >
              <View
                style={[
                  styles.prototypeDot,
                  {
                    backgroundColor:
                      "#E85B68",
                  },
                ]}
              />

              <Text
                style={styles.prototypeButtonText}
              >
                Red
              </Text>
            </Pressable>

          </View>

        </View>

      </ScrollView>


      {/* =========================================
          BOTTOM NAVIGATION
      ========================================= */}

      <BottomNavigation />

    </View>
  );
}


/* =====================================================
   CHECK ROW
===================================================== */

function CheckRow({
  label,
  status,
}: {
  label: string;
  status: "good" | "warning";
}) {
  return (
    <View style={styles.checkRow}>

      <Ionicons
        name={
          status === "good"
            ? "checkmark-circle"
            : "warning"
        }
        size={23}
        color={
          status === "good"
            ? "#55A968"
            : "#E0AA27"
        }
      />

      <Text style={styles.checkText}>
        {label}
      </Text>

    </View>
  );
}


/* =====================================================
   BOTTOM NAVIGATION
===================================================== */

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
          size={23}
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
          router.push("/exercise")
        }
      >
        <Ionicons
          name="fitness"
          size={25}
          color="#4A8BC3"
        />

        <Text style={styles.navText}>
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
          size={25}
          color="#4A8BC3"
        />

        <Text style={styles.navText}>
          Progress
        </Text>
      </Pressable>


      {/* Readiness */}
      <Pressable
        style={styles.navItem}
        onPress={() =>
          router.replace("/adherence")
        }
      >
        <Ionicons
          name="shield-checkmark"
          size={24}
          color="#367FBD"
        />

        <Text
          style={[
            styles.navText,
            styles.activeNavText,
          ]}
        >
          Readiness
        </Text>
      </Pressable>

    </View>
  );
}


/* =====================================================
   STYLES
===================================================== */

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
    fontSize: 26,
    fontWeight: "400",
    color: "#367FBD",
  },

  /* CONTENT */

  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 30,
  },

  /* STATUS CARD */

  statusCard: {
    borderRadius: 20,
    paddingHorizontal: 20,
    paddingVertical: 24,
    alignItems: "center",
    marginBottom: 22,
  },

  statusLight: {
    width: 76,
    height: 76,
    borderRadius: 38,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
    shadowColor: "#000000",
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.12,
    shadowRadius: 4,
    elevation: 3,
  },

  statusTitle: {
    fontSize: 21,
    fontWeight: "600",
    color: "#222222",
    textAlign: "center",
    marginBottom: 7,
  },

  statusMessage: {
    fontSize: 15,
    color: "#444444",
    lineHeight: 22,
    textAlign: "center",
  },

  /* SECTION */

  sectionTitle: {
    fontSize: 20,
    fontWeight: "600",
    color: "#222222",
    marginBottom: 9,
  },

  /* SUMMARY */

  summaryCard: {
    backgroundColor: "#EEF4F8",
    borderRadius: 17,
    minHeight: 105,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    marginBottom: 20,
  },

  summaryItem: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 15,
  },

  summaryNumber: {
    fontSize: 30,
    fontWeight: "600",
    color: "#367FBD",
  },

  summaryLabel: {
    fontSize: 12,
    color: "#666666",
    marginTop: 3,
    textAlign: "center",
  },

  divider: {
    width: 1,
    height: 55,
    backgroundColor: "#BFD2E0",
  },

  /* CHECKS */

  checkCard: {
    backgroundColor: "#EEF4F8",
    borderRadius: 17,
    padding: 15,
    marginBottom: 18,
  },

  checkRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },

  checkText: {
    flex: 1,
    fontSize: 14,
    color: "#333333",
    marginLeft: 9,
  },

  /* ACTION BUTTONS */

  startButton: {
    minHeight: 54,
    borderRadius: 16,
    backgroundColor: "#367FBD",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 7,
    marginBottom: 18,
  },

  yellowButton: {
    minHeight: 54,
    borderRadius: 16,
    backgroundColor: "#C6A62E",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 7,
    marginBottom: 18,
  },

  redButton: {
    minHeight: 54,
    borderRadius: 16,
    backgroundColor: "#D45763",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 7,
    marginBottom: 18,
  },

  startButtonPressed: {
    opacity: 0.72,
    transform: [{ scale: 0.99 }],
  },

  startButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },

  /* PROTOTYPE */

  prototypeCard: {
    backgroundColor: "#F5F7F9",
    borderRadius: 17,
    padding: 15,
    marginTop: 4,
    borderWidth: 1,
    borderColor: "#D9E1E8",
  },

  prototypeTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333333",
    marginBottom: 4,
  },

  prototypeDescription: {
    fontSize: 13,
    lineHeight: 19,
    color: "#666666",
    marginBottom: 12,
  },

  prototypeButtons: {
    flexDirection: "row",
    gap: 8,
  },

  prototypeButton: {
    flex: 1,
    minHeight: 42,
    borderRadius: 11,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#D4DCE3",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },

  selectedPrototypeGreen: {
    borderColor: "#55C878",
    borderWidth: 2,
  },

  selectedPrototypeYellow: {
    borderColor: "#E8C84A",
    borderWidth: 2,
  },

  selectedPrototypeRed: {
    borderColor: "#E85B68",
    borderWidth: 2,
  },

  prototypeDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
  },

  prototypeButtonText: {
    fontSize: 13,
    color: "#333333",
    fontWeight: "500",
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
    fontSize: 10,
    marginTop: 3,
    textAlign: "center",
  },

  activeNavText: {
    fontWeight: "600",
  },

});