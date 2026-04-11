import React from "react";
import { View, Platform, useWindowDimensions, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useThemeStore } from "../../stores/useThemeStore";

export type Breakpoint = "mobile" | "tablet" | "desktop";

const TABLET_MIN = 768;
const DESKTOP_MIN = 1024;

export function useBreakpoint(): Breakpoint {
  const { width } = useWindowDimensions();
  if (Platform.OS !== "web") return "mobile";
  if (width >= DESKTOP_MIN) return "desktop";
  if (width >= TABLET_MIN) return "tablet";
  return "mobile";
}

interface ResponsiveContainerProps {
  children: React.ReactNode;
  maxWidth?: number;
  safeArea?: boolean;
  style?: ViewStyle;
}

export function ResponsiveContainer({
  children,
  maxWidth = 480,
  safeArea = true,
  style,
}: ResponsiveContainerProps) {
  const colors = useThemeStore((s) => s.colors);
  const bp = useBreakpoint();

  const isWide = bp !== "mobile";
  const effectiveMax = bp === "desktop" ? Math.max(maxWidth, 960) : maxWidth;
  const Wrapper = safeArea ? SafeAreaView : View;

  return (
    <Wrapper
      style={[
        { flex: 1, backgroundColor: colors.background },
        isWide && { alignItems: "center" as const },
        style,
      ]}
    >
      <View style={[{ flex: 1, width: "100%" }, isWide && { maxWidth: effectiveMax }]}>
        {children}
      </View>
    </Wrapper>
  );
}
