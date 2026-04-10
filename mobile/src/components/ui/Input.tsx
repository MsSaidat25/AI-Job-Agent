import React from "react";
import { View, TextInput, Text, type TextInputProps } from "react-native";
import { useThemeStore } from "../../stores/useThemeStore";

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
}

export function Input({ label, error, style, ...props }: InputProps) {
  const colors = useThemeStore((s) => s.colors);

  return (
    <View className="mb-3">
      {label && (
        <Text
          className="text-sm font-medium mb-1.5"
          style={{ color: colors.textSecondary }}
        >
          {label}
        </Text>
      )}
      <TextInput
        className="rounded-xl px-4 py-3 text-base"
        style={[
          {
            backgroundColor: colors.surface,
            borderWidth: 1,
            borderColor: error ? colors.error : colors.border,
            color: colors.text,
          },
          style,
        ]}
        placeholderTextColor={colors.textSecondary}
        {...props}
      />
      {error && (
        <Text className="text-xs mt-1" style={{ color: colors.error }}>
          {error}
        </Text>
      )}
    </View>
  );
}
