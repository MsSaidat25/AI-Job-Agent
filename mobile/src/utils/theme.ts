/** Theme color tokens for programmatic use (non-Tailwind contexts like charts) */

export const lightTheme = {
  primary: "#8C5543",
  secondary: "#64748B",
  background: "#f8fafc",
  surface: "#f1f5f9",
  text: "#0f172a",
  textSecondary: "#64748B",
  accent: "#6E4535",
  success: "#15803D",
  error: "#DC2626",
  border: "#e2e8f0",
};

export const darkTheme = {
  primary: "#8C5543",
  secondary: "#94a3b8",
  background: "#0f172a",
  surface: "#1e293b",
  text: "#f1f5f9",
  textSecondary: "#94a3b8",
  accent: "#B8806E",
  success: "#22C55E",
  error: "#EF4444",
  border: "#334155",
};

export type ThemeColors = typeof lightTheme;
