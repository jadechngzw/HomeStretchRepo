import React, { useState } from "react";
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
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(
    null
  );

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
      text,
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
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      {/* Header */}
      <View style={styles.header}>
        {selectedProvider ? (
          <>
            <Pressable
              style={styles.backButton}
              onPress={() => setSelectedProvider(null)}
            >
              <Ionicons
                name="arrow-back-circle-outline"
                size={31}
                color="#4A8BC3"
              />
            </Pressable>

            <Text style={styles.headerTitle}>
              {selectedProvider.name}
            </Text>
          </>
        ) : (
          <Text style={styles.headerTitle}>Messages</Text>
        )}
      </View>

      {/* Main content */}
      {!selectedProvider ? (
        <View style={styles.listContainer}>
          {providers.map((provider) => (
            <Pressable
              key={provider.id}
              style={({ pressed }) => [
                styles.providerCard,
                pressed && styles.providerPressed,
              ]}
              onPress={() => setSelectedProvider(provider)}
            >
              <View>
                <Text style={styles.providerName}>{provider.name}</Text>
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
          <ScrollView
            style={styles.messageList}
            contentContainerStyle={styles.messageContent}
            showsVerticalScrollIndicator={false}
          >
            {messages[selectedProvider.id]?.length === 0 ? (
              <View style={styles.emptyChat}>
                <Text style={styles.emptyText}>
                  Send a message to your care team.
                </Text>
              </View>
            ) : (
              messages[selectedProvider.id].map((message) => (
                <View
                  key={message.id}
                  style={[
                    styles.messageBubble,
                    message.sender === "patient"
                      ? styles.patientMessage
                      : styles.providerMessage,
                  ]}
                >
                  <Text style={styles.messageText}>{message.text}</Text>
                </View>
              ))
            )}
          </ScrollView>

          {/* Message input */}
          <View style={styles.inputRow}>
            <TextInput
              value={messageText}
              onChangeText={setMessageText}
              placeholder="Send Message..."
              placeholderTextColor="#4A8BC3"
              style={styles.messageInput}
              multiline
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
                size={28}
                color="#4A8BC3"
              />
            </Pressable>
          </View>
        </View>
      )}

      {/* Bottom navigation */}
      <View style={styles.bottomNav}>
        <Pressable style={styles.navItem}>
          <Ionicons name="chatbox" size={25} color="#4A8BC3" />
          <Text style={styles.navText}>Messages</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
          <Ionicons name="fitness" size={27} color="#4A8BC3" />
          <Text style={styles.navText}>Exercise</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
          <Ionicons name="bar-chart" size={27} color="#4A8BC3" />
          <Text style={styles.navText}>Progress</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },

  header: {
    height: 100,
    backgroundColor: "#C4DCEF",
    borderBottomWidth: 1,
    borderBottomColor: "#76A9D2",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },

  headerTitle: {
    color: "#367FBD",
    fontSize: 27,
    fontWeight: "400",
  },

  backButton: {
    position: "absolute",
    left: 16,
    top: 34,
  },

  listContainer: {
    flex: 1,
    paddingHorizontal: 15,
    paddingTop: 12,
  },

  providerCard: {
    minHeight: 70,
    backgroundColor: "#C9DEEF",
    borderRadius: 17,
    marginBottom: 12,
    paddingHorizontal: 15,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  providerPressed: {
    opacity: 0.7,
    transform: [{ scale: 0.99 }],
  },

  providerName: {
    fontSize: 18,
    color: "#111111",
    fontWeight: "500",
  },

  providerSubtitle: {
    fontSize: 14,
    color: "#222222",
    marginTop: 2,
  },

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
    paddingTop: 15,
    paddingBottom: 15,
  },

  emptyChat: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  emptyText: {
    color: "#B5B5B5",
    fontSize: 16,
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
  },

  providerMessage: {
    alignSelf: "flex-start",
    backgroundColor: "#E8EFF5",
  },

  messageText: {
    fontSize: 16,
    color: "#222222",
  },

  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 10,
    gap: 8,
  },

  messageInput: {
    flex: 1,
    minHeight: 48,
    maxHeight: 100,
    backgroundColor: "#D5E7F3",
    borderRadius: 25,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: "#222222",
    fontSize: 16,
  },

  sendButton: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },

  sendPressed: {
    opacity: 0.6,
    transform: [{ scale: 0.92 }],
  },

  bottomNav: {
    height: 68,
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
});