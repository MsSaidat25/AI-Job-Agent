/** Request/response types mirroring routers/schemas.py and router-specific schemas */

import {
  ApplicationStatus,
  ExperienceLevel,
  JobType,
  Tone,
} from "./models";

// ── Request types ──────────────────────────────────────────────────────────

export interface ProfileRequest {
  name: string;
  email: string;
  phone?: string | null;
  location: string;
  skills: string[];
  experience_level: ExperienceLevel;
  years_of_experience: number;
  education: Record<string, unknown>[];
  work_history: Record<string, unknown>[];
  desired_roles: string[];
  desired_job_types: JobType[];
  preferred_currency: string;
  desired_salary_min?: number | null;
  desired_salary_max?: number | null;
  languages: string[];
  certifications: string[];
  portfolio_url?: string | null;
  linkedin_url?: string | null;
}

export interface JobSearchRequest {
  location_filter: string;
  include_remote: boolean;
  max_results: number;
}

export interface MarketInsightsRequest {
  region: string;
  industry: string;
}

export interface ApplicationTipsRequest {
  region: string;
}

export interface ResumeRequest {
  job_id: string;
  tone: Tone;
}

export interface CoverLetterRequest {
  job_id: string;
}

export interface TrackApplicationRequest {
  job_id: string;
  notes: string;
}

export interface UpdateApplicationRequest {
  new_status: ApplicationStatus;
  feedback?: string | null;
  notes?: string | null;
}

export interface ChatRequest {
  message: string;
}

export interface MoveCardRequest {
  new_status: ApplicationStatus;
  notes?: string | null;
}

export interface EmployerWaitlistRequest {
  email: string;
  company_name: string;
  company_size: string;
}

// ── Response types ─────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  sessions: number;
  db: string;
  llm_configured: boolean;
}

export interface SessionResponse {
  session_id: string;
}

export interface ProfileResponse {
  profile_id: string;
  message: string;
  currency: string;
}

export interface JobSearchResponse {
  response: string;
  job_ids: string[];
  job_cache_size: number;
}

export interface AgentResponse {
  response: string;
}

export interface ResumeParseResponse {
  name: string;
  email: string;
  phone?: string | null;
  location: string;
  experience_level: string;
  years_of_experience: number;
  skills: string[];
  desired_roles: string[];
  certifications: string[];
  languages: string[];
  linkedin_url?: string | null;
  portfolio_url?: string | null;
}

export interface EmployerWaitlistResponse {
  message: string;
  position: number;
}

// ── Kanban types ───────────────────────────────────────────────────────────

export interface KanbanCard {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  location: string;
  status: string;
  submitted_at?: string | null;
  last_updated?: string | null;
  notes: string;
  match_score?: number | null;
  source_url: string;
}

export interface KanbanColumn {
  status: string;
  label: string;
  color: string;
  cards: KanbanCard[];
}

export interface KanbanBoardResponse {
  columns: KanbanColumn[];
  total_cards: number;
}

export interface MoveCardResponse {
  id: string;
  old_status: string;
  new_status: string;
  message: string;
}

// ── Dashboard types ────────────────────────────────────────────────────────

export interface DashboardSummaryResponse {
  total_applications: number;
  submitted: number;
  response_rate: number;
  interview_rate: number;
  offer_rate: number;
  avg_days_to_reply?: number | null;
  by_status: Record<string, number>;
  top_industries: [string, number][];
  top_platforms: [string, number][];
  cached_jobs: number;
}

export interface DashboardApplicationItem {
  id: string;
  job_id: string;
  status: string;
  submitted_at?: string | null;
  last_updated?: string | null;
  employer_feedback?: string | null;
  notes: string;
  job_title?: string | null;
  job_company?: string | null;
  job_location?: string | null;
  match_score?: number | null;
}

export interface DashboardApplicationsResponse {
  applications: DashboardApplicationItem[];
  total: number;
}

export interface DashboardActivityItem {
  timestamp: string;
  event: string;
  detail: string;
}

export interface DashboardActivityResponse {
  activity: DashboardActivityItem[];
}

export interface DashboardSkillsResponse {
  user_skills: string[];
  in_demand_skills: string[];
  matching_skills: string[];
  gap_skills: string[];
  match_pct: number;
}

// ── Document types ─────────────────────────────────────────────────────────

export interface TemplateInfo {
  id: string;
  name: string;
  description: string;
  tags: string[];
  header_style: string;
  columns: number;
}

export interface TemplateListResponse {
  templates: TemplateInfo[];
}

export interface ExportRequest {
  job_id: string;
  template_id: string;
  format: "pdf" | "docx";
  tone: string;
}

export interface ExportContentRequest {
  content: string;
  template_id: string;
  format: "pdf" | "docx";
}
