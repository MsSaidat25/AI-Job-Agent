/** Theme color tokens for programmatic use (non-Tailwind contexts like charts) */

export const lightTheme = {
  primary: "#B87333",
  secondary: "#78716C",
  background: "#FAFAF9",
  surface: "#F5F5F4",
  text: "#292524",
  textSecondary: "#78716C",
  accent: "#A16207",
  success: "#15803D",
  error: "#DC2626",
  border: "#E7E5E4",
};

export const darkTheme = {
  primary: "#CD8B4E",
  secondary: "#A8A29E",
  background: "#1C1917",
  surface: "#292524",
  text: "#F5F5F4",
  textSecondary: "#A8A29E",
  accent: "#D4A72C",
  success: "#22C55E",
  error: "#EF4444",
  border: "#44403C",
};

export type ThemeColors = typeof lightTheme;
