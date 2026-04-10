import React from "react";
import { View, Text, useColorScheme } from "react-native";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ScreenWrapper } from "../../components/ScreenWrapper";
import { useThemeStore } from "../../stores/useThemeStore";
import { useSessionStore } from "../../stores/useSessionStore";
import { useProfileStore } from "../../stores/useProfileStore";
import { useChatStore } from "../../stores/useChatStore";
import { useJobStore } from "../../stores/useJobStore";
import { useDashboardStore } from "../../stores/useDashboardStore";
import { useApplicationStore } from "../../stores/useApplicationStore";

function isValidApiUrl(url: string): boolean {
  // Allow localhost and 10.0.2.2 for dev, require https for everything else
  if (/^https?:\/\/(localhost|127\.0\.0\.1|10\.0\.2\.2)(:\d+)?/.test(url)) {
    return true;
  }
  return url.startsWith("https://");
}

export function SettingsScreen() {
  const { colors, mode, setMode } = useThemeStore();
  const { apiBaseUrl, setApiBaseUrl, reset: resetSession } = useSessionStore();
  const { clearProfile } = useProfileStore();
  const systemColorScheme = useColorScheme();

  function handleSetApiUrl(url: string) {
    if (url && !isValidApiUrl(url)) {
      return; // Reject non-HTTPS URLs for non-dev hosts
    }
    setApiBaseUrl(url);
  }

  function handleLogout() {
    // Clear all stores to prevent data leakage
    clearProfile();
    useChatStore.getState().clearLocal();
    useJobStore.getState().clear();
    // Reset dashboard and application stores by clearing their persisted data
    useDashboardStore.setState({ summary: null, activity: null, skills: null });
    useApplicationStore.setState({ board: null });
    resetSession();
  }

  return (
    <ScreenWrapper>
      <View className="px-4 pt-4">
        {/* Theme */}
        <Card>
          <Text
            className="text-sm font-semibold mb-3"
            style={{ color: colors.text }}
          >
            Appearance
          </Text>
          <View className="flex-row gap-2">
            {(["light", "dark", "system"] as const).map((m) => (
              <Button
                key={m}
                title={m.charAt(0).toUpperCase() + m.slice(1)}
                onPress={() => setMode(m, systemColorScheme === "dark")}
                variant={mode === m ? "primary" : "secondary"}
                size="sm"
              />
            ))}
          </View>
        </Card>

        {/* API URL */}
        <Card style={{ marginTop: 12 }}>
          <Text
            className="text-sm font-semibold mb-2"
            style={{ color: colors.text }}
          >
            API Server
          </Text>
          <Input
            value={apiBaseUrl}
            onChangeText={handleSetApiUrl}
            placeholder="https://api.example.com"
            autoCapitalize="none"
          />
          <Text
            className="text-xs mt-1"
            style={{ color: colors.textSecondary }}
          >
            HTTPS required for non-local servers
          </Text>
        </Card>

        {/* Logout */}
        <View className="mt-8">
          <Button
            title="Reset Session"
            onPress={handleLogout}
            variant="ghost"
          />
        </View>

        {/* About */}
        <View className="mt-8 items-center mb-8">
          <Text
            className="text-xs"
            style={{ color: colors.textSecondary }}
          >
            Job Agent v1.0.0
          </Text>
          <Text
            className="text-xs"
            style={{ color: colors.textSecondary }}
          >
            Built by AVIEN Solutions
          </Text>
        </View>
      </View>
    </ScreenWrapper>
  );
}
