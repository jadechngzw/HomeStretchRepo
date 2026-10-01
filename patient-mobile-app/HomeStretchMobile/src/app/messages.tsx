import React, { useState } from "react";
import SettingsButton from "../components/SettingsButton";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

type Provider = {
  id: string;
  name: string;
  subtitle: string;
};

type Message = {
  id: number;
  sender: "patient" | "provider";
  text: string;
};

const providers: Provider[] = [
  {
    id: "cindy",
    name: "Dr. Cindy Sullivan",
    subtitle: "Your Primary Provider",
  },
  {
    id: "john",
    name: "Dr. John Doe, PT",
    subtitle: "Your Primary PT",
  },
];

export default function MessagesScreen() {
  const [selectedProvider, setSelectedProvider] =
    useState<Provider | null>(null);

  const [messageText, setMessageText] = useState("");

  const [messages, setMessages] = useState<Record<string, Message[]>>({
    cindy: [],
    john: [],
  });

  const sendMessage = () => {
    const text = messageText.trim();

    if (!text || !selectedProvider) {
      return;
    }

    const newMessage: Message = {
      id: Date.now(),
      sender: "patient",
      text: text,
    };

    setMessages((previous) => ({
      ...previous,
      [selectedProvider.id]: [
        ...(previous[selectedProvider.id] || []),
        newMessage,
      ],
    }));

    setMessageText("");
  };

  return (
    <View style={styles.screen}>
      <KeyboardAvoidingView
        style={styles.screen}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {/* HEADER */}
        <View style={styles.header}>
          <SettingsButton color="#367FBD" />
          {selectedProvider ? (
            <>
              <Pressable
                style={styles.backButton}
                onPress={() => setSelectedProvider(null)}
              >
                <Ionicons
                  name="arrow-back-circle-outline"
                  size={29}
                  color="#367FBD"
                />
              </Pressable>

              <Text style={styles.headerTitle}>
                {selectedProvider.name}
              </Text>
            </>
          ) : (
            <Text style={styles.headerTitle}>
              Messages
            </Text>
          )}
        </View>

        {/* MAIN CONTENT */}
        {!selectedProvider ? (
          <View style={styles.listContainer}>
            {providers.map((provider) => (
              <Pressable
                key={provider.id}
                style={({ pressed }) => [
                  styles.providerCard,
                  pressed && styles.providerPressed,
                ]}
                onPress={() =>
                  setSelectedProvider(provider)
                }
              >
                <View style={styles.providerInfo}>
                  <Text style={styles.providerName}>
                    {provider.name}
                  </Text>

                  <Text style={styles.providerSubtitle}>
                    {provider.subtitle}
                  </Text>
                </View>

                <Ionicons
                  name="chevron-forward-outline"
                  size={30}
                  color="#4A8BC3"
                />
              </Pressable>
            ))}
          </View>
        ) : (
          <View style={styles.chatContainer}>
            {/* MESSAGE HISTORY */}
            <ScrollView
              style={styles.messageList}
              contentContainerStyle={styles.messageContent}
              showsVerticalScrollIndicator={false}
              keyboardShouldPersistTaps="handled"
            >
              {messages[selectedProvider.id]?.length === 0 ? (
                <View style={styles.emptyChat}>
                  <Ionicons
                    name="chatbubble-outline"
                    size={42}
                    color="#B5B5B5"
                  />

                  <Text style={styles.emptyText}>
                    No messages yet
                  </Text>

                  <Text style={styles.emptySubtext}>
                    Send a message to your care team.
                  </Text>
                </View>
              ) : (
                messages[selectedProvider.id].map(
                  (message) => (
                    <View
                      key={message.id}
                      style={[
                        styles.messageBubble,
                        message.sender === "patient"
                          ? styles.patientMessage
                          : styles.providerMessage,
                      ]}
                    >
                      <Text style={styles.messageText}>
                        {message.text}
                      </Text>
                    </View>
                  )
                )
              )}
            </ScrollView>

            {/* MESSAGE INPUT */}
            <View style={styles.inputRow}>
              <TextInput
                value={messageText}
                onChangeText={setMessageText}
                placeholder="Send Message..."
                placeholderTextColor="#6A9BC3"
                style={styles.messageInput}
                multiline
                textAlignVertical="center"
              />

              <Pressable
                style={({ pressed }) => [
                  styles.sendButton,
                  pressed && styles.sendPressed,
                ]}
                onPress={sendMessage}
              >
                <Ionicons
                  name="paper-plane"
                  size={25}
                  color="#4A8BC3"
                />
              </Pressable>
            </View>
          </View>
        )}

        {/* BOTTOM NAVIGATION */}
        <View style={styles.bottomNav}>
          {/* Messages */}
          <Pressable
            style={styles.navItem}
            onPress={() =>
              router.replace("/messages")
            }
          >
            <Ionicons
              name="chatbox"
              size={25}
              color="#367FBD"
            />

            <Text
              style={[
                styles.navText,
                styles.activeNavText,
              ]}
            >
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
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },

  /* =========================
     HEADER
     ========================= */

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
    paddingHorizontal: 60,
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

  /* =========================
     PROVIDER LIST
     ========================= */

  listContainer: {
    flex: 1,
    paddingHorizontal: 15,
    paddingTop: 14,
  },

  providerCard: {
    minHeight: 72,
    backgroundColor: "#C9DEEF",
    borderRadius: 17,
    marginBottom: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  providerPressed: {
    opacity: 0.7,
    transform: [{ scale: 0.99 }],
  },

  providerInfo: {
    flex: 1,
    paddingRight: 10,
  },

  providerName: {
    fontSize: 18,
    color: "#111111",
    fontWeight: "500",
  },

  providerSubtitle: {
    fontSize: 14,
    color: "#333333",
    marginTop: 3,
  },

  /* =========================
     CHAT
     ========================= */

  chatContainer: {
    flex: 1,
  },

  messageList: {
    flex: 1,
    paddingHorizontal: 15,
  },

  messageContent: {
    flexGrow: 1,
    justifyContent: "flex-end",
    paddingTop: 16,
    paddingBottom: 12,
  },

  emptyChat: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 30,
  },

  emptyText: {
    color: "#999999",
    fontSize: 17,
    fontWeight: "500",
    marginTop: 12,
  },

  emptySubtext: {
    color: "#B5B5B5",
    fontSize: 14,
    marginTop: 5,
    textAlign: "center",
  },

  messageBubble: {
    maxWidth: "78%",
    paddingHorizontal: 15,
    paddingVertical: 11,
    borderRadius: 15,
    marginBottom: 10,
  },

  patientMessage: {
    alignSelf: "flex-end",
    backgroundColor: "#C9DEEF",
    borderBottomRightRadius: 5,
  },

  providerMessage: {
    alignSelf: "flex-start",
    backgroundColor: "#E8EFF5",
    borderBottomLeftRadius: 5,
  },

  messageText: {
    fontSize: 16,
    color: "#222222",
    lineHeight: 22,
  },

  /* =========================
     MESSAGE INPUT
     ========================= */

  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 10,
    backgroundColor: "#FFFFFF",
  },

  messageInput: {
    flex: 1,
    minHeight: 48,
    maxHeight: 100,
    backgroundColor: "#D5E7F3",
    borderRadius: 25,
    paddingHorizontal: 17,
    paddingVertical: 11,
    color: "#222222",
    fontSize: 16,
  },

  sendButton: {
    width: 48,
    height: 48,
    marginLeft: 7,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#D5E7F3",
  },

  sendPressed: {
    opacity: 0.6,
    transform: [{ scale: 0.92 }],
  },

  /* =========================
     BOTTOM NAV
     ========================= */

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