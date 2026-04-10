/** Chat state management */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { sendMessage, resetChat } from "../api/endpoints/chat";

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

interface ChatState {
  messages: ChatMessage[];
  isTyping: boolean;
  error: string | null;
  send: (text: string) => Promise<void>;
  reset: () => Promise<void>;
  clearLocal: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      isTyping: false,
      error: null,

      send: async (text: string) => {
        const userMsg: ChatMessage = {
          id: generateId(),
          role: "user",
          content: text,
          timestamp: new Date().toISOString(),
        };
        set((s) => ({
          messages: [...s.messages, userMsg],
          isTyping: true,
          error: null,
        }));

        try {
          const response = await sendMessage({ message: text });
          const agentMsg: ChatMessage = {
            id: generateId(),
            role: "agent",
            content: response.response,
            timestamp: new Date().toISOString(),
          };
          set((s) => ({
            messages: [...s.messages, agentMsg],
            isTyping: false,
          }));
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to send message";
          set({ isTyping: false, error: message });
        }
      },

      reset: async () => {
        try {
          await resetChat();
        } catch {
          // Server may not have an active session -- clear locally anyway
        }
        set({ messages: [], error: null });
      },

      clearLocal: () => {
        set({ messages: [], error: null, isTyping: false });
      },
    }),
    {
      name: "chat-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ messages: state.messages }),
    }
  )
);
