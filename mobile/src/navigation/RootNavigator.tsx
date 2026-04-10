import React, { useEffect, useState } from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { View, ActivityIndicator } from "react-native";
import { MainTabNavigator } from "./MainTabNavigator";
import { WelcomeScreen } from "../screens/onboarding/WelcomeScreen";
import { ProfileSetupScreen } from "../screens/onboarding/ProfileSetupScreen";
import { useSessionStore } from "../stores/useSessionStore";
import { useProfileStore } from "../stores/useProfileStore";
import { useThemeStore } from "../stores/useThemeStore";
import type { RootStackParamList, OnboardingStackParamList } from "../types/navigation";

const RootStack = createNativeStackNavigator<RootStackParamList>();
const OnboardingStack = createNativeStackNavigator<OnboardingStackParamList>();

function OnboardingFlow() {
  const colors = useThemeStore((s) => s.colors);

  return (
    <OnboardingStack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <OnboardingStack.Screen name="Welcome" component={WelcomeScreen} />
      <OnboardingStack.Screen name="ProfileSetup" component={ProfileSetupScreen} />
    </OnboardingStack.Navigator>
  );
}

export function RootNavigator() {
  const { isInitialized, initialize } = useSessionStore();
  const { hasProfile } = useProfileStore();
  const colors = useThemeStore((s) => s.colors);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function boot() {
      await initialize();
      setLoading(false);
    }
    boot();
  }, [initialize]);

  if (loading || !isInitialized) {
    return (
      <View
        className="flex-1 items-center justify-center"
        style={{ backgroundColor: colors.background }}
      >
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <RootStack.Navigator screenOptions={{ headerShown: false }}>
      {hasProfile ? (
        <RootStack.Screen name="Main" component={MainTabNavigator} />
      ) : (
        <RootStack.Screen name="Onboarding" component={OnboardingFlow} />
      )}
    </RootStack.Navigator>
  );
}
