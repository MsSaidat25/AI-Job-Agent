/**
 * Options Page Script
 *
 * Manages extension settings: API URL, auto-detect toggle,
 * notifications, theme, and data export/clear.
 */

(function () {
  'use strict';

  const DEFAULT_SETTINGS = {
    apiUrl: 'http://localhost:8000',
    autoDetect: true,
    notifications: true,
    theme: 'dark',
    syncIntervalMinutes: 15,
  };

  // ── DOM References ─────────────────────────────────────────────────────────

  const el = {
    apiUrl: document.getElementById('apiUrl'),
    syncInterval: document.getElementById('syncInterval'),
    autoDetect: document.getElementById('autoDetect'),
    notifications: document.getElementById('notifications'),
    themeOptions: document.querySelectorAll('.theme-option'),
    totalJobs: document.getElementById('totalJobs'),
    syncedJobs: document.getElementById('syncedJobs'),
    appliedJobs: document.getElementById('appliedJobs'),
    saveBtn: document.getElementById('saveBtn'),
    resetBtn: document.getElementById('resetBtn'),
    exportBtn: document.getElementById('exportBtn'),
    clearBtn: document.getElementById('clearBtn'),
    toast: document.getElementById('toast'),
  };

  let currentTheme = 'dark';

  // ── Initialization ─────────────────────────────────────────────────────────

  async function init() {
    await loadCurrentSettings();
    await loadStats();
    setupEventListeners();
  }

  async function loadCurrentSettings() {
    const result = await chrome.storage.local.get(['settings']);
    const settings = { ...DEFAULT_SETTINGS, ...(result.settings || {}) };

    el.apiUrl.value = settings.apiUrl;
    el.syncInterval.value = settings.syncIntervalMinutes;
    el.autoDetect.checked = settings.autoDetect;
    el.notifications.checked = settings.notifications;

    currentTheme = settings.theme;
    applyTheme(currentTheme);
    updateThemeUI(currentTheme);
  }

  async function loadStats() {
    const result = await chrome.storage.local.get(['bookmarked_jobs']);
    const jobs = result.bookmarked_jobs || [];

    el.totalJobs.textContent = jobs.length;
    el.syncedJobs.textContent = jobs.filter((j) => j.synced).length;
    el.appliedJobs.textContent = jobs.filter(
      (j) => j.status !== 'saved'
    ).length;
  }

  // ── Theme ──────────────────────────────────────────────────────────────────

  function applyTheme(theme) {
    if (theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  }

  function updateThemeUI(theme) {
    el.themeOptions.forEach((opt) => {
      if (opt.dataset.theme === theme) {
        opt.classList.add('active');
      } else {
        opt.classList.remove('active');
      }
    });
  }

  // ── Save Settings ──────────────────────────────────────────────────────────

  async function saveSettings() {
    const settings = {
      apiUrl: el.apiUrl.value.trim().replace(/\/+$/, '') || DEFAULT_SETTINGS.apiUrl,
      syncIntervalMinutes: Math.max(5, Math.min(120, parseInt(el.syncInterval.value) || 15)),
      autoDetect: el.autoDetect.checked,
      notifications: el.notifications.checked,
      theme: currentTheme,
    };

    await chrome.storage.local.set({ settings });

    // Notify the service worker that settings changed
    try {
      await chrome.runtime.sendMessage({ type: 'SETTINGS_UPDATED' });
    } catch (err) {
      // Service worker might not be running, that's fine
    }

    showToast('Settings saved', 'success');
  }

  async function resetSettings() {
    el.apiUrl.value = DEFAULT_SETTINGS.apiUrl;
    el.syncInterval.value = DEFAULT_SETTINGS.syncIntervalMinutes;
    el.autoDetect.checked = DEFAULT_SETTINGS.autoDetect;
    el.notifications.checked = DEFAULT_SETTINGS.notifications;
    currentTheme = DEFAULT_SETTINGS.theme;
    applyTheme(currentTheme);
    updateThemeUI(currentTheme);

    await chrome.storage.local.set({ settings: DEFAULT_SETTINGS });
    try {
      await chrome.runtime.sendMessage({ type: 'SETTINGS_UPDATED' });
    } catch (err) {
      // Ignore
    }

    showToast('Settings reset to defaults', 'success');
  }

  // ── Data Management ────────────────────────────────────────────────────────

  async function exportBookmarks() {
    const result = await chrome.storage.local.get(['bookmarked_jobs']);
    const jobs = result.bookmarked_jobs || [];

    const blob = new Blob([JSON.stringify(jobs, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `jobagent-bookmarks-${new Date().toISOString().split('T')[0]}.json`;
    a.click();

    URL.revokeObjectURL(url);
    showToast(`Exported ${jobs.length} bookmarks`, 'success');
  }

  async function clearBookmarks() {
    const confirmed = confirm(
      'Are you sure you want to delete all bookmarked jobs? This cannot be undone.'
    );
    if (!confirmed) return;

    await chrome.storage.local.set({ bookmarked_jobs: [] });
    await loadStats();
    showToast('All bookmarks cleared', 'success');
  }

  // ── Toast ──────────────────────────────────────────────────────────────────

  function showToast(message, type = 'success') {
    el.toast.textContent = message;
    el.toast.className = `toast ${type}`;

    // Trigger reflow to restart animation
    el.toast.offsetHeight;
    el.toast.classList.add('show');

    setTimeout(() => {
      el.toast.classList.remove('show');
    }, 2500);
  }

  // ── Event Listeners ────────────────────────────────────────────────────────

  function setupEventListeners() {
    el.saveBtn.addEventListener('click', saveSettings);
    el.resetBtn.addEventListener('click', resetSettings);
    el.exportBtn.addEventListener('click', exportBookmarks);
    el.clearBtn.addEventListener('click', clearBookmarks);

    // Theme selection
    el.themeOptions.forEach((opt) => {
      opt.addEventListener('click', () => {
        currentTheme = opt.dataset.theme;
        applyTheme(currentTheme);
        updateThemeUI(currentTheme);
      });
    });

    // Save on Enter key in text fields
    el.apiUrl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveSettings();
    });

    el.syncInterval.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveSettings();
    });
  }

  // ── Start ──────────────────────────────────────────────────────────────────

  init();
})();
