import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  TextInput,
  Modal,
  Image,
} from "react-native";

import Slider from "@react-native-community/slider";

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

const symptomOptions = [
  "Getting Better",
  "Staying the Same",
  "Getting Worse",
];

type PainRegion = {
  id: string;
  label: string;

  // Invisible clickable area
  left: number;
  top: number;
  width: number;
  height: number;

  // Location where the pink marker appears
  dotX: number;
  dotY: number;
};

/*
 * Your image:
 * 920 x 863
 *
 * LEFT FIGURE  = BACK
 * RIGHT FIGURE = FRONT
 *
 * For the FRONT view, the patient's
 * left side appears on the RIGHT side
 * of the image.
 *
 * For the BACK view, the patient's
 * left side appears on the LEFT side
 * of the image.
 */
const painRegions: PainRegion[] = [
  // =====================================================
  // BACK VIEW - LEFT FIGURE
  // =====================================================

  {
    id: "back-left-shoulder",
    label: "Back - Left Shoulder",
    left: 10,
    top: 16,
    width: 12,
    height: 11,
    dotX: 17,
    dotY: 22,
  },

  {
    id: "back-right-shoulder",
    label: "Back - Right Shoulder",
    left: 25,
    top: 16,
    width: 12,
    height: 11,
    dotX: 31,
    dotY: 22,
  },

  {
    id: "back-left-arm",
    label: "Back - Left Arm",
    left: 1,
    top: 27,
    width: 14,
    height: 23,
    dotX: 8,
    dotY: 38,
  },

  {
    id: "back-right-arm",
    label: "Back - Right Arm",
    left: 35,
    top: 27,
    width: 13,
    height: 23,
    dotX: 41,
    dotY: 38,
  },

  {
    id: "back-upper-back",
    label: "Upper Back",
    left: 16,
    top: 23,
    width: 17,
    height: 16,
    dotX: 25,
    dotY: 31,
  },

  {
    id: "back-lower-back",
    label: "Lower Back",
    left: 16,
    top: 38,
    width: 17,
    height: 14,
    dotX: 25,
    dotY: 45,
  },

  {
    id: "back-left-hip",
    label: "Back - Left Hip",
    left: 11,
    top: 49,
    width: 13,
    height: 13,
    dotX: 18,
    dotY: 56,
  },

  {
    id: "back-right-hip",
    label: "Back - Right Hip",
    left: 25,
    top: 49,
    width: 13,
    height: 13,
    dotX: 32,
    dotY: 56,
  },

  {
    id: "back-left-knee",
    label: "Back - Left Knee",
    left: 11,
    top: 66,
    width: 12,
    height: 13,
    dotX: 17,
    dotY: 73,
  },

  {
    id: "back-right-knee",
    label: "Back - Right Knee",
    left: 26,
    top: 66,
    width: 12,
    height: 13,
    dotX: 32,
    dotY: 73,
  },

  {
    id: "back-left-leg",
    label: "Back - Left Lower Leg",
    left: 10,
    top: 78,
    width: 13,
    height: 18,
    dotX: 17,
    dotY: 86,
  },

  {
    id: "back-right-leg",
    label: "Back - Right Lower Leg",
    left: 26,
    top: 78,
    width: 13,
    height: 18,
    dotX: 33,
    dotY: 86,
  },

  {
    id: "back-left-foot",
    label: "Back - Left Foot",
    left: 5,
    top: 94,
    width: 15,
    height: 6,
    dotX: 13,
    dotY: 97,
  },

  {
    id: "back-right-foot",
    label: "Back - Right Foot",
    left: 27,
    top: 94,
    width: 15,
    height: 6,
    dotX: 34,
    dotY: 97,
  },

  // =====================================================
  // FRONT VIEW - RIGHT FIGURE
  // =====================================================

  {
    id: "front-right-shoulder",
    label: "Front - Right Shoulder",
    left: 59,
    top: 16,
    width: 12,
    height: 11,
    dotX: 66,
    dotY: 22,
  },

  {
    id: "front-left-shoulder",
    label: "Front - Left Shoulder",
    left: 75,
    top: 16,
    width: 12,
    height: 11,
    dotX: 81,
    dotY: 22,
  },

  {
    id: "front-right-arm",
    label: "Front - Right Arm",
    left: 51,
    top: 27,
    width: 14,
    height: 23,
    dotX: 58,
    dotY: 38,
  },

  {
    id: "front-left-arm",
    label: "Front - Left Arm",
    left: 86,
    top: 27,
    width: 13,
    height: 23,
    dotX: 93,
    dotY: 38,
  },

  {
    id: "front-chest",
    label: "Chest",
    left: 66,
    top: 22,
    width: 18,
    height: 16,
    dotX: 75,
    dotY: 30,
  },

  {
    id: "front-abdomen",
    label: "Abdomen",
    left: 66,
    top: 37,
    width: 18,
    height: 15,
    dotX: 75,
    dotY: 44,
  },

  {
    id: "front-right-hip",
    label: "Front - Right Hip",
    left: 61,
    top: 49,
    width: 13,
    height: 13,
    dotX: 68,
    dotY: 56,
  },

  {
    id: "front-left-hip",
    label: "Front - Left Hip",
    left: 76,
    top: 49,
    width: 13,
    height: 13,
    dotX: 82,
    dotY: 56,
  },

  {
    id: "front-right-knee",
    label: "Front - Right Knee",
    left: 61,
    top: 66,
    width: 12,
    height: 13,
    dotX: 68,
    dotY: 73,
  },

  {
    id: "front-left-knee",
    label: "Front - Left Knee",
    left: 76,
    top: 66,
    width: 12,
    height: 13,
    dotX: 82,
    dotY: 73,
  },

  {
    id: "front-right-leg",
    label: "Front - Right Lower Leg",
    left: 60,
    top: 78,
    width: 13,
    height: 18,
    dotX: 67,
    dotY: 86,
  },

  {
    id: "front-left-leg",
    label: "Front - Left Lower Leg",
    left: 76,
    top: 78,
    width: 13,
    height: 18,
    dotX: 83,
    dotY: 86,
  },

  {
    id: "front-right-foot",
    label: "Front - Right Foot",
    left: 56,
    top: 94,
    width: 15,
    height: 6,
    dotX: 64,
    dotY: 97,
  },

  {
    id: "front-left-foot",
    label: "Front - Left Foot",
    left: 78,
    top: 94,
    width: 15,
    height: 6,
    dotX: 86,
    dotY: 97,
  },
];

