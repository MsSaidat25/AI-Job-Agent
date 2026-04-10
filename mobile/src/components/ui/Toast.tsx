import React, { useEffect, useRef, useCallback } from "react";
import { Animated, Text } from "react-native";
import { useThemeStore } from "../../stores/useThemeStore";

interface ToastProps {
  message: string;
  type?: "success" | "error" | "info";
  visible: boolean;
  onDismiss: () => void;
  duration?: number;
}

export function Toast({
  message,
  type = "info",
  visible,
  onDismiss,
  duration = 3000,
}: ToastProps) {
  const colors = useThemeStore((s) => s.colors);
  const opacity = useRef(new Animated.Value(0)).current;
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
      opacity.stopAnimation();
    };
  }, [opacity]);

  useEffect(() => {
    if (visible) {
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.delay(duration),
        Animated.timing(opacity, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start(() => {
        if (isMounted.current) {
          onDismiss();
        }
      });
    }
  }, [visible, duration, onDismiss, opacity]);

  if (!visible) return null;

  const bgColors = {
    success: colors.success,
    error: colors.error,
    info: colors.primary,
  };

  return (
    <Animated.View
      className="absolute bottom-24 left-4 right-4 rounded-xl px-4 py-3 z-50"
      style={{
        opacity,
        backgroundColor: bgColors[type],
      }}
    >
      <Text className="text-white text-sm font-medium text-center">
        {message}
      </Text>
    </Animated.View>
  );
}
