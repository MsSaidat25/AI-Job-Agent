import React from "react";
import { View, ActivityIndicator, Text } from "react-native";
import { useThemeStore } from "../../stores/useThemeStore";

interface LoadingOverlayProps {
  visible: boolean;
  message?: string;
}

export function LoadingOverlay({ visible, message }: LoadingOverlayProps) {
  const colors = useThemeStore((s) => s.colors);

  if (!visible) return null;

  return (
    <View
      className="absolute inset-0 items-center justify-center z-50"
      style={{ backgroundColor: "rgba(0,0,0,0.4)" }}
    >
      <View
        className="rounded-2xl p-6 items-center"
        style={{ backgroundColor: colors.surface }}
      >
        <ActivityIndicator size="large" color={colors.primary} />
        {message && (
          <Text
            className="mt-3 text-sm font-medium"
            style={{ color: colors.text }}
          >
            {message}
          </Text>
        )}
      </View>
    </View>
  );
}
