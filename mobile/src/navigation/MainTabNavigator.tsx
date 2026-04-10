import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { HomeStack } from "./stacks/HomeStack";
import { SearchStack } from "./stacks/SearchStack";
import { ApplicationsStack } from "./stacks/ApplicationsStack";
import { ChatStack } from "./stacks/ChatStack";
import { ProfileStack } from "./stacks/ProfileStack";
import { useThemeStore } from "../stores/useThemeStore";

const Tab = createBottomTabNavigator();

const TAB_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  Home: "grid-outline",
  Search: "search-outline",
  Apps: "albums-outline",
  Chat: "chatbubble-outline",
  Profile: "person-outline",
};

const TAB_ICONS_FOCUSED: Record<string, keyof typeof Ionicons.glyphMap> = {
  Home: "grid",
  Search: "search",
  Apps: "albums",
  Chat: "chatbubble",
  Profile: "person",
};

export function MainTabNavigator() {
  const colors = useThemeStore((s) => s.colors);
  const insets = useSafeAreaInsets();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          paddingBottom: Math.max(insets.bottom, 8),
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
        tabBarIcon: ({ focused, color, size }) => {
          const iconName = focused
            ? TAB_ICONS_FOCUSED[route.name]
            : TAB_ICONS[route.name];
          return (
            <Ionicons
              name={iconName ?? "ellipse-outline"}
              size={size}
              color={color}
            />
          );
        },
        tabBarAccessibilityLabel: `${route.name} tab`,
      })}
    >
      <Tab.Screen name="Home" component={HomeStack} />
      <Tab.Screen name="Search" component={SearchStack} />
      <Tab.Screen name="Apps" component={ApplicationsStack} />
      <Tab.Screen name="Chat" component={ChatStack} />
      <Tab.Screen name="Profile" component={ProfileStack} />
    </Tab.Navigator>
  );
}