export default function SurveyScreen() {
  const [symptoms, setSymptoms] = useState("Select One");

  const [symptomModalVisible, setSymptomModalVisible] =
    useState(false);

  const [painLevel, setPainLevel] = useState(0);

  const [selectedPainRegions, setSelectedPainRegions] =
    useState<string[]>([]);

  const [notes, setNotes] = useState("");

  const togglePainRegion = (id: string) => {
    setSelectedPainRegions((current) => {
      if (current.includes(id)) {
        return current.filter((region) => region !== id);
      }

      return [...current, id];
    });
  };

  const submitSurvey = () => {
    console.log({
      symptoms,
      painLevel,
      selectedPainRegions,
      notes,
    });

    router.replace("/exercise");
  };

  return (
    <View style={styles.screen}>
      <View style={styles.screen}>

        {/* ========================================= */}
        {/* HEADER */}
        {/* ========================================= */}

        <View style={styles.header}>

          <Pressable
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Ionicons
              name="arrow-back-circle-outline"
              size={27}
              color="#367FBD"
            />
          </Pressable>

          <Text style={styles.headerTitle}>
            Post-Exercise Survey
          </Text>

        </View>

        {/* ========================================= */}
        {/* CONTENT */}
        {/* ========================================= */}

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >

          {/* ======================================= */}
          {/* SYMPTOMS */}
          {/* ======================================= */}

          <Text style={styles.question}>
            How are your symptoms changing?
          </Text>

          <Pressable
            style={styles.dropdown}
            onPress={() =>
              setSymptomModalVisible(true)
            }
          >
            <Text style={styles.dropdownText}>
              {symptoms}
            </Text>

            <Ionicons
              name="chevron-down"
              size={20}
              color="#222222"
            />
          </Pressable>

          {/* Symptom selector */}
          <Modal
            visible={symptomModalVisible}
            transparent
            animationType="fade"
            onRequestClose={() =>
              setSymptomModalVisible(false)
            }
          >
            <Pressable
              style={styles.modalOverlay}
              onPress={() =>
                setSymptomModalVisible(false)
              }
            >
              <View style={styles.modalCard}>

                <Text style={styles.modalTitle}>
                  How are your symptoms changing?
                </Text>

                {symptomOptions.map((option) => (
                  <Pressable
                    key={option}
                    style={styles.option}
                    onPress={() => {
                      setSymptoms(option);
                      setSymptomModalVisible(false);
                    }}
                  >
                    <Text style={styles.optionText}>
                      {option}
                    </Text>
                  </Pressable>
                ))}

              </View>
            </Pressable>
          </Modal>

          {/* ======================================= */}
          {/* PAIN MAP */}
          {/* ======================================= */}

          <Text style={styles.question}>
            Tap the areas where you are experiencing
            pain.
          </Text>

          <Text style={styles.helperText}>
            You can select more than one area.
          </Text>

          <View style={styles.bodyMapContainer}>

            {/* BACK / FRONT labels */}

            <View
              style={[
                styles.bodyViewLabel,
                { left: "25%" },
              ]}
            >
              <Text style={styles.bodyViewLabelText}>
                BACK
              </Text>
            </View>

            <View
              style={[
                styles.bodyViewLabel,
                { left: "75%" },
              ]}
            >
              <Text style={styles.bodyViewLabelText}>
                FRONT
              </Text>
            </View>

            {/* Body image */}

            <Image
              source={require("../../assets/images/body-map.png")}
              style={styles.bodyMap}
              resizeMode="contain"
            />

            {/* ================================= */}
            {/* INVISIBLE CLICKABLE AREAS */}
            {/* ================================= */}

            {painRegions.map((region) => (
              <Pressable
                key={region.id}
                onPress={() =>
                  togglePainRegion(region.id)
                }
                style={[
                  styles.invisibleHitArea,
                  {
                    left: `${region.left}%`,
                    top: `${region.top}%`,
                    width: `${region.width}%`,
                    height: `${region.height}%`,
                  },
                ]}
              />
            ))}

            {/* ================================= */}
            {/* SELECTED PAIN MARKERS */}
            {/* ================================= */}

            {painRegions.map((region) => {
              const selected =
                selectedPainRegions.includes(
                  region.id
                );

              if (!selected) {
                return null;
              }

              return (
                <View
                  key={`dot-${region.id}`}
                  pointerEvents="none"
                  style={[
                    styles.selectedPainCircle,
                    {
                      left: `${region.dotX}%`,
                      top: `${region.dotY}%`,
                    },
                  ]}
                >
                  <Ionicons
                    name="checkmark"
                    size={14}
                    color="#FFFFFF"
                  />
                </View>
              );
            })}

          </View>

          {/* ======================================= */}
          {/* SELECTED AREAS */}
          {/* ======================================= */}

          {selectedPainRegions.length > 0 && (
            <View style={styles.selectedRegionsBox}>

              <Text style={styles.selectedLabel}>
                Areas selected:
              </Text>

              <Text style={styles.selectedText}>
                {painRegions
                  .filter((region) =>
                    selectedPainRegions.includes(
                      region.id
                    )
                  )
                  .map((region) => region.label)
                  .join(", ")}
              </Text>

            </View>
          )}

          {/* ======================================= */}
          {/* PAIN LEVEL */}
          {/* ======================================= */}

          <Text style={styles.question}>
            Overall Pain
          </Text>

          <Text style={styles.painDescription}>
            0 = no pain, 10 = worst pain
          </Text>

          <View style={styles.sliderContainer}>

            <Slider
              style={styles.slider}
              minimumValue={0}
              maximumValue={10}
              step={1}
              value={painLevel}
              onValueChange={setPainLevel}
              minimumTrackTintColor="#76A9D2"
              maximumTrackTintColor="#D5E7F3"
              thumbTintColor="#76A9D2"
            />

            <View style={styles.sliderLabels}>

              <Text style={styles.sliderNumber}>
                0
              </Text>

              <Text style={styles.sliderCurrent}>
                {painLevel}
              </Text>

              <Text style={styles.sliderNumber}>
                10
              </Text>

            </View>

          </View>

          {/* ======================================= */}
          {/* NOTES */}
          {/* ======================================= */}

          <Text style={styles.question}>
            Additional Notes
          </Text>

          <TextInput
            style={styles.notesInput}
            placeholder="Tell us how you felt during the exercises..."
            placeholderTextColor="#7A7A7A"
            value={notes}
            onChangeText={setNotes}
            multiline
            textAlignVertical="top"
          />

          {/* ======================================= */}
          {/* SUBMIT */}
          {/* ======================================= */}

          <Pressable
            style={({ pressed }) => [
              styles.submitButton,
              pressed && styles.submitPressed,
            ]}
            onPress={submitSurvey}
          >
            <Text style={styles.submitText}>
              Submit Survey
            </Text>

            <Ionicons
              name="checkmark-circle-outline"
              size={24}
              color="#FFFFFF"
            />
          </Pressable>

        </ScrollView>

        {/* ========================================= */}
        {/* BOTTOM NAVIGATION */}
        {/* ========================================= */}

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
    </View>
  );
}


