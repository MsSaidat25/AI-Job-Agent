import React from "react";
import { View, Text } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { Button } from "../../components/ui/Button";
import { ScreenWrapper } from "../../components/ScreenWrapper";
import { useThemeStore } from "../../stores/useThemeStore";
import type { OnboardingStackParamList } from "../../types/navigation";

type Nav = NativeStackNavigationProp<OnboardingStackParamList, "Welcome">;

export function WelcomeScreen() {
  const navigation = useNavigation<Nav>();
  const colors = useThemeStore((s) => s.colors);

  return (
    <ScreenWrapper>
      <View className="flex-1 justify-center items-center px-8">
        {/* Logo area */}
        <View
          className="w-20 h-20 rounded-2xl items-center justify-center mb-6"
          style={{ backgroundColor: colors.primary }}
        >
          <Text className="text-3xl font-bold text-white">JA</Text>
        </View>

        <Text
          className="text-3xl font-bold text-center mb-3"
          style={{ color: colors.text }}
        >
          Job Agent
        </Text>

        <Text
          className="text-base text-center mb-2"
          style={{ color: colors.textSecondary }}
        >
          Your AI-powered career companion
        </Text>

        <Text
          className="text-sm text-center mb-12 px-4"
          style={{ color: colors.textSecondary }}
        >
          Search jobs, generate tailored resumes, track applications, and get
          personalized career advice -- all in one place.
        </Text>

        {/* Feature highlights */}
        <View className="w-full mb-12 gap-4">
          <FeatureRow
            iconName="search-outline"
            title="Smart Job Search"
            desc="AI-matched listings with compatibility scores"
          />
          <FeatureRow
            iconName="document-text-outline"
            title="Document Generation"
            desc="Tailored resumes and cover letters in seconds"
          />
          <FeatureRow
            iconName="clipboard-outline"
            title="Application Tracking"
            desc="Kanban board to manage your pipeline"
          />
        </View>

        <Button
          title="Get Started"
          onPress={() => navigation.navigate("ProfileSetup", {})}
          size="lg"
        />
      </View>
    </ScreenWrapper>
  );
}

function FeatureRow({
  iconName,
  title,
  desc,
}: {
  iconName: keyof typeof Ionicons.glyphMap;
  title: string;
  desc: string;
}) {
  const colors = useThemeStore((s) => s.colors);

  return (
    <View className="flex-row items-center gap-4">
      <View
        className="w-10 h-10 rounded-xl items-center justify-center"
        style={{ backgroundColor: `${colors.primary}20` }}
      >
        <Ionicons name={iconName} size={20} color={colors.primary} />
      </View>
      <View className="flex-1">
        <Text className="text-sm font-semibold" style={{ color: colors.text }}>
          {title}
        </Text>
        <Text className="text-xs" style={{ color: colors.textSecondary }}>
          {desc}
        </Text>
      </View>
    </View>
  );
}
