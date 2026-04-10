/** Profile state management */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { postProfile, getProfile } from "../api/endpoints/auth";
import type { ProfileRequest, ProfileResponse } from "../types/api";
import { secureStorage } from "../utils/secureStorage";

interface ProfileState {
  profile: ProfileRequest | null;
  hasProfile: boolean;
  isLoading: boolean;
  error: string | null;
  submitProfile: (profile: ProfileRequest) => Promise<ProfileResponse>;
  loadProfile: () => Promise<void>;
  clearProfile: () => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      profile: null,
      hasProfile: false,
      isLoading: false,
      error: null,

      submitProfile: async (profile: ProfileRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await postProfile(profile);
          set({ profile, hasProfile: true, isLoading: false });
          return response;
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to save profile";
          set({ isLoading: false, error: message });
          throw err;
        }
      },

      loadProfile: async () => {
        set({ isLoading: true, error: null });
        try {
          const profile = await getProfile();
          set({ profile, hasProfile: true, isLoading: false });
        } catch {
          set({ isLoading: false });
        }
      },

      clearProfile: () => {
        set({ profile: null, hasProfile: false });
      },
    }),
    {
      name: "profile-store",
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({
        profile: state.profile,
        hasProfile: state.hasProfile,
      }),
    }
  )
);
