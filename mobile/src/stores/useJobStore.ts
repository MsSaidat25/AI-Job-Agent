/** Job search state management */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { searchJobs } from "../api/endpoints/jobs";
import type { JobSearchRequest, JobSearchResponse } from "../types/api";

interface JobState {
  searchResults: JobSearchResponse | null;
  filters: JobSearchRequest;
  isSearching: boolean;
  error: string | null;
  search: (filters: JobSearchRequest) => Promise<void>;
  setFilters: (filters: Partial<JobSearchRequest>) => void;
  clear: () => void;
}

const DEFAULT_FILTERS: JobSearchRequest = {
  location_filter: "",
  include_remote: true,
  max_results: 10,
};

export const useJobStore = create<JobState>()(
  persist(
    (set, get) => ({
      searchResults: null,
      filters: DEFAULT_FILTERS,
      isSearching: false,
      error: null,

      search: async (filters: JobSearchRequest) => {
        set({ isSearching: true, error: null, filters });
        try {
          const data = await searchJobs(filters);
          set({ searchResults: data, isSearching: false });
        } catch (err) {
          const message = err instanceof Error ? err.message : "Search failed";
          set({ isSearching: false, error: message });
        }
      },

      setFilters: (partial: Partial<JobSearchRequest>) => {
        set({ filters: { ...get().filters, ...partial } });
      },

      clear: () => {
        set({ searchResults: null, filters: DEFAULT_FILTERS });
      },
    }),
    {
      name: "job-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        searchResults: state.searchResults,
        filters: state.filters,
      }),
    }
  )
);
