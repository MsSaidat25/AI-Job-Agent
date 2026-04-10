/** Job search & market endpoints */

import api from "../client";
import type {
  JobSearchRequest,
  JobSearchResponse,
  MarketInsightsRequest,
  ApplicationTipsRequest,
  AgentResponse,
} from "../../types/api";

export async function searchJobs(req: JobSearchRequest): Promise<JobSearchResponse> {
  const { data } = await api.post<JobSearchResponse>("/api/jobs/search", req);
  return data;
}

export async function getMarketInsights(req: MarketInsightsRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/market-insights", req);
  return data;
}

export async function getApplicationTips(req: ApplicationTipsRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/application-tips", req);
  return data;
}
