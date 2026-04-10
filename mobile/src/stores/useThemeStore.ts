/** Theme state management */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { lightTheme, darkTheme, type ThemeColors } from "../utils/theme";

type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  colors: ThemeColors;
  isDark: boolean;
  setMode: (mode: ThemeMode, systemIsDark?: boolean) => void;
  resolveSystemTheme: (systemIsDark: boolean) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: "light" as ThemeMode,
      colors: lightTheme,
      isDark: false,

      setMode: (mode: ThemeMode, systemIsDark = false) => {
        let isDark: boolean;
        if (mode === "system") {
          isDark = systemIsDark;
        } else {
          isDark = mode === "dark";
        }
        set({
          mode,
          isDark,
          colors: isDark ? darkTheme : lightTheme,
        });
      },

      resolveSystemTheme: (systemIsDark: boolean) => {
        set((state) => {
          if (state.mode !== "system") return state;
          return {
            isDark: systemIsDark,
            colors: systemIsDark ? darkTheme : lightTheme,
          };
        });
      },
    }),
    {
      name: "theme-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ mode: state.mode }),
    }
  )
);
