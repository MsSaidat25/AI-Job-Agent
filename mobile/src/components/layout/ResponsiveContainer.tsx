import React from "react";
import { View, Platform, useWindowDimensions, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useThemeStore } from "../../stores/useThemeStore";

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
  const { width } = useWindowDimensions();

  const isWide = Platform.OS === "web" || width > 768;
  const Wrapper = safeArea ? SafeAreaView : View;

  return (
    <Wrapper
      style={[
        { flex: 1, backgroundColor: colors.background },
        isWide && { alignItems: "center" as const },
        style,
      ]}
    >
      <View style={[{ flex: 1, width: "100%" }, isWide && { maxWidth }]}>
        {children}
      </View>
    </Wrapper>
  );
}
