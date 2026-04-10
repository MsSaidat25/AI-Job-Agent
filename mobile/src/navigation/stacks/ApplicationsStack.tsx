import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { KanbanBoardScreen } from "../../screens/applications/KanbanBoardScreen";
import type { ApplicationsStackParamList } from "../../types/navigation";
import { useThemeStore } from "../../stores/useThemeStore";

const Stack = createNativeStackNavigator<ApplicationsStackParamList>();

export function ApplicationsStack() {
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
        name="KanbanBoard"
        component={KanbanBoardScreen}
        options={{ title: "Applications" }}
      />
    </Stack.Navigator>
  );
}
