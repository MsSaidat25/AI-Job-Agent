import React from "react";
import { View, Text } from "react-native";
import { STATUS_COLORS } from "../../utils/constants";

interface BadgeProps {
  label: string;
  color?: string;
  status?: string;
}

export function Badge({ label, color, status }: BadgeProps) {
  const bgColor = color ?? (status ? STATUS_COLORS[status] : "#78716C") ?? "#78716C";

  return (
    <View
      className="rounded-full px-3 py-1"
      style={{ backgroundColor: `${bgColor}20` }}
    >
      <Text
        className="text-xs font-semibold"
        style={{ color: bgColor }}
      >
        {label}
      </Text>
    </View>
  );
}
