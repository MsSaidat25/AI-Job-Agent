/**
 * Popup Script
 *
 * Controls the extension popup UI: listing saved jobs, saving the
 * current page, filtering, status changes, and backend sync.
 */

(function () {
  'use strict';

  // ── DOM References ─────────────────────────────────────────────────────────

  const elements = {
    syncBtn: document.getElementById('syncBtn'),
    settingsBtn: document.getElementById('settingsBtn'),
    connectionDot: document.getElementById('connectionDot'),
    connectionText: document.getElementById('connectionText'),
    saveCurrentBtn: document.getElementById('saveCurrentBtn'),
    searchInput: document.getElementById('searchInput'),
    statusFilter: document.getElementById('statusFilter'),
    jobCount: document.getElementById('jobCount'),
    unsyncedCount: document.getElementById('unsyncedCount'),
    unsyncedNum: document.getElementById('unsyncedNum'),
    jobList: document.getElementById('jobList'),
    emptyState: document.getElementById('emptyState'),
    openAppLink: document.getElementById('openAppLink'),
  };

  // ── State ──────────────────────────────────────────────────────────────────

  let currentJobs = [];
  let settings = {};

  // ── Initialization ─────────────────────────────────────────────────────────

  async function init() {
    // Load settings and apply theme
    await loadSettings();
    applyTheme();

    // Check backend connection
    checkBackend();

    // Load and display jobs
    await loadJobs();

    // Set up event listeners
    setupEventListeners();

    // Update app link URL
    if (settings.apiUrl) {
      elements.openAppLink.href = settings.apiUrl;
    }
  }

  async function loadSettings() {
    const result = await chrome.storage.local.get(['settings']);
    settings = { ...getDefaultSettings(), ...(result.settings || {}) };
  }

  function getDefaultSettings() {
    return {
      apiUrl: 'http://localhost:8000',
      autoDetect: true,
      notifications: true,
      theme: 'dark',
      syncIntervalMinutes: 15,
    };
  }

  function applyTheme() {
    if (settings.theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  }

  // ── Backend Connection ─────────────────────────────────────────────────────

  async function checkBackend() {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'CHECK_BACKEND',
      });

      if (response && response.success) {
        elements.connectionDot.className = 'dot connected';
        elements.connectionText.textContent = 'Connected to backend';
      } else {
        elements.connectionDot.className = 'dot disconnected';
        elements.connectionText.textContent =
          'Backend offline - jobs saved locally';
      }
    } catch (err) {
      elements.connectionDot.className = 'dot disconnected';
      elements.connectionText.textContent = 'Cannot reach backend';
    }
  }

  // ── Job Loading ────────────────────────────────────────────────────────────

  async function loadJobs() {
    const filter = {
      search: elements.searchInput.value,
      status: elements.statusFilter.value,
    };

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'GET_JOBS',
        filter,
      });

      if (response && response.success) {
        currentJobs = response.jobs;
        renderJobs(currentJobs);
        updateCounts();
      }
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  }

  function updateCounts() {
    elements.jobCount.textContent = currentJobs.length;

    const unsynced = currentJobs.filter((j) => !j.synced).length;
    if (unsynced > 0) {
      elements.unsyncedCount.style.display = 'inline-flex';
      elements.unsyncedNum.textContent = unsynced;
    } else {
      elements.unsyncedCount.style.display = 'none';
    }
  }

  // ── Job Rendering ──────────────────────────────────────────────────────────

  function renderJobs(jobs) {
    if (jobs.length === 0) {
      elements.jobList.style.display = 'none';
      elements.emptyState.style.display = 'flex';
      return;
    }

    elements.jobList.style.display = 'block';
    elements.emptyState.style.display = 'none';

    elements.jobList.innerHTML = jobs.map((job) => createJobCard(job)).join('');

    // Attach event listeners to dynamic elements
    attachJobEventListeners();
  }

  function createJobCard(job) {
    const timeAgo = formatTimeAgo(job.savedAt);
    const statusClass = `status-${job.status}`;
    const syncClass = job.synced ? 'synced' : 'unsynced';
    const syncTitle = job.synced ? 'Synced with backend' : 'Not yet synced';

    return `
      <div class="job-card" data-job-id="${job.id}" data-url="${escapeHtml(job.url)}">
        <div class="job-card-content">
          <div class="job-title" title="${escapeHtml(job.title)}">${escapeHtml(job.title || 'Untitled Position')}</div>
          <div class="job-company">${escapeHtml(job.company || 'Unknown Company')}</div>
          <div class="job-meta">
            ${job.location ? `
              <span class="job-meta-item" title="${escapeHtml(job.location)}">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                ${escapeHtml(truncate(job.location, 25))}
              </span>
            ` : ''}
            ${job.salary ? `
              <span class="job-meta-item">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                ${escapeHtml(truncate(job.salary, 20))}
              </span>
            ` : ''}
            <span class="source-badge">${escapeHtml(job.source)}</span>
            <span class="job-meta-item">${timeAgo}</span>
          </div>
        </div>
        <div class="job-actions">
          <div class="status-dropdown">
            <span class="status-badge ${statusClass}" data-job-id="${job.id}">${escapeHtml(job.status)}</span>
            <div class="status-menu">
              <button class="status-menu-item" data-job-id="${job.id}" data-status="saved">Saved</button>
              <button class="status-menu-item" data-job-id="${job.id}" data-status="applied">Applied</button>
              <button class="status-menu-item" data-job-id="${job.id}" data-status="interview">Interview</button>
              <button class="status-menu-item" data-job-id="${job.id}" data-status="offer">Offer</button>
              <button class="status-menu-item" data-job-id="${job.id}" data-status="rejected">Rejected</button>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:4px;">
            <span class="sync-dot ${syncClass}" title="${syncTitle}"></span>
            <button class="delete-btn" data-job-id="${job.id}" title="Remove">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function attachJobEventListeners() {
    // Card click -> open URL
    document.querySelectorAll('.job-card').forEach((card) => {
      card.addEventListener('click', (e) => {
        // Ignore clicks on buttons and dropdowns
        if (
          e.target.closest('.delete-btn') ||
          e.target.closest('.status-menu') ||
          e.target.closest('.status-badge')
        ) {
          return;
        }
        const url = card.dataset.url;
        if (url) {
          chrome.tabs.create({ url });
        }
      });
    });

    // Status change
    document.querySelectorAll('.status-menu-item').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const jobId = btn.dataset.jobId;
        const newStatus = btn.dataset.status;
        await updateJobStatus(jobId, newStatus);
      });
    });

    // Delete
    document.querySelectorAll('.delete-btn').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const jobId = btn.dataset.jobId;
        await deleteJob(jobId);
      });
    });
  }

  // ── Job Actions ────────────────────────────────────────────────────────────

  async function saveCurrentPage() {
    const btn = elements.saveCurrentBtn;
    const originalContent = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="loading">
        <circle cx="12" cy="12" r="10"/>
      </svg>
      Detecting job...
    `;

    try {
      // Try content script extraction first
      const response = await chrome.runtime.sendMessage({
        type: 'EXTRACT_CURRENT_PAGE',
      });

      if (response && response.success && response.data) {
        // Save the extracted job
        const saveResponse = await chrome.runtime.sendMessage({
          type: 'SAVE_JOB',
          data: response.data,
        });

        if (saveResponse && saveResponse.success) {
          if (saveResponse.duplicate) {
            btn.innerHTML = `
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Already Saved
            `;
            btn.classList.add('error');
          } else {
            btn.innerHTML = `
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              Saved!
            `;
            btn.classList.add('success');
            await loadJobs();
          }
        } else {
          throw new Error(saveResponse?.error || 'Failed to save');
        }
      } else {
        // Fallback: save the current tab URL manually
        const [tab] = await chrome.tabs.query({
          active: true,
          currentWindow: true,
        });

        if (tab) {
          const saveResponse = await chrome.runtime.sendMessage({
            type: 'SAVE_JOB',
            data: {
              title: tab.title || 'Untitled',
              company: '',
              location: '',
              description: '',
              salary: '',
              url: tab.url,
              source: 'manual',
              remote: false,
              postedDate: '',
            },
          });

          if (saveResponse && saveResponse.success) {
            if (saveResponse.duplicate) {
              btn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                Already Saved
              `;
            } else {
              btn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                Saved (basic info)
              `;
              btn.classList.add('success');
              await loadJobs();
            }
          }
        }
      }
    } catch (err) {
      console.error('Save error:', err);
      btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        Failed to save
      `;
      btn.classList.add('error');
    }

    // Reset button after delay
    setTimeout(() => {
      btn.innerHTML = originalContent;
      btn.classList.remove('success', 'error');
      btn.disabled = false;
    }, 2000);
  }

  async function updateJobStatus(jobId, newStatus) {
    try {
      await chrome.runtime.sendMessage({
        type: 'UPDATE_JOB_STATUS',
        jobId,
        status: newStatus,
      });
      await loadJobs();
    } catch (err) {
      console.error('Status update error:', err);
    }
  }

  async function deleteJob(jobId) {
    try {
      await chrome.runtime.sendMessage({
        type: 'DELETE_JOB',
        jobId,
      });
      await loadJobs();
    } catch (err) {
      console.error('Delete error:', err);
    }
  }

  async function syncNow() {
    const btn = elements.syncBtn;
    btn.classList.add('spinning');

    try {
      await chrome.runtime.sendMessage({ type: 'SYNC_NOW' });
      await loadJobs();
      await checkBackend();
    } catch (err) {
      console.error('Sync error:', err);
    } finally {
      btn.classList.remove('spinning');
    }
  }

  // ── Event Listeners ────────────────────────────────────────────────────────

  function setupEventListeners() {
    elements.saveCurrentBtn.addEventListener('click', saveCurrentPage);
    elements.syncBtn.addEventListener('click', syncNow);
    elements.settingsBtn.addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });

    // Debounced search
    let searchTimeout;
    elements.searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(loadJobs, 250);
    });

    elements.statusFilter.addEventListener('change', loadJobs);

    // Listen for storage changes (e.g. settings updated from options page)
    chrome.storage.onChanged.addListener((changes) => {
      if (changes.settings) {
        settings = {
          ...getDefaultSettings(),
          ...(changes.settings.newValue || {}),
        };
        applyTheme();
        if (settings.apiUrl) {
          elements.openAppLink.href = settings.apiUrl;
        }
      }
      if (changes.bookmarked_jobs) {
        loadJobs();
      }
    });
  }

  // ── Utility Functions ──────────────────────────────────────────────────────

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function truncate(str, maxLength) {
    if (!str) return '';
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
  }

  function formatTimeAgo(timestamp) {
    if (!timestamp) return '';
    const seconds = Math.floor((Date.now() - timestamp) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return new Date(timestamp).toLocaleDateString();
  }

  // ── Start ──────────────────────────────────────────────────────────────────

  init();
})();
