/** Domain enums mirroring src/models.py */

export enum JobType {
  FULL_TIME = "full_time",
  PART_TIME = "part_time",
  CONTRACT = "contract",
  FREELANCE = "freelance",
  INTERNSHIP = "internship",
  REMOTE = "remote",
}

export enum ApplicationStatus {
  DRAFT = "draft",
  SUBMITTED = "submitted",
  UNDER_REVIEW = "under_review",
  INTERVIEW_SCHEDULED = "interview_scheduled",
  OFFER_RECEIVED = "offer_received",
  REJECTED = "rejected",
  WITHDRAWN = "withdrawn",
}

export enum ExperienceLevel {
  ENTRY = "entry",
  MID = "mid",
  SENIOR = "senior",
  LEAD = "lead",
  EXECUTIVE = "executive",
}

export const TONE_OPTIONS = [
  "professional",
  "creative",
  "technical",
  "executive",
  "academic",
] as const;

export type Tone = (typeof TONE_OPTIONS)[number];
