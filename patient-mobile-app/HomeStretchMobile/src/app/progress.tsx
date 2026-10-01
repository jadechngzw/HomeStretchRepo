import React, { useEffect, useState } from "react";
import SettingsButton from "../components/SettingsButton";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  ActivityIndicator,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import {
  collection,
  getDocs,
} from "firebase/firestore";

import { db } from "../firebase/config";

type Session = {
  id: string;
  num_reps?: number;
  duration_sec?: number;
  num_typical?: number;
  num_atypical?: number;
  classification?: string;
  tremor_level?: string;
  file_name?: string;
};

export default function ProgressScreen() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const snapshot = await getDocs(
        collection(db, "sessions")
      );

      const data: Session[] = [];

      snapshot.forEach((doc) => {
        data.push({
          id: doc.id,
          ...doc.data(),
        } as Session);
      });

      /*
       * Sort by the timestamp contained in the newer
       * HomeStretch filenames.
       *
       * Example:
       * session_20260408T143622_HomeStretch...
       *
       * If a filename does not contain a timestamp,
       * it gets pushed toward the end.
       */
      data.sort((a, b) => {
        const timeA = getFilenameTimestamp(a.file_name);
        const timeB = getFilenameTimestamp(b.file_name);

        return timeB - timeA;
      });

      setSessions(data);
    } catch (error) {
      console.error("Error loading sessions:", error);
    } finally {
      setLoading(false);
    }
  }

  /*
   * Most recent 5 sessions
   */
  const recentSessions = sessions.slice(0, 5);

  /*
   * Weekly summary
   *
   * This currently summarizes the 5 most recent sessions.
   * Later, once uploaded_at exists in Firestore, we can
   * change this to a true calendar-week calculation.
   */
  const totalSessions = recentSessions.length;

  const totalMinutes =
    recentSessions.reduce(
      (sum, session) =>
        sum + (session.duration_sec || 0),
      0
    ) / 60;

  /*
   * Patient-friendly categories.
   *
   * These are intentionally not pulled from filenames.
   */
  const workedOn = [
    "Balance",
    "Walking",
    "Stretching",
    "Strength",
  ];

  /*
   * Simple patient-friendly accomplishments.
   */
  const accomplishments = [
    `Completed ${totalSessions} sessions`,
    `Reached ${totalMinutes.toFixed(0)} minutes of movement`,
    "Kept up with your exercise routine",
  ];

  /*
   * Maximum rep count used to scale the bar chart.
   */
  const maxReps = Math.max(
    ...recentSessions.map(
      (session) => session.num_reps || 0
    ),
    1
  );

  return (
    <View style={styles.screen}>
      <View style={styles.screen}>

        {/* ===================================== */}
        {/* HEADER */}
        {/* ===================================== */}

        <View style={styles.header}>
          <SettingsButton />
          <Text style={styles.headerTitle}>
            Progress
          </Text>
        </View>

        {/* ===================================== */}
        {/* MAIN CONTENT */}
        {/* ===================================== */}

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >

          {/* ===================================== */}
          {/* WEEKLY SUMMARY */}
          {/* ===================================== */}

          <View style={styles.summaryCard}>

            <Text style={styles.summaryTitle}>
              Weekly Summary
            </Text>

            <Text style={styles.encouragement}>
              You’re doing great!
            </Text>

            <Text style={styles.movementLabel}>
              Movement this week:
            </Text>

            {loading ? (
              <ActivityIndicator
                color="#367FBD"
                size="small"
                style={styles.loading}
              />
            ) : (
              <>
                <Text style={styles.movementText}>
                  {totalSessions}{" "}
                  {totalSessions === 1
                    ? "session"
                    : "sessions"}{" "}
                  completed
                </Text>

                <Text style={styles.movementText}>
                  {totalMinutes.toFixed(0)} minutes of movement
                </Text>
              </>
            )}

            {/* ================================= */}
            {/* REP BAR GRAPH */}
            {/* ================================= */}

            <View style={styles.chartCard}>

              <Text style={styles.chartTitle}>
                Reps in Your Last 5 Sessions
              </Text>

              {loading ? (
                <ActivityIndicator
                  color="#367FBD"
                  size="small"
                  style={styles.chartLoading}
                />
              ) : recentSessions.length === 0 ? (
                <Text style={styles.emptyChartText}>
                  No sessions yet
                </Text>
              ) : (
                <View style={styles.chartArea}>

                  {/* Bars */}
                  <View style={styles.barsRow}>

                    {recentSessions
                      .slice()
                      .reverse()
                      .map((session) => {

                        const reps =
                          session.num_reps || 0;

                        const hasAtypical =
                          (session.num_atypical || 0) > 0;

                        const barHeight =
                          Math.max(
                            12,
                            (reps / maxReps) * 130
                          );

                        return (
                          <View
                            key={session.id}
                            style={styles.barColumn}
                          >

                            <Text
                              style={
                                styles.repNumber
                              }
                            >
                              {reps}
                            </Text>

                            <View
                              style={[
                                styles.bar,
                                {
                                  height: barHeight,
                                  backgroundColor:
                                    hasAtypical
                                      ? "#E56B6F"
                                      : "#4A8BC3",
                                },
                              ]}
                            />

                            <Text
                              style={
                                styles.barDate
                              }
                            >
                              {getDateLabel(
                                session.file_name
                              )}
                            </Text>

                          </View>
                        );
                      })}

                  </View>

                </View>
              )}

              {/* Legend */}
              <View style={styles.legend}>

                <View style={styles.legendItem}>
                  <View
                    style={[
                      styles.legendDot,
                      {
                        backgroundColor:
                          "#4A8BC3",
                      },
                    ]}
                  />

                  <Text style={styles.legendText}>
                    Typical session
                  </Text>
                </View>

                <View style={styles.legendItem}>
                  <View
                    style={[
                      styles.legendDot,
                      {
                        backgroundColor:
                          "#E56B6F",
                      },
                    ]}
                  />

                  <Text style={styles.legendText}>
                    Atypical reps detected
                  </Text>
                </View>

              </View>
            </View>

            {/* Caption */}
            <Text style={styles.graphicCaption}>
              Keep moving — every session counts!
            </Text>

          </View>


          {/* ===================================== */}
          {/* WHAT YOU WORKED ON */}
          {/* ===================================== */}

          <View style={styles.section}>

            <Text style={styles.sectionTitle}>
              What you worked on:
            </Text>

            {workedOn.map((item) => (
              <View
                key={item}
                style={styles.activityPill}
              >
                <Text style={styles.activityText}>
                  {item}
                </Text>
              </View>
            ))}

          </View>


          {/* ===================================== */}
          {/* ACCOMPLISHMENTS */}
          {/* ===================================== */}

          <View style={styles.section}>

            <Text style={styles.sectionTitle}>
              Accomplishments:
            </Text>

            {accomplishments.map(
              (item, index) => (
                <View
                  key={index}
                  style={
                    styles.accomplishmentRow
                  }
                >

                  <Ionicons
                    name="checkmark-circle"
                    size={22}
                    color="#367FBD"
                  />

                  <Text
                    style={
                      styles.accomplishmentText
                    }
                  >
                    {item}
                  </Text>

                </View>
              )
            )}

          </View>


          {/* ===================================== */}
          {/* EXERCISE SUMMARY */}
          {/* ===================================== */}

          <View style={styles.section}>

            <Text style={styles.sectionTitle}>
              Exercise Summary:
            </Text>

            {recentSessions.length === 0 ? (

              <Text style={styles.emptyText}>
                No exercise sessions yet.
              </Text>

            ) : (

              recentSessions.map(
                (session) => {

                  const dateLabel =
                    getDateLabel(
                      session.file_name
                    );

                  const hasAtypical =
                    (session.num_atypical || 0) > 0;

                  return (
                    <View
                      key={session.id}
                      style={styles.sessionCard}
                    >

                      {/* Session header */}
                      <View
                        style={
                          styles.sessionHeader
                        }
                      >

                        <Text
                          style={
                            styles.sessionDate
                          }
                        >
                          {dateLabel}
                        </Text>

                        <Text
                          style={[
                            styles.sessionQuality,
                            hasAtypical &&
                              styles.atypicalText,
                          ]}
                        >
                          {hasAtypical
                            ? "Atypical reps"
                            : "Completed"}
                        </Text>

                      </View>


                      {/* Session data */}
                      <View
                        style={styles.sessionInfo}
                      >

                        <View
                          style={styles.sessionStat}
                        >

                          <Text
                            style={
                              styles.sessionValue
                            }
                          >
                            {session.num_reps ??
                              "--"}
                          </Text>

                          <Text
                            style={
                              styles.sessionLabel
                            }
                          >
                            reps
                          </Text>

                        </View>


                        <View
                          style={styles.sessionStat}
                        >

                          <Text
                            style={
                              styles.sessionValue
                            }
                          >
                            {session.duration_sec
                              ? session.duration_sec.toFixed(
                                  1
                                )
                              : "--"}
                          </Text>

                          <Text
                            style={
                              styles.sessionLabel
                            }
                          >
                            sec
                          </Text>

                        </View>


                        <View
                          style={styles.sessionStat}
                        >

                          <Text
                            style={
                              styles.sessionValue
                            }
                          >
                            {session.num_typical ??
                              "--"}
                          </Text>

                          <Text
                            style={
                              styles.sessionLabel
                            }
                          >
                            good reps
                          </Text>

                        </View>

                      </View>

                    </View>
                  );
                }
              )

            )}

          </View>

        </ScrollView>


        {/* ===================================== */}
        {/* BOTTOM NAVIGATION */}
        {/* ===================================== */}

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
              router.push("/exercise")
            }
          >

            <Ionicons
              name="fitness"
              size={27}
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
              router.replace("/progress")
            }
          >

            <Ionicons
              name="bar-chart"
              size={27}
              color="#367FBD"
            />

            <Text
              style={[
                styles.navText,
                styles.activeNavText,
              ]}
            >
              Progress
            </Text>

          </Pressable>

        </View>

      </View>
    </View>
  );
}


