/**
 * Background Service Worker
 *
 * Handles messages from content scripts and popup, manages sync
 * with the backend API, and maintains the extension badge count.
 */

importScripts('src/utils/storage.js', 'src/utils/api.js');

const api = new ApiClient();

// ── Initialization ───────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('[JobAgent] Extension installed/updated:', details.reason);

  // Set default settings on first install
  if (details.reason === 'install') {
    await Storage.updateSettings(Storage.DEFAULT_SETTINGS);
  }

  // Set up periodic sync alarm
  await setupSyncAlarm();

  // Update badge
  await updateBadge();
});

chrome.runtime.onStartup.addListener(async () => {
  await setupSyncAlarm();
  await updateBadge();
  await loadSettings();
});

// ── Settings ─────────────────────────────────────────────────────────────────

async function loadSettings() {
  const settings = await Storage.getSettings();
  api.setBaseUrl(settings.apiUrl);

  const sessionId = await Storage.getSessionId();
  if (sessionId) {
    api.setSessionId(sessionId);
  }
}

// ── Sync Alarm ───────────────────────────────────────────────────────────────

async function setupSyncAlarm() {
  const settings = await Storage.getSettings();
  const intervalMinutes = settings.syncIntervalMinutes || 15;

  // Clear existing alarm
  await chrome.alarms.clear('jobagent-sync');

  // Create new periodic alarm
  chrome.alarms.create('jobagent-sync', {
    delayInMinutes: 1,
    periodInMinutes: intervalMinutes,
  });
}

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'jobagent-sync') {
    await syncWithBackend();
  }
});

// ── Badge Management ─────────────────────────────────────────────────────────

