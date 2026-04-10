/** Dashboard endpoints */

import api from "../client";
import type {
  DashboardSummaryResponse,
  DashboardApplicationsResponse,
  DashboardActivityResponse,
  DashboardSkillsResponse,
} from "../../types/api";

export async function getSummary(): Promise<DashboardSummaryResponse> {
  const { data } = await api.get<DashboardSummaryResponse>("/api/dashboard/summary");
  return data;
}

export async function getApplications(): Promise<DashboardApplicationsResponse> {
  const { data } = await api.get<DashboardApplicationsResponse>("/api/dashboard/applications");
  return data;
}

export async function getActivity(): Promise<DashboardActivityResponse> {
  const { data } = await api.get<DashboardActivityResponse>("/api/dashboard/activity");
  return data;
}

export async function getSkills(): Promise<DashboardSkillsResponse> {
  const { data } = await api.get<DashboardSkillsResponse>("/api/dashboard/skills");
  return data;
}