/* =========================================
   TIMESTAMP FROM FILENAME
========================================= */

function getFilenameTimestamp(
  fileName: string | undefined
): number {

  if (!fileName) {
    return 0;
  }

  const match = fileName.match(
    /session_(\d{8})T(\d{6})/
  );

  if (!match) {
    return 0;
  }

  const dateString = match[1];
  const timeString = match[2];

  const year = Number(
    dateString.substring(0, 4)
  );

  const month = Number(
    dateString.substring(4, 6)
  ) - 1;

  const day = Number(
    dateString.substring(6, 8)
  );

  const hour = Number(
    timeString.substring(0, 2)
  );

  const minute = Number(
    timeString.substring(2, 4)
  );

  const second = Number(
    timeString.substring(4, 6)
  );

  return new Date(
    year,
    month,
    day,
    hour,
    minute,
    second
  ).getTime();
}


/* =========================================
   READABLE DATE
========================================= */

function getDateLabel(
  fileName: string | undefined
) {

  if (!fileName) {
    return "Session";
  }

  const match = fileName.match(
    /session_(\d{8})T(\d{6})/
  );

  if (!match) {
    return "Session";
  }

  const dateString = match[1];

  const year = Number(
    dateString.substring(0, 4)
  );

  const month = Number(
    dateString.substring(4, 6)
  ) - 1;

  const day = Number(
    dateString.substring(6, 8)
  );

  const date = new Date(
    year,
    month,
    day
  );

  return date.toLocaleDateString(
    "en-US",
    {
      month: "short",
      day: "numeric",
    }
  );
}


