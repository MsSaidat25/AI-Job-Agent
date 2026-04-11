import React from "react";
import { View, Text, ScrollView, TouchableOpacity, Platform } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { ResponsiveContainer } from "../../components/layout/ResponsiveContainer";
import { useProfileStore } from "../../stores/useProfileStore";
import { useThemeStore } from "../../stores/useThemeStore";
import type { ProfileStackParamList } from "../../types/navigation";

type Nav = NativeStackNavigationProp<ProfileStackParamList, "Profile">;

const webScrollStyle = Platform.OS === "web" ? ({ flex: 1, overflow: "auto" } as any) : undefined;

export function ProfileScreen() {
  const navigation = useNavigation<Nav>();
  const { profile } = useProfileStore();
  const colors = useThemeStore((s) => s.colors);

  if (!profile) return null;

  return (
    <ResponsiveContainer>
      <ScrollView
        className="flex-1 px-4 pt-4"
        contentContainerStyle={{ flexGrow: 1 }}
        style={webScrollStyle}
      >
        {/* Header */}
        <View className="items-center mb-6">
          <View
            className="w-16 h-16 rounded-full items-center justify-center mb-3"
            style={{ backgroundColor: colors.primary }}
          >
            <Text className="text-xl font-bold text-white">
              {profile.name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </Text>
          </View>
          <Text
            className="text-xl font-bold"
            style={{ color: colors.text }}
          >
            {profile.name}
          </Text>
          <Text
            className="text-sm"
            style={{ color: colors.textSecondary }}
          >
            {profile.email}
          </Text>
          <Text
            className="text-sm"
            style={{ color: colors.textSecondary }}
          >
            {profile.location}
          </Text>
        </View>

        {/* Skills */}
        {profile.skills.length > 0 && (
          <Card>
            <Text
              className="text-sm font-semibold mb-2"
              style={{ color: colors.text }}
            >
              Skills
            </Text>
            <View className="flex-row flex-wrap gap-2">
              {profile.skills.map((skill) => (
                <Badge key={skill} label={skill} color={colors.primary} />
              ))}
            </View>
          </Card>
        )}

        {/* Desired Roles */}
        {profile.desired_roles.length > 0 && (
          <Card style={{ marginTop: 12 }}>
            <Text
              className="text-sm font-semibold mb-2"
              style={{ color: colors.text }}
            >
              Target Roles
            </Text>
            {profile.desired_roles.map((role) => (
              <Text
                key={role}
                className="text-sm mb-1"
                style={{ color: colors.text }}
              >
                {role}
              </Text>
            ))}
          </Card>
        )}

        {/* Info */}
        <Card style={{ marginTop: 12 }}>
          <InfoRow label="Experience" value={`${profile.experience_level} (${profile.years_of_experience} years)`} />
          <InfoRow label="Languages" value={profile.languages.join(", ")} />
          {profile.phone && <InfoRow label="Phone" value={profile.phone} />}
        </Card>

        {/* Settings button */}
        <TouchableOpacity
          onPress={() => navigation.navigate("Settings")}
          className="mt-6 mb-8 items-center"
          accessibilityRole="button"
          accessibilityLabel="Open settings"
        >
          <Text
            className="text-sm font-medium"
            style={{ color: colors.primary }}
          >
            Settings
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </ResponsiveContainer>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  const colors = useThemeStore((s) => s.colors);
  return (
    <View className="flex-row justify-between items-center py-1.5">
      <Text className="text-xs" style={{ color: colors.textSecondary }}>
        {label}
      </Text>
      <Text className="text-sm font-medium" style={{ color: colors.text }}>
        {value}
      </Text>
    </View>
  );
}
