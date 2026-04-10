import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ProfileScreen } from "../../screens/profile/ProfileScreen";
import { SettingsScreen } from "../../screens/profile/SettingsScreen";
import type { ProfileStackParamList } from "../../types/navigation";
import { useThemeStore } from "../../stores/useThemeStore";

const Stack = createNativeStackNavigator<ProfileStackParamList>();

export function ProfileStack() {
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
        name="Profile"
        component={ProfileScreen}
        options={{ title: "Profile" }}
      />
      <Stack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ title: "Settings" }}
      />
    </Stack.Navigator>
  );
}
