import React, { useState } from "react";
import { View, Text, Switch } from "react-native";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { ScreenWrapper } from "../../components/ScreenWrapper";
import { useProfileStore } from "../../stores/useProfileStore";
import { useThemeStore } from "../../stores/useThemeStore";
import { ExperienceLevel, JobType } from "../../types/models";
import type { ProfileRequest } from "../../types/api";

export function ProfileSetupScreen() {
  const { submitProfile, isLoading } = useProfileStore();
  const colors = useThemeStore((s) => s.colors);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [desiredRoles, setDesiredRoles] = useState("");
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>(ExperienceLevel.MID);
  const [yearsExp, setYearsExp] = useState("0");
  const [includeRemote, setIncludeRemote] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const levels = Object.values(ExperienceLevel);

  async function handleSubmit() {
    if (!name.trim() || !email.trim() || !location.trim()) {
      setError("Name, email, and location are required.");
      return;
    }
    setError(null);

    const profile: ProfileRequest = {
      name: name.trim(),
      email: email.trim(),
      phone: phone.trim() || null,
      location: location.trim(),
      skills: skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      experience_level: experienceLevel,
      years_of_experience: parseInt(yearsExp, 10) || 0,
      education: [],
      work_history: [],
      desired_roles: desiredRoles
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      desired_job_types: includeRemote
        ? [JobType.FULL_TIME, JobType.REMOTE]
        : [JobType.FULL_TIME],
      preferred_currency: "USD",
      desired_salary_min: null,
      desired_salary_max: null,
      languages: ["English"],
      certifications: [],
      portfolio_url: null,
      linkedin_url: null,
    };

    try {
      await submitProfile(profile);
    } catch {
      setError("Failed to save profile. Check your connection.");
    }
  }

  return (
    <ScreenWrapper>
      <View className="px-6">
        <Text
          className="text-2xl font-bold mt-6 mb-2"
          style={{ color: colors.text }}
        >
          Set Up Your Profile
        </Text>
        <Text
          className="text-sm mb-6"
          style={{ color: colors.textSecondary }}
        >
          Tell us about yourself so we can find the best matches.
        </Text>

        <Input
          label="Full Name *"
          value={name}
          onChangeText={setName}
          placeholder="Jane Doe"
        />

        <Input
          label="Email *"
          value={email}
          onChangeText={setEmail}
          placeholder="jane@example.com"
          keyboardType="email-address"
          autoCapitalize="none"
        />

        <Input
          label="Phone"
          value={phone}
          onChangeText={setPhone}
          placeholder="+1 555 123 4567"
          keyboardType="phone-pad"
        />

        <Input
          label="Location *"
          value={location}
          onChangeText={setLocation}
          placeholder="San Francisco, CA"
        />

        <Input
          label="Skills (comma-separated)"
          value={skills}
          onChangeText={setSkills}
          placeholder="Python, React, SQL, AWS"
          multiline
        />

        <Input
          label="Desired Roles (comma-separated)"
          value={desiredRoles}
          onChangeText={setDesiredRoles}
          placeholder="Software Engineer, Full Stack Developer"
        />

        {/* Experience level selector */}
        <Text
          className="text-sm font-medium mb-2"
          style={{ color: colors.textSecondary }}
        >
          Experience Level
        </Text>
        <View className="flex-row flex-wrap gap-2 mb-4">
          {levels.map((level) => (
            <Button
              key={level}
              title={level.charAt(0).toUpperCase() + level.slice(1)}
              onPress={() => setExperienceLevel(level)}
              variant={experienceLevel === level ? "primary" : "secondary"}
              size="sm"
            />
          ))}
        </View>

        <Input
          label="Years of Experience"
          value={yearsExp}
          onChangeText={setYearsExp}
          keyboardType="numeric"
          placeholder="3"
        />

        <View className="flex-row items-center justify-between mb-6">
          <Text className="text-sm font-medium" style={{ color: colors.text }}>
            Include Remote Jobs
          </Text>
          <Switch
            value={includeRemote}
            onValueChange={setIncludeRemote}
            trackColor={{ false: colors.border, true: `${colors.primary}80` }}
            thumbColor={includeRemote ? colors.primary : colors.textSecondary}
          />
        </View>

        {error && (
          <Text className="text-sm mb-4" style={{ color: colors.error }}>
            {error}
          </Text>
        )}

        <Button
          title="Save Profile"
          onPress={handleSubmit}
          loading={isLoading}
          size="lg"
        />

        <View className="h-12" />
      </View>
    </ScreenWrapper>
  );
}