/* =====================================================
   STYLES
===================================================== */

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

  headerTitle: {
    fontSize: 24,
    color: "#367FBD",
    fontWeight: "400",
    textAlign: "center",
    paddingHorizontal: 60,
  },

  /* CONTENT */

  scrollContent: {
    paddingHorizontal: 14,
    paddingTop: 14,
    paddingBottom: 24,
  },

  question: {
    fontSize: 17,
    color: "#111111",
    lineHeight: 25,
    marginBottom: 7,
  },

  helperText: {
    fontSize: 13,
    color: "#666666",
    marginBottom: 9,
  },

  /* DROPDOWN */

  dropdown: {
    backgroundColor: "#D5E7F3",
    borderRadius: 9,
    minHeight: 48,
    paddingHorizontal: 15,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 18,
  },

  dropdownText: {
    fontSize: 15,
    color: "#222222",
  },

  /* MODAL */

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.35)",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 25,
  },

  modalCard: {
    width: "100%",
    backgroundColor: "#FFFFFF",
    borderRadius: 17,
    padding: 20,
  },

  modalTitle: {
    fontSize: 19,
    fontWeight: "600",
    marginBottom: 12,
  },

  option: {
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E5E5",
  },

  optionText: {
    fontSize: 16,
    color: "#222222",
  },

  /* BODY MAP */

  bodyMapContainer: {
    width: "100%",
    aspectRatio: 920 / 863,
    position: "relative",
    backgroundColor: "#FFFFFF",
    marginBottom: 12,
  },

  bodyMap: {
    width: "100%",
    height: "100%",
  },

  /* BACK / FRONT LABELS */

  bodyViewLabel: {
    position: "absolute",
    top: 1,
    transform: [{ translateX: -24 }],
    zIndex: 5,
    backgroundColor: "#D9E8F4",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },

  bodyViewLabelText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#367FBD",
    letterSpacing: 0.5,
  },

  /*
   * Completely invisible clickable area.
   *
   * These are separate from the visible markers,
   * so the patient doesn't see dots before selecting.
   */

  invisibleHitArea: {
    position: "absolute",
    backgroundColor: "transparent",
  },

  /*
   * Pink marker appears ONLY after selection.
   */

  selectedPainCircle: {
    position: "absolute",
    width: 30,
    height: 30,
    marginLeft: -15,
    marginTop: -15,
    borderRadius: 15,
    backgroundColor: "#F725A7",
    borderWidth: 2,
    borderColor: "#FFFFFF",
    alignItems: "center",
    justifyContent: "center",

    shadowColor: "#000000",
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },

  /* SELECTED AREAS */

  selectedRegionsBox: {
    backgroundColor: "#EEF4F8",
    borderRadius: 12,
    padding: 12,
    marginBottom: 15,
  },

  selectedLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#367FBD",
    marginBottom: 3,
  },

  selectedText: {
    fontSize: 14,
    color: "#333333",
    lineHeight: 21,
  },

  /* PAIN */

  painDescription: {
    fontSize: 14,
    color: "#222222",
    marginBottom: 8,
  },

  sliderContainer: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 5,
    marginBottom: 18,
  },

  slider: {
    width: "100%",
    height: 40,
  },

  sliderLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 5,
  },

  sliderNumber: {
    fontSize: 12,
    color: "#333333",
  },

  sliderCurrent: {
    fontSize: 14,
    fontWeight: "600",
    color: "#367FBD",
  },

  /* NOTES */

  notesInput: {
    minHeight: 110,
    borderRadius: 12,
    backgroundColor: "#EEF4F8",
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: "#222222",
    marginBottom: 16,
  },

  /* SUBMIT */

  submitButton: {
    minHeight: 55,
    backgroundColor: "#367FBD",
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
    marginBottom: 8,
  },

  submitPressed: {
    opacity: 0.75,
  },

  submitText: {
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