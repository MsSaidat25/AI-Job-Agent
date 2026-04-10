import React, { useState } from "react";
import { View, Text, FlatList, Switch } from "react-native";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { ScreenWrapper } from "../../components/ScreenWrapper";
import { useJobStore } from "../../stores/useJobStore";
import { useThemeStore } from "../../stores/useThemeStore";

export function JobSearchScreen() {
  const { searchResults, filters, isSearching, search, setFilters } = useJobStore();
  const colors = useThemeStore((s) => s.colors);
  const [location, setLocation] = useState(filters.location_filter);
  const [includeRemote, setIncludeRemote] = useState(filters.include_remote);

  function handleSearch() {
    const updated = {
      ...filters,
      location_filter: location,
      include_remote: includeRemote,
    };
    setFilters(updated);
    search(updated);
  }

  return (
    <ScreenWrapper scroll={false}>
      <View className="px-4 pt-4">
        <Input
          placeholder="Location (e.g. New York, Remote)"
          value={location}
          onChangeText={setLocation}
          returnKeyType="search"
          onSubmitEditing={handleSearch}
        />

        <View className="flex-row items-center justify-between mb-4">
          <Text className="text-sm font-medium" style={{ color: colors.text }}>
            Include Remote
          </Text>
          <Switch
            value={includeRemote}
            onValueChange={setIncludeRemote}
            trackColor={{ false: colors.border, true: `${colors.primary}80` }}
            thumbColor={includeRemote ? colors.primary : colors.textSecondary}
          />
        </View>

        <Button
          title="Search Jobs"
          onPress={handleSearch}
          loading={isSearching}
        />
      </View>

      {searchResults ? (
        <View className="flex-1 mt-4">
          <Text
            className="px-4 text-xs font-medium mb-2"
            style={{ color: colors.textSecondary }}
          >
            {searchResults.job_ids.length} jobs found
          </Text>
          <FlatList
            data={searchResults.job_ids}
            keyExtractor={(item) => item}
            contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 20 }}
            ItemSeparatorComponent={() => <View className="h-3" />}
            renderItem={({ item }) => (
              <Card>
                <Text
                  className="text-sm font-semibold"
                  style={{ color: colors.text }}
                >
                  Job ID: {item}
                </Text>
                <Badge label="Match" status="submitted" />
              </Card>
            )}
          />
        </View>
      ) : (
        !isSearching && (
          <EmptyState
            title="Find Your Next Role"
            message="Enter a location and search to discover matching opportunities."
          />
        )
      )}
    </ScreenWrapper>
  );
}
