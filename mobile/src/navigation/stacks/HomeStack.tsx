import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { DashboardScreen } from "../../screens/home/DashboardScreen";
import type { HomeStackParamList } from "../../types/navigation";
import { useThemeStore } from "../../stores/useThemeStore";

const Stack = createNativeStackNavigator<HomeStackParamList>();

export function HomeStack() {
  const colors = useThemeStore((s) => s.colors);

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: "600" },
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{ title: "Dashboard" }}
      />
    </Stack.Navigator>
  );
}
