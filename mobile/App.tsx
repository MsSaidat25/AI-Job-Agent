import "./global.css";
import React, { useEffect, useState } from "react";
import { useColorScheme, Platform } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import * as Font from "expo-font";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { useThemeStore } from "./src/stores/useThemeStore";

export default function App() {
  const { isDark, resolveSystemTheme } = useThemeStore();
  const systemColorScheme = useColorScheme();
  const [fontsReady, setFontsReady] = useState(false);

  useEffect(() => {
    resolveSystemTheme(systemColorScheme === "dark");
  }, [systemColorScheme, resolveSystemTheme]);

  useEffect(() => {
    async function loadFonts() {
      try {
        await Font.loadAsync({
          SpaceGrotesk: require("./src/assets/fonts/SpaceGrotesk-Regular.ttf"),
          "SpaceGrotesk-Medium": require("./src/assets/fonts/SpaceGrotesk-Medium.ttf"),
          "SpaceGrotesk-Bold": require("./src/assets/fonts/SpaceGrotesk-Bold.ttf"),
        });
      } catch {
        // Fonts failed to load -- continue with system font
      }
      setFontsReady(true);
    }
    loadFonts();
  }, []);

  // On native, wait for fonts. On web, render immediately (fonts load async via CSS).
  if (!fontsReady && Platform.OS !== "web") {
    return null;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <NavigationContainer>
        <StatusBar style={isDark ? "light" : "dark"} />
        <RootNavigator />
      </NavigationContainer>
    </GestureHandlerRootView>
  );
}
