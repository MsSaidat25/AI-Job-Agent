import React from "react";
import { TouchableOpacity, Text, ActivityIndicator, View } from "react-native";
import { useThemeStore } from "../../stores/useThemeStore";

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
}

export function Button({
  title,
  onPress,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  icon,
}: ButtonProps) {
  const colors = useThemeStore((s) => s.colors);

  const sizeStyles = {
    sm: "px-3 py-1.5",
    md: "px-5 py-3",
    lg: "px-7 py-4",
  };

  const textSize = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg",
  };

  const variantStyles = {
    primary: {
      bg: { backgroundColor: colors.primary },
      text: "text-white font-semibold",
    },
    secondary: {
      bg: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
      text: `font-medium`,
    },
    ghost: {
      bg: { backgroundColor: "transparent" },
      text: `font-medium`,
    },
  };

  const style = variantStyles[variant];

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      className={`rounded-xl flex-row items-center justify-center ${sizeStyles[size]}`}
      style={[
        style.bg,
        (disabled || loading) && { opacity: 0.5 },
      ]}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: disabled || loading }}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === "primary" ? "#fff" : colors.primary}
        />
      ) : (
        <View className="flex-row items-center gap-2">
          {icon}
          <Text
            className={`${style.text} ${textSize[size]}`}
            style={{ color: variant === "primary" ? "#fff" : colors.text }}
          >
            {title}
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );
}
