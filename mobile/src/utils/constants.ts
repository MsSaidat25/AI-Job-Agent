/** App-wide constants */

export const DEFAULT_API_BASE_URL = "http://localhost:8000";

export const SESSION_STORAGE_KEY = "@jobagent_session_id";
export const API_URL_STORAGE_KEY = "@jobagent_api_url";
export const THEME_STORAGE_KEY = "@jobagent_theme";

export const REQUEST_TIMEOUT = 30_000;
export const DOCUMENT_TIMEOUT = 60_000;

export const STATUS_COLORS: Record<string, string> = {
  draft: "#64748b",
  submitted: "#8C5543",
  under_review: "#6E4535",
  interview_scheduled: "#7C3AED",
  offer_received: "#15803D",
  rejected: "#DC2626",
  withdrawn: "#475569",
};
