/** Application tracking endpoints */

import api from "../client";
import type {
  TrackApplicationRequest,
  UpdateApplicationRequest,
  AgentResponse,
} from "../../types/api";

export async function trackApplication(req: TrackApplicationRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/applications", req);
  return data;
}

export async function updateApplication(
  applicationId: string,
  req: UpdateApplicationRequest
): Promise<AgentResponse> {
  const { data } = await api.put<AgentResponse>(`/api/applications/${applicationId}`, req);
  return data;
}

export async function getAnalytics(): Promise<AgentResponse> {
  const { data } = await api.get<AgentResponse>("/api/analytics");
  return data;
}

export async function getFeedback(): Promise<AgentResponse> {
  const { data } = await api.get<AgentResponse>("/api/feedback");
  return data;
}
