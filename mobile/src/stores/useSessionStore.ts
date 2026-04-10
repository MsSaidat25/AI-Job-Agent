/** Session state management -- single source of truth via Zustand persist */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { createNewSession } from "../api/session";
import { DEFAULT_API_BASE_URL } from "../utils/constants";
import { secureStorage } from "../utils/secureStorage";

interface SessionState {
  sessionId: string | null;
  isInitialized: boolean;
  apiBaseUrl: string;
  createSession: () => Promise<void>;
  initialize: () => Promise<void>;
  setApiBaseUrl: (url: string) => void;
  reset: () => Promise<void>;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessionId: null,
      isInitialized: false,
      apiBaseUrl: DEFAULT_API_BASE_URL,

      createSession: async () => {
        try {
          const sessionId = await createNewSession();
          set({ sessionId });
        } catch {
          // Server unreachable -- leave sessionId null, will retry later
        }
      },

      initialize: async () => {
        // Zustand persist rehydrates sessionId automatically.
        // Only create a new session if none was persisted.
        if (!get().sessionId) {
          await get().createSession();
        }
        set({ isInitialized: true });
      },

      setApiBaseUrl: (url: string) => {
        set({ apiBaseUrl: url });
      },

      reset: async () => {
        set({ sessionId: null, isInitialized: false });
        await get().createSession();
        set({ isInitialized: true });
      },
    }),
    {
      name: "session-store",
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({
        sessionId: state.sessionId,
        apiBaseUrl: state.apiBaseUrl,
      }),
      onRehydrateStorage: () => {
        // Called after rehydration completes
        return (_state, error) => {
          if (error) {
            console.warn("Session store rehydration failed:", error);
          }
        };
      },
    }
  )
);
