import React, { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import * as DocumentPicker from "expo-document-picker";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { WebSafeScrollView } from "../../components/WebSafeScrollView";
import { ResponsiveContainer } from "../../components/layout/ResponsiveContainer";
import { parseResume } from "../../api/endpoints/chat";
import { useProfileStore } from "../../stores/useProfileStore";
import { useThemeStore } from "../../stores/useThemeStore";
import type { ProfileStackParamList } from "../../types/navigation";

type Nav = NativeStackNavigationProp<ProfileStackParamList, "Profile">;

const ALLOWED_TYPES = [
  "application/pdf",
  "text/plain",
  "text/csv",
  "text/markdown",
];

export function ProfileScreen() {
  const navigation = useNavigation<Nav>();
  const { profile, submitProfile } = useProfileStore();
  const colors = useThemeStore((s) => s.colors);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function handleResumeUpload() {
    try {
      setUploadError(null);
      const result = await DocumentPicker.getDocumentAsync({
        type: ALLOWED_TYPES,
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;

      const file = result.assets[0];
      if (file.size && file.size > 5_000_000) {
        setUploadError("File too large (max 5 MB).");
        return;
      }

      setUploading(true);
      const parsed = await parseResume({
        uri: file.uri,
        name: file.name ?? "resume",
        type: file.mimeType ?? "text/plain",
      });

      // Merge parsed data into existing profile
      if (profile) {
        await submitProfile({
          ...profile,
          name: parsed.name || profile.name,
          email: parsed.email || profile.email,
          phone: parsed.phone || profile.phone,
          location: parsed.location || profile.location,
          skills: parsed.skills.length > 0 ? parsed.skills : profile.skills,
          desired_roles: parsed.desired_roles.length > 0 ? parsed.desired_roles : profile.desired_roles,
          certifications: parsed.certifications.length > 0 ? parsed.certifications : profile.certifications,
          languages: parsed.languages.length > 0 ? parsed.languages : profile.languages,
          linkedin_url: parsed.linkedin_url || profile.linkedin_url,
          portfolio_url: parsed.portfolio_url || profile.portfolio_url,
        });
      }
    } catch {
      setUploadError("Failed to parse resume. Try a different file.");
    } finally {
      setUploading(false);
    }
  }

  if (!profile) return null;

  return (
    <ResponsiveContainer>
      <WebSafeScrollView className="flex-1 px-4 pt-4">
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

        {/* Resume Upload */}
        <View className="mt-4">
          <Button
            title={uploading ? "Parsing..." : "Upload Resume"}
            onPress={handleResumeUpload}
            variant="secondary"
            loading={uploading}
          />
          {uploadError && (
            <Text
              className="text-xs mt-2 text-center"
              style={{ color: colors.error }}
            >
              {uploadError}
            </Text>
          )}
        </View>

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
      </WebSafeScrollView>
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
