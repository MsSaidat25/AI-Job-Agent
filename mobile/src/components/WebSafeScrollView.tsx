import React from "react";
import { Platform, ScrollView, type ScrollViewProps } from "react-native";

const webStyle = Platform.OS === "web" ? ({ flex: 1, overflow: "auto" } as any) : undefined;

/**
 * ScrollView wrapper that applies the correct web overflow style automatically.
 * Drop-in replacement for ScrollView in screens that run on web.
 */
export function WebSafeScrollView({ style, children, ...props }: ScrollViewProps) {
  return (
    <ScrollView
      style={[{ flex: 1 }, webStyle, style]}
      contentContainerStyle={{ flexGrow: 1 }}
      keyboardShouldPersistTaps="handled"
      {...props}
    >
      {children}
    </ScrollView>
  );
}
