import React, { useEffect, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  useWindowDimensions,
} from "react-native";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";
import { ScreenWrapper } from "../../components/ScreenWrapper";
import { useApplicationStore } from "../../stores/useApplicationStore";
import { useThemeStore } from "../../stores/useThemeStore";
import { formatRelativeDate } from "../../utils/formatters";

const MAX_CONTENT_WIDTH = 768;

export function KanbanBoardScreen() {
  const { board, isLoading, loadBoard } = useApplicationStore();
  const colors = useThemeStore((s) => s.colors);
  const { width: screenWidth } = useWindowDimensions();
  const constrainedWidth = Math.min(screenWidth, MAX_CONTENT_WIDTH);
  const columnWidth = constrainedWidth - 32; // 16px padding each side

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const onRefresh = useCallback(() => {
    loadBoard();
  }, [loadBoard]);

  if (!board && !isLoading) {
    return (
      <EmptyState
        title="No Applications Yet"
        message="Track your first job application to see it on the board."
        action={<Button title="Refresh" onPress={loadBoard} variant="secondary" />}
      />
    );
  }

  return (
    <ScreenWrapper scroll={false}>
      <ScrollView
        className="flex-1"
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={onRefresh} />
        }
      >
        <ScrollView
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          nestedScrollEnabled
        >
          {board?.columns.map((column) => (
            <View key={column.status} style={{ width: columnWidth }} className="px-4 pt-4">
              <View className="flex-row items-center gap-2 mb-3">
                <View
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: column.color }}
                />
                <Text
                  className="text-sm font-semibold"
                  style={{ color: colors.text }}
                >
                  {column.label}
                </Text>
                <Text
                  className="text-xs"
                  style={{ color: colors.textSecondary }}
                >
                  ({column.cards.length})
                </Text>
              </View>

              {column.cards.map((item) => (
                <View key={item.id} className="mb-2">
                  <Card>
                    <Text
                      className="text-sm font-semibold mb-1"
                      style={{ color: colors.text }}
                      numberOfLines={1}
                    >
                      {item.job_title || "Untitled"}
                    </Text>
                    <Text
                      className="text-xs mb-2"
                      style={{ color: colors.textSecondary }}
                      numberOfLines={1}
                    >
                      {item.company} -- {item.location}
                    </Text>
                    <View className="flex-row items-center justify-between">
                      <Badge label={column.label} color={column.color} />
                      {item.last_updated && (
                        <Text
                          className="text-xs"
                          style={{ color: colors.textSecondary }}
                        >
                          {formatRelativeDate(item.last_updated)}
                        </Text>
                      )}
                    </View>
                    {item.match_score != null && (
                      <Text
                        className="text-xs mt-1 font-medium"
                        style={{ color: colors.accent }}
                      >
                        {Math.round(item.match_score)}% match
                      </Text>
                    )}
                  </Card>
                </View>
              ))}
            </View>
          ))}
        </ScrollView>
      </ScrollView>
    </ScreenWrapper>
  );
}