/* =========================================
   STYLES
========================================= */

const styles = StyleSheet.create({

  safeArea: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },

  screen: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },

  /* HEADER */

  header: {
    height: 120,
    paddingTop: 55,
    backgroundColor: "#C4DCEF",
    borderBottomWidth: 1,
    borderBottomColor: "#76A9D2",
    alignItems: "center",
    justifyContent: "center",
  },

  headerTitle: {
    fontSize: 27,
    color: "#367FBD",
    fontWeight: "400",
  },

  /* CONTENT */

  scrollContent: {
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 20,
  },

  /* WEEKLY SUMMARY */

  summaryCard: {
    backgroundColor: "#D9E8F4",
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 18,
    marginBottom: 18,
  },

  summaryTitle: {
    textAlign: "center",
    fontSize: 25,
    fontWeight: "400",
    color: "#367FBD",
    marginBottom: 22,
  },

  encouragement: {
    fontSize: 22,
    fontWeight: "600",
    color: "#367FBD",
    marginBottom: 12,
  },

  movementLabel: {
    fontSize: 18,
    fontWeight: "500",
    color: "#111111",
    marginBottom: 6,
  },

  movementText: {
    fontSize: 16,
    color: "#222222",
    marginBottom: 6,
  },

  loading: {
    marginVertical: 15,
  },

  /* CHART */

  chartCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    marginTop: 12,
    paddingTop: 14,
    paddingHorizontal: 10,
    paddingBottom: 10,
  },

  chartTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#222222",
    textAlign: "center",
    marginBottom: 10,
  },

  chartLoading: {
    height: 150,
  },

  chartArea: {
    height: 180,
    justifyContent: "flex-end",
  },

  barsRow: {
    height: 160,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "flex-end",
    paddingHorizontal: 4,
  },

  barColumn: {
    flex: 1,
    height: 160,
    alignItems: "center",
    justifyContent: "flex-end",
  },

  repNumber: {
    fontSize: 12,
    color: "#333333",
    marginBottom: 3,
  },

  bar: {
    width: 30,
    minHeight: 12,
    borderTopLeftRadius: 7,
    borderTopRightRadius: 7,
  },

  barDate: {
    fontSize: 10,
    color: "#555555",
    marginTop: 6,
  },

  legend: {
    flexDirection: "row",
    justifyContent: "center",
    flexWrap: "wrap",
    marginTop: 8,
    gap: 12,
  },

  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 4,
  },

  legendDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    marginRight: 5,
  },

  legendText: {
    fontSize: 10,
    color: "#555555",
  },

  graphicCaption: {
    fontSize: 13,
    fontStyle: "italic",
    color: "#333333",
    marginTop: 10,
  },

  /* SECTIONS */

  section: {
    marginBottom: 18,
  },

  sectionTitle: {
    fontSize: 21,
    fontWeight: "600",
    color: "#111111",
    marginBottom: 10,
  },

  /* WORKED ON */

  activityPill: {
    backgroundColor: "#C9DEEF",
    borderRadius: 18,
    paddingVertical: 9,
    paddingHorizontal: 14,
    marginBottom: 9,
  },

  activityText: {
    fontSize: 16,
    color: "#111111",
  },

  /* ACCOMPLISHMENTS */

  accomplishmentRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
    paddingHorizontal: 4,
  },

  accomplishmentText: {
    flex: 1,
    fontSize: 15,
    color: "#222222",
    marginLeft: 8,
  },

  /* EXERCISE SUMMARY */

  emptyText: {
    fontSize: 15,
    color: "#888888",
  },

  emptyChartText: {
    textAlign: "center",
    color: "#888888",
    paddingVertical: 60,
  },

  sessionCard: {
    backgroundColor: "#EEF4F8",
    borderRadius: 15,
    padding: 14,
    marginBottom: 10,
  },

  sessionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },

  sessionDate: {
    fontSize: 16,
    fontWeight: "600",
    color: "#111111",
  },

  sessionQuality: {
    fontSize: 13,
    color: "#367FBD",
  },

  atypicalText: {
    color: "#D94B50",
    fontWeight: "600",
  },

  sessionInfo: {
    flexDirection: "row",
    justifyContent: "space-around",
  },

  sessionStat: {
    alignItems: "center",
  },

  sessionValue: {
    fontSize: 20,
    fontWeight: "600",
    color: "#367FBD",
  },

  sessionLabel: {
    fontSize: 12,
    color: "#666666",
    marginTop: 2,
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
    fontSize: 12,
    color: "#4A8BC3",
    marginTop: 3,
  },

  activeNavText: {
    fontWeight: "600",
  },

});