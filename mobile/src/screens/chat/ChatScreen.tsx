import React, { useState, useRef } from "react";
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Card } from "../../components/ui/Card";
import { ScreenWrapper } from "../../components/ScreenWrapper";
import { useChatStore, type ChatMessage } from "../../stores/useChatStore";
import { useThemeStore } from "../../stores/useThemeStore";

const QUICK_ACTIONS = [
  "Search for jobs",
  "My analytics",
  "Application tips",
  "Career advice",
];

export function ChatScreen() {
  const { messages, isTyping, error, send } = useChatStore();
  const colors = useThemeStore((s) => s.colors);
  const [input, setInput] = useState("");
  const listRef = useRef<FlatList>(null);

  async function handleSend(text?: string) {
    const msg = text ?? input.trim();
    if (!msg) return;
    setInput("");
    await send(msg);
  }

  function renderMessage({ item }: { item: ChatMessage }) {
    const isUser = item.role === "user";
    return (
      <View
        className={`mb-3 max-w-[80%] ${isUser ? "self-end" : "self-start"}`}
      >
        <View
          className="rounded-2xl px-4 py-3"
          style={{
            backgroundColor: isUser ? colors.primary : colors.surface,
          }}
        >
          <Text
            className="text-sm"
            style={{ color: isUser ? "#fff" : colors.text }}
          >
            {item.content}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <ScreenWrapper scroll={false}>
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={90}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessage}
          inverted
          contentContainerStyle={{
            paddingHorizontal: 16,
            paddingTop: 16,
          }}
          ListEmptyComponent={
            <View className="items-center justify-center py-20">
              <Text
                className="text-lg font-semibold mb-2"
                style={{ color: colors.text }}
              >
                Chat with your AI Agent
              </Text>
              <Text
                className="text-sm text-center px-8"
                style={{ color: colors.textSecondary }}
              >
                Ask about jobs, get career advice, or request document
                generation.
              </Text>
            </View>
          }
        />

        {isTyping && (
          <View className="px-4 pb-2">
            <Text className="text-xs" style={{ color: colors.textSecondary }}>
              Agent is thinking...
            </Text>
          </View>
        )}

        {error && (
          <View className="px-4 pb-2">
            <Text className="text-xs" style={{ color: colors.error }}>
              Failed to send. Try again.
            </Text>
          </View>
        )}

        {/* Quick actions */}
        {messages.length === 0 && (
          <View className="flex-row flex-wrap gap-2 px-4 pb-2">
            {QUICK_ACTIONS.map((action) => (
              <TouchableOpacity
                key={action}
                onPress={() => handleSend(action)}
                className="rounded-full px-3 py-1.5"
                style={{
                  borderWidth: 1,
                  borderColor: colors.primary,
                }}
                accessibilityRole="button"
                accessibilityLabel={action}
              >
                <Text
                  className="text-xs font-medium"
                  style={{ color: colors.primary }}
                >
                  {action}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Input bar */}
        <View
          className="flex-row items-end px-4 py-3 gap-2"
          style={{
            borderTopWidth: 1,
            borderTopColor: colors.border,
            backgroundColor: colors.background,
          }}
        >
          <TextInput
            className="flex-1 rounded-xl px-4 py-2.5 text-sm"
            style={{
              backgroundColor: colors.surface,
              color: colors.text,
              maxHeight: 100,
            }}
            value={input}
            onChangeText={setInput}
            placeholder="Type a message..."
            placeholderTextColor={colors.textSecondary}
            returnKeyType="send"
            onSubmitEditing={() => handleSend()}
          />
          <TouchableOpacity
            onPress={() => handleSend()}
            disabled={!input.trim() || isTyping}
            className="w-10 h-10 rounded-full items-center justify-center"
            style={{
              backgroundColor: input.trim() ? colors.primary : colors.border,
            }}
            accessibilityRole="button"
            accessibilityLabel="Send message"
            accessibilityState={{ disabled: !input.trim() || isTyping }}
          >
            <Text className="text-white font-bold text-lg">^</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </ScreenWrapper>
  );
}
