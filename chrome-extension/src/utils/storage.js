/**
 * Chrome Storage Helpers
 *
 * Wraps chrome.storage.local with async/await and provides typed
 * accessors for bookmarked jobs, session info, and settings.
 */

const STORAGE_KEYS = {
  JOBS: 'bookmarked_jobs',
  SESSION_ID: 'session_id',
  SETTINGS: 'settings',
  LAST_SYNC: 'last_sync_timestamp',
};

const DEFAULT_SETTINGS = {
  apiUrl: 'http://localhost:8000',
  autoDetect: true,
  notifications: true,
  theme: 'dark',
  syncIntervalMinutes: 15,
};

/**
 * Get a value from chrome.storage.local.
 * @param {string} key
 * @param {*} defaultValue
 * @returns {Promise<*>}
 */
async function storageGet(key, defaultValue = null) {
  return new Promise((resolve) => {
    chrome.storage.local.get([key], (result) => {
      resolve(result[key] !== undefined ? result[key] : defaultValue);
    });
  });
}

/**
 * Set a value in chrome.storage.local.
 * @param {string} key
 * @param {*} value
 * @returns {Promise<void>}
 */
async function storageSet(key, value) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ [key]: value }, resolve);
  });
}

/**
 * Remove a key from chrome.storage.local.
 * @param {string} key
 * @returns {Promise<void>}
 */
async function storageRemove(key) {
  return new Promise((resolve) => {
    chrome.storage.local.remove([key], resolve);
  });
}

// ── Bookmarked Jobs ──────────────────────────────────────────────────────────

/**
 * @typedef {Object} BookmarkedJob
 * @property {string} id - UUID
 * @property {string} title
 * @property {string} company
 * @property {string} location
 * @property {string} description
 * @property {string} salary
 * @property {string} url
 * @property {string} source - e.g. "linkedin", "indeed"
 * @property {boolean} remote
 * @property {string} postedDate
 * @property {string} status - "saved" | "applied" | "interview" | "offer" | "rejected"
 * @property {boolean} synced - whether pushed to backend
 * @property {number} savedAt - timestamp
 */

/**
 * Get all bookmarked jobs.
 * @returns {Promise<BookmarkedJob[]>}
 */
async function getBookmarkedJobs() {
  return storageGet(STORAGE_KEYS.JOBS, []);
}

/**
 * Save a new job bookmark.
 * @param {Partial<BookmarkedJob>} jobData
 * @returns {Promise<BookmarkedJob>}
 */
async function saveJob(jobData) {
  const jobs = await getBookmarkedJobs();

  // Check for duplicates by URL
  const existing = jobs.find((j) => j.url === jobData.url);
  if (existing) {
    return existing;
  }

  const job = {
    id: crypto.randomUUID(),
    title: jobData.title || 'Untitled Position',
    company: jobData.company || 'Unknown Company',
    location: jobData.location || '',
    description: jobData.description || '',
    salary: jobData.salary || '',
    url: jobData.url || '',
    source: jobData.source || 'manual',
    remote: jobData.remote || false,
    postedDate: jobData.postedDate || '',
    status: 'saved',
    synced: false,
    savedAt: Date.now(),
  };

  jobs.unshift(job);
  await storageSet(STORAGE_KEYS.JOBS, jobs);

  return job;
}

/**
 * Update a bookmarked job by ID.
 * @param {string} jobId
 * @param {Partial<BookmarkedJob>} updates
 * @returns {Promise<BookmarkedJob|null>}
 */
async function updateJob(jobId, updates) {
  const jobs = await getBookmarkedJobs();
  const index = jobs.findIndex((j) => j.id === jobId);
  if (index === -1) return null;

  jobs[index] = { ...jobs[index], ...updates };
  await storageSet(STORAGE_KEYS.JOBS, jobs);
  return jobs[index];
}

/**
 * Delete a bookmarked job by ID.
 * @param {string} jobId
 * @returns {Promise<boolean>}
 */
async function deleteJob(jobId) {
  const jobs = await getBookmarkedJobs();
  const filtered = jobs.filter((j) => j.id !== jobId);
  if (filtered.length === jobs.length) return false;
  await storageSet(STORAGE_KEYS.JOBS, filtered);
  return true;
}

/**
 * Get count of unsynced jobs.
 * @returns {Promise<number>}
 */
async function getUnsyncedCount() {
  const jobs = await getBookmarkedJobs();
  return jobs.filter((j) => !j.synced).length;
}

/**
 * Mark jobs as synced.
 * @param {string[]} jobIds
 * @returns {Promise<void>}
 */
async function markJobsSynced(jobIds) {
  const jobs = await getBookmarkedJobs();
  for (const job of jobs) {
    if (jobIds.includes(job.id)) {
      job.synced = true;
    }
  }
  await storageSet(STORAGE_KEYS.JOBS, jobs);
}

// ── Session ──────────────────────────────────────────────────────────────────

/**
 * Get the current backend session ID.
 * @returns {Promise<string|null>}
 */
async function getSessionId() {
  return storageGet(STORAGE_KEYS.SESSION_ID, null);
}

/**
 * Save a backend session ID.
 * @param {string} sessionId
 * @returns {Promise<void>}
 */
async function setSessionId(sessionId) {
  return storageSet(STORAGE_KEYS.SESSION_ID, sessionId);
}

// ── Settings ─────────────────────────────────────────────────────────────────

/**
 * Get extension settings.
 * @returns {Promise<typeof DEFAULT_SETTINGS>}
 */
async function getSettings() {
  const stored = await storageGet(STORAGE_KEYS.SETTINGS, {});
  return { ...DEFAULT_SETTINGS, ...stored };
}

/**
 * Update extension settings.
 * @param {Partial<typeof DEFAULT_SETTINGS>} updates
 * @returns {Promise<typeof DEFAULT_SETTINGS>}
 */
async function updateSettings(updates) {
  const current = await getSettings();
  const merged = { ...current, ...updates };
  await storageSet(STORAGE_KEYS.SETTINGS, merged);
  return merged;
}

// ── Last Sync ────────────────────────────────────────────────────────────────

async function getLastSync() {
  return storageGet(STORAGE_KEYS.LAST_SYNC, null);
}

async function setLastSync(timestamp) {
  return storageSet(STORAGE_KEYS.LAST_SYNC, timestamp);
}

// Export for use in other modules (ES module style not available in MV3
// content scripts, so we attach to globalThis for service worker imports)
if (typeof globalThis !== 'undefined') {
  globalThis.Storage = {
    getBookmarkedJobs,
    saveJob,
    updateJob,
    deleteJob,
    getUnsyncedCount,
    markJobsSynced,
    getSessionId,
    setSessionId,
    getSettings,
    updateSettings,
    getLastSync,
    setLastSync,
    STORAGE_KEYS,
    DEFAULT_SETTINGS,
  };
}
