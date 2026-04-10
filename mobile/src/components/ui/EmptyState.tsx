import React from "react";
import { View, Text } from "react-native";
import { useThemeStore } from "../../stores/useThemeStore";

interface EmptyStateProps {
  title: string;
  message: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  const colors = useThemeStore((s) => s.colors);

  return (
    <View className="flex-1 items-center justify-center p-8">
      <Text
        className="text-xl font-bold mb-2 text-center"
        style={{ color: colors.text }}
      >
        {title}
      </Text>
      <Text
        className="text-sm text-center mb-6"
        style={{ color: colors.textSecondary }}
      >
        {message}
      </Text>
      {action}
    </View>
  );
}
