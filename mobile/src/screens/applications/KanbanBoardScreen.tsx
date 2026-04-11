import React, { useEffect, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  useWindowDimensions,
} from "react-native";
import { WebSafeScrollView } from "../../components/WebSafeScrollView";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";
import { ResponsiveContainer, useBreakpoint } from "../../components/layout/ResponsiveContainer";
import { useApplicationStore } from "../../stores/useApplicationStore";
import { useThemeStore } from "../../stores/useThemeStore";
import { formatRelativeDate } from "../../utils/formatters";

const MAX_BOARD_WIDTH = 1024;

export function KanbanBoardScreen() {
  const { board, isLoading, loadBoard } = useApplicationStore();
  const colors = useThemeStore((s) => s.colors);
  const bp = useBreakpoint();
  const { width: screenWidth } = useWindowDimensions();
  // On desktop, show multiple columns side-by-side; on mobile, paginated scroll
  const columnWidth = bp === "desktop"
    ? Math.floor((Math.min(screenWidth, MAX_BOARD_WIDTH) - 48) / 4)
    : Math.min(screenWidth, MAX_BOARD_WIDTH) - 32;

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const onRefresh = useCallback(() => {
    loadBoard();
  }, [loadBoard]);

  if (!board && !isLoading) {
    return (
      <ResponsiveContainer maxWidth={MAX_BOARD_WIDTH}>
        <EmptyState
          title="No Applications Yet"
          message="Track your first job application to see it on the board."
          action={<Button title="Refresh" onPress={loadBoard} variant="secondary" />}
        />
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer maxWidth={MAX_BOARD_WIDTH}>
      <WebSafeScrollView
        className="flex-1"
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={onRefresh} />
        }
      >
        <ScrollView
          horizontal
          pagingEnabled={bp === "mobile"}
          showsHorizontalScrollIndicator={bp !== "mobile"}
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
      </WebSafeScrollView>
    </ResponsiveContainer>
  );
}
