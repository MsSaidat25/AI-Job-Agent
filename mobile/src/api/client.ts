/** Axios instance with session interceptor */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { DEFAULT_API_BASE_URL, REQUEST_TIMEOUT } from "../utils/constants";
import { useSessionStore } from "../stores/useSessionStore";
import { useProfileStore } from "../stores/useProfileStore";

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

const api = axios.create({
  baseURL: DEFAULT_API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: { "Content-Type": "application/json" },
});

// Inject X-Session-ID on every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { sessionId, apiBaseUrl } = useSessionStore.getState();
  if (apiBaseUrl) {
    config.baseURL = apiBaseUrl;
  }
  if (sessionId) {
    config.headers.set("X-Session-ID", sessionId);
  }
  return config;
});

// Handle expired sessions (404 from missing session) -- retry once.
// If session was recreated, also re-submit the profile so the agent
// is initialized before the original request is retried.
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryableConfig | undefined;
    if (
      error.response?.status === 404 &&
      original &&
      !original.url?.includes("/api/session") &&
      !original.url?.includes("/api/health") &&
      !original.url?.includes("/api/profile") &&
      !original._retried
    ) {
      original._retried = true;
      try {
        // Recreate session
        const { createSession } = useSessionStore.getState();
        await createSession();

        // Re-submit profile so the backend agent is initialized
        const { profile } = useProfileStore.getState();
        if (profile) {
          await api.post("/api/profile", profile);
        }

        return api(original);
      } catch {
        // Session re-creation or profile re-submission failed
        // Propagate the original error -- keep profile data locally
        // so the user doesn't have to re-enter it
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
