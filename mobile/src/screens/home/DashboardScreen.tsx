import React, { useEffect, useCallback } from "react";
import { View, Text, RefreshControl } from "react-native";
import { WebSafeScrollView } from "../../components/WebSafeScrollView";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";
import { ResponsiveContainer, useBreakpoint } from "../../components/layout/ResponsiveContainer";
import { useDashboardStore } from "../../stores/useDashboardStore";
import { useThemeStore } from "../../stores/useThemeStore";


export function DashboardScreen() {
  const { summary, skills, activity, isLoading, error, loadAll } = useDashboardStore();
  const colors = useThemeStore((s) => s.colors);
  const bp = useBreakpoint();
  const metricMinWidth = bp === "desktop" ? "22%" : "45%";

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const onRefresh = useCallback(() => {
    loadAll();
  }, [loadAll]);

  if (!summary && !isLoading && error) {
    return (
      <ResponsiveContainer>
        <EmptyState
          title="Something went wrong"
          message={error}
          action={<Button title="Retry" onPress={loadAll} variant="secondary" />}
        />
      </ResponsiveContainer>
    );
  }

  if (!summary && !isLoading) {
    return (
      <ResponsiveContainer>
        <EmptyState
          title="Welcome!"
          message="Start searching for jobs to see your dashboard metrics here."
          action={<Button title="Refresh" onPress={loadAll} variant="secondary" />}
        />
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer>
      <WebSafeScrollView
        className="flex-1 px-4 pt-4"
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={onRefresh} />
        }
      >
        {/* Summary Cards */}
        {summary && (
          <View className="flex-row flex-wrap gap-3 mb-4">
            <MetricCard
              label="Applications"
              value={String(summary.total_applications)}
              minWidth={metricMinWidth}
            />
            <MetricCard
              label="Response Rate"
              value={`${Math.round(summary.response_rate)}%`}
              minWidth={metricMinWidth}
            />
            <MetricCard
              label="Interview Rate"
              value={`${Math.round(summary.interview_rate)}%`}
              minWidth={metricMinWidth}
            />
            <MetricCard
              label="Offers"
              value={`${Math.round(summary.offer_rate)}%`}
              minWidth={metricMinWidth}
            />
          </View>
        )}

        {/* Skills Gap */}
        {skills && (
          <Card>
            <Text
              className="text-base font-semibold mb-3"
              style={{ color: colors.text }}
            >
              Skills Match: {Math.round(skills.match_pct)}%
            </Text>
            {skills.gap_skills.length > 0 && (
              <View>
                <Text
                  className="text-xs font-medium mb-2"
                  style={{ color: colors.textSecondary }}
                >
                  Skills to develop:
                </Text>
                <View className="flex-row flex-wrap gap-2">
                  {skills.gap_skills.slice(0, 8).map((skill) => (
                    <View
                      key={skill}
                      className="rounded-full px-3 py-1"
                      style={{ backgroundColor: `${colors.accent}20` }}
                    >
                      <Text
                        className="text-xs font-medium"
                        style={{ color: colors.accent }}
                      >
                        {skill}
                      </Text>
                    </View>
                  ))}
                </View>
              </View>
            )}
          </Card>
        )}

        {/* Activity Feed */}
        {activity && activity.activity.length > 0 && (
          <View className="mt-4 mb-8">
            <Text
              className="text-base font-semibold mb-3"
              style={{ color: colors.text }}
            >
              Recent Activity
            </Text>
            {activity.activity.slice(0, 10).map((item) => (
              <View key={`${item.timestamp}-${item.event}`} className="flex-row items-start gap-3 mb-3">
                <View
                  className="w-2 h-2 rounded-full mt-1.5"
                  style={{ backgroundColor: colors.primary }}
                />
                <View className="flex-1">
                  <Text
                    className="text-sm font-medium"
                    style={{ color: colors.text }}
                  >
                    {item.event}
                  </Text>
                  <Text
                    className="text-xs"
                    style={{ color: colors.textSecondary }}
                  >
                    {item.detail}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        <View className="h-4" />
      </WebSafeScrollView>
    </ResponsiveContainer>
  );
}

function MetricCard({ label, value, minWidth }: { label: string; value: string; minWidth?: string }) {
  const colors = useThemeStore((s) => s.colors);

  return (
    <Card style={{ flex: 1, minWidth: minWidth ?? "45%" }}>
      <Text className="text-2xl font-bold" style={{ color: colors.primary }}>
        {value}
      </Text>
      <Text
        className="text-xs font-medium mt-1"
        style={{ color: colors.textSecondary }}
      >
        {label}
      </Text>
    </Card>
  );
}
