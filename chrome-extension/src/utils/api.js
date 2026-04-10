/**
 * Backend API Client
 *
 * Communicates with the AI Job Agent FastAPI backend.
 * Manages session creation, profile setup, and job tracking.
 */

/**
 * API client for the AI Job Agent backend.
 */
class ApiClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.sessionId = null;
  }

  /**
   * Set the base URL for API calls.
   * @param {string} url
   */
  setBaseUrl(url) {
    this.baseUrl = url.replace(/\/+$/, '');
  }

  /**
   * Set the session ID for authenticated requests.
   * @param {string} sessionId
   */
  setSessionId(sessionId) {
    this.sessionId = sessionId;
  }

  /**
   * Make an HTTP request to the backend.
   * @param {string} path
   * @param {Object} options
   * @returns {Promise<Object>}
   */
  async request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.sessionId ? { 'X-Session-ID': this.sessionId } : {}),
      ...(options.headers || {}),
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        const error = new Error(
          errorBody.detail || `API error: ${response.status} ${response.statusText}`
        );
        error.status = response.status;
        error.body = errorBody;
        throw error;
      }

      if (response.status === 204) return null;
      return response.json();
    } catch (err) {
      if (err.status) throw err;
      // Network error
      const networkError = new Error(`Network error: Unable to reach ${this.baseUrl}`);
      networkError.status = 0;
      throw networkError;
    }
  }

  // ── Session Management ────────────────────────────────────────────────────

  /**
   * Check if the backend is reachable.
   * @returns {Promise<Object>}
   */
  async healthCheck() {
    return this.request('/api/health');
  }

  /**
   * Create a new backend session.
   * @returns {Promise<{session_id: string}>}
   */
  async createSession() {
    const result = await this.request('/api/session', { method: 'POST' });
    this.sessionId = result.session_id;
    return result;
  }

  /**
   * Set user profile for the current session.
   * @param {Object} profile
   * @returns {Promise<Object>}
   */
  async setProfile(profile) {
    return this.request('/api/profile', {
      method: 'POST',
      body: JSON.stringify(profile),
    });
  }

  /**
   * Get user profile for the current session.
   * @returns {Promise<Object>}
   */
  async getProfile() {
    return this.request('/api/profile');
  }

  // ── Job Operations ────────────────────────────────────────────────────────

  /**
   * Search for similar jobs via the backend.
   * @param {Object} params
   * @param {string} params.location_filter
   * @param {boolean} params.include_remote
   * @param {number} params.max_results
   * @returns {Promise<Object>}
   */
  async searchJobs(params = {}) {
    return this.request('/api/jobs/search', {
      method: 'POST',
      body: JSON.stringify({
        location_filter: params.location_filter || '',
        include_remote: params.include_remote !== false,
        max_results: params.max_results || 10,
      }),
    });
  }

  /**
   * Track a new application in the backend.
   * @param {string} jobId
   * @param {string} notes
   * @returns {Promise<Object>}
   */
  async trackApplication(jobId, notes = '') {
    return this.request('/api/applications', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId, notes }),
    });
  }

  /**
   * Update an application status.
   * @param {string} applicationId
   * @param {string} newStatus
   * @param {string} feedback
   * @param {string} notes
   * @returns {Promise<Object>}
   */
  async updateApplication(applicationId, newStatus, feedback = '', notes = '') {
    return this.request(`/api/applications/${applicationId}`, {
      method: 'PUT',
      body: JSON.stringify({
        new_status: newStatus,
        ...(feedback ? { feedback } : {}),
        ...(notes ? { notes } : {}),
      }),
    });
  }

  // ── Chat ──────────────────────────────────────────────────────────────────

  /**
   * Send a message to the AI agent.
   * @param {string} message
   * @returns {Promise<{response: string}>}
   */
  async chat(message) {
    return this.request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────

  /**
   * Get dashboard summary metrics.
   * @returns {Promise<Object>}
   */
  async getDashboardSummary() {
    return this.request('/api/dashboard/summary');
  }

  /**
   * Get application list with job details.
   * @returns {Promise<Object>}
   */
  async getDashboardApplications() {
    return this.request('/api/dashboard/applications');
  }
}

// Export for service worker importScripts
if (typeof globalThis !== 'undefined') {
  globalThis.ApiClient = ApiClient;
}