async function updateBadge() {
  const count = await Storage.getUnsyncedCount();
  if (count > 0) {
    chrome.action.setBadgeText({ text: String(count) });
    chrome.action.setBadgeBackgroundColor({ color: '#f2cc0d' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

// ── Backend Sync ─────────────────────────────────────────────────────────────

async function ensureSession() {
  await loadSettings();

  let sessionId = await Storage.getSessionId();
  if (sessionId) {
    api.setSessionId(sessionId);
    // Verify session is still valid
    try {
      await api.healthCheck();
      return true;
    } catch (err) {
      // Health check failed, but session might still be valid
      if (err.status === 0) {
        // Network error, backend not reachable
        return false;
      }
    }
  }

  // Create new session
  try {
    const result = await api.createSession();
    await Storage.setSessionId(result.session_id);
    api.setSessionId(result.session_id);
    return true;
  } catch (err) {
    console.warn('[JobAgent] Could not create session:', err.message);
    return false;
  }
}

async function syncWithBackend() {
  console.log('[JobAgent] Starting sync...');

  const connected = await ensureSession();
  if (!connected) {
    console.warn('[JobAgent] Backend not reachable, skipping sync.');
    return;
  }

  const jobs = await Storage.getBookmarkedJobs();
  const unsynced = jobs.filter((j) => !j.synced);

  if (unsynced.length === 0) {
    console.log('[JobAgent] No unsynced jobs.');
    await Storage.setLastSync(Date.now());
    return;
  }

  const syncedIds = [];

  for (const job of unsynced) {
    try {
      // Use chat endpoint to tell the agent about this bookmarked job
      await api.chat(
        `I found a job I'm interested in. Please note it for me:\n` +
          `- Title: ${job.title}\n` +
          `- Company: ${job.company}\n` +
          `- Location: ${job.location}\n` +
          `- Source: ${job.source}\n` +
          `- URL: ${job.url}\n` +
          (job.salary ? `- Salary: ${job.salary}\n` : '') +
          (job.remote ? `- Remote: Yes\n` : '') +
          `\nPlease track this as a bookmarked job.`
      );
      syncedIds.push(job.id);
    } catch (err) {
      console.warn(
        `[JobAgent] Failed to sync job "${job.title}":`,
        err.message
      );
      // If session expired, stop trying
      if (err.status === 404) break;
    }
  }

  if (syncedIds.length > 0) {
    await Storage.markJobsSynced(syncedIds);
    console.log(`[JobAgent] Synced ${syncedIds.length} jobs.`);
  }

  await Storage.setLastSync(Date.now());
  await updateBadge();
}

// ── Message Handler ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(sendResponse)
    .catch((err) => {
      console.error('[JobAgent] Message handler error:', err);
      sendResponse({ success: false, error: err.message });
    });

  // Return true to indicate async response
  return true;
});

async function handleMessage(message, sender) {
  switch (message.type) {
    case 'SAVE_JOB':
      return handleSaveJob(message.data);

    case 'GET_JOBS':
      return handleGetJobs(message.filter);

    case 'DELETE_JOB':
      return handleDeleteJob(message.jobId);

    case 'UPDATE_JOB_STATUS':
      return handleUpdateStatus(message.jobId, message.status);

    case 'SYNC_NOW':
      await syncWithBackend();
      return { success: true };

    case 'GET_SYNC_STATUS':
      return handleGetSyncStatus();

    case 'CHECK_BACKEND':
      return handleCheckBackend();

    case 'EXTRACT_CURRENT_PAGE':
      return handleExtractCurrentPage(sender);

    case 'SETTINGS_UPDATED':
      await loadSettings();
      await setupSyncAlarm();
      return { success: true };

    default:
      return { success: false, error: 'Unknown message type' };
  }
}

async function handleSaveJob(jobData) {
  try {
    const jobs = await Storage.getBookmarkedJobs();
    const existing = jobs.find((j) => j.url === jobData.url);
    if (existing) {
      return { success: true, duplicate: true, job: existing };
    }

    const job = await Storage.saveJob(jobData);
    await updateBadge();

    // Send notification if enabled
    const settings = await Storage.getSettings();
    if (settings.notifications) {
      // Notifications require the notifications permission, which we
      // do not declare in the manifest to keep permissions minimal.
      // Instead we rely on the toast shown by the content script.
    }

    return { success: true, job };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

async function handleGetJobs(filter) {
  let jobs = await Storage.getBookmarkedJobs();

  if (filter) {
    if (filter.status && filter.status !== 'all') {
      jobs = jobs.filter((j) => j.status === filter.status);
    }
    if (filter.search) {
      const q = filter.search.toLowerCase();
      jobs = jobs.filter(
        (j) =>
          j.title.toLowerCase().includes(q) ||
          j.company.toLowerCase().includes(q) ||
          j.location.toLowerCase().includes(q)
      );
    }
    if (filter.source && filter.source !== 'all') {
      jobs = jobs.filter((j) => j.source === filter.source);
    }
  }

  return { success: true, jobs };
}

async function handleDeleteJob(jobId) {
  const deleted = await Storage.deleteJob(jobId);
  await updateBadge();
  return { success: deleted };
}

async function handleUpdateStatus(jobId, newStatus) {
  const job = await Storage.updateJob(jobId, {
    status: newStatus,
    synced: false,
  });
  await updateBadge();
  return { success: !!job, job };
}

async function handleGetSyncStatus() {
  const lastSync = await Storage.getLastSync();
  const unsyncedCount = await Storage.getUnsyncedCount();
  const sessionId = await Storage.getSessionId();
  return {
    success: true,
    lastSync,
    unsyncedCount,
    hasSession: !!sessionId,
  };
}

async function handleCheckBackend() {
  await loadSettings();
  try {
    const health = await api.healthCheck();
    return { success: true, health };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

async function handleExtractCurrentPage(sender) {
  // Query the active tab and send extraction message to content script
  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    if (!tab || !tab.id) {
      return { success: false, error: 'No active tab' };
    }

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: 'EXTRACT_JOB',
    });
    return response;
  } catch (err) {
    return {
      success: false,
      error: 'Could not extract job data from current page.',
    };
  }
}

// ── Initial load ─────────────────────────────────────────────────────────────
loadSettings();
