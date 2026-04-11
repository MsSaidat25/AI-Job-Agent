/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        rose: {
          DEFAULT: "#8C5543",
          light: "#B8806E",
          dark: "#6E4535",
        },
        slate: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
        accent: "#6E4535",
        success: "#15803D",
        error: "#DC2626",
      },
      fontFamily: {
        sans: ["SpaceGrotesk"],
        "space-grotesk": ["SpaceGrotesk"],
      },
    },
  },
  plugins: [],
};
