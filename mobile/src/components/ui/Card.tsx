import React from "react";
import { View, type ViewProps } from "react-native";
import { useThemeStore } from "../../stores/useThemeStore";

interface CardProps extends ViewProps {
  children: React.ReactNode;
  padded?: boolean;
}

export function Card({ children, padded = true, style, ...props }: CardProps) {
  const colors = useThemeStore((s) => s.colors);

  return (
    <View
      className={`rounded-2xl ${padded ? "p-4" : ""}`}
      style={[
        {
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: colors.border,
        },
        style,
      ]}
      {...props}
    >
      {children}
    </View>
  );
}
