/** Dashboard state management */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getSummary, getActivity, getSkills } from "../api/endpoints/dashboard";
import type {
  DashboardSummaryResponse,
  DashboardActivityResponse,
  DashboardSkillsResponse,
} from "../types/api";

interface DashboardState {
  summary: DashboardSummaryResponse | null;
  activity: DashboardActivityResponse | null;
  skills: DashboardSkillsResponse | null;
  isLoading: boolean;
  error: string | null;
  loadAll: () => Promise<void>;
}

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set) => ({
      summary: null,
      activity: null,
      skills: null,
      isLoading: false,
      error: null,

      loadAll: async () => {
        set({ isLoading: true, error: null });
        try {
          const [summary, activity, skills] = await Promise.all([
            getSummary(),
            getActivity(),
            getSkills(),
          ]);
          set({ summary, activity, skills, isLoading: false });
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to load dashboard";
          set({ isLoading: false, error: message });
        }
      },
    }),
    {
      name: "dashboard-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        summary: state.summary,
        activity: state.activity,
        skills: state.skills,
      }),
    }
  )
);
