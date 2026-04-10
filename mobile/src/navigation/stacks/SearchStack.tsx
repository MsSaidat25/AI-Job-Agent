import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { JobSearchScreen } from "../../screens/search/JobSearchScreen";
import type { SearchStackParamList } from "../../types/navigation";
import { useThemeStore } from "../../stores/useThemeStore";

const Stack = createNativeStackNavigator<SearchStackParamList>();

export function SearchStack() {
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
        name="JobSearch"
        component={JobSearchScreen}
        options={{ title: "Search Jobs" }}
      />
    </Stack.Navigator>
  );
}
