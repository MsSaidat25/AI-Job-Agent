/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        copper: {
          DEFAULT: "#B87333",
          light: "#CD8B4E",
          dark: "#965F2A",
        },
        stone: {
          50: "#FAFAF9",
          100: "#F5F5F4",
          200: "#E7E5E4",
          300: "#D6D3D1",
          400: "#A8A29E",
          500: "#78716C",
          600: "#57534E",
          700: "#44403C",
          800: "#292524",
          900: "#1C1917",
        },
        accent: "#A16207",
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
