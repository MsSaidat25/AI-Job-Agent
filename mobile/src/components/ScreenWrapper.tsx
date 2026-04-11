import React from "react";
import { Platform, View, type ScrollViewProps } from "react-native";
import { WebSafeScrollView } from "./WebSafeScrollView";
import { SafeAreaView } from "react-native-safe-area-context";
import { useThemeStore } from "../stores/useThemeStore";

interface ScreenWrapperProps {
  children: React.ReactNode;
  /** When true (default), wraps children in a ScrollView. Set to false for screens with FlatList or custom scroll. */
  scroll?: boolean;
  /** Extra props forwarded to the inner ScrollView (ignored when scroll=false). */
  scrollViewProps?: ScrollViewProps;
  /** Override the screen background color. Defaults to theme background. */
  backgroundColor?: string;
}

const MAX_WIDTH = 768;

export function ScreenWrapper({
  children,
  scroll = true,
  scrollViewProps,
  backgroundColor,
}: ScreenWrapperProps) {
  const colors = useThemeStore((s) => s.colors);
  const bg = backgroundColor ?? colors.background;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: bg }}>
      <View
        style={[
          {
            flex: 1,
            width: "100%",
            maxWidth: MAX_WIDTH,
            alignSelf: "center" as const,
          },
          Platform.OS === "web" && { height: "100vh" as unknown as number },
        ]}
      >
        {scroll ? (
          <WebSafeScrollView {...scrollViewProps}>
            {children}
          </WebSafeScrollView>
        ) : (
          <View style={{ flex: 1 }}>{children}</View>
        )}
      </View>
    </SafeAreaView>
  );
}
