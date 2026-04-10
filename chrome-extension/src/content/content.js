/**
 * Content Script
 *
 * Injected into supported job board pages to detect job listings
 * and provide a floating "Save to JobAgent" button.
 */

(function () {
  'use strict';

  // Prevent double-injection
  if (window.__jobAgentContentLoaded) return;
  window.__jobAgentContentLoaded = true;

  // ── Constants ──────────────────────────────────────────────────────────────

  const BUTTON_ID = 'jobagent-save-btn';
  const TOAST_ID = 'jobagent-toast';
  const ACCENT = '#f2cc0d';
  const ACCENT_HOVER = '#d4b30b';
  const BG_DARK = '#1a1a2e';
  const TEXT_LIGHT = '#e0e0e0';

  // ── Inline Extractors (self-contained for content script) ──────────────────

  function detectJobBoard(hostname) {
    if (hostname.includes('linkedin.com')) return 'linkedin';
    if (hostname.includes('indeed.com')) return 'indeed';
    if (hostname.includes('glassdoor.com')) return 'glassdoor';
    if (hostname.includes('boards.greenhouse.io')) return 'greenhouse';
    if (hostname.includes('jobs.lever.co')) return 'lever';
    if (hostname.includes('myworkdayjobs.com')) return 'workday';
    return null;
  }

  function textFromSelectors(selectors, context = document) {
    for (const sel of selectors) {
      const el = context.querySelector(sel);
      if (el) {
        const text = el.textContent.trim();
        if (text) return text;
      }
    }
    return '';
  }

  function isRemoteText(text) {
    return /\b(remote|work from home|wfh|telecommute|distributed)\b/i.test(text);
  }

  function extractLinkedIn() {
    return {
      title: textFromSelectors([
        '.job-details-jobs-unified-top-card__job-title h1',
        '.jobs-unified-top-card__job-title',
        '.t-24.job-details-jobs-unified-top-card__job-title',
        'h1.topcard__title',
        'h2.t-24',
      ]),
      company: textFromSelectors([
        '.job-details-jobs-unified-top-card__company-name a',
        '.job-details-jobs-unified-top-card__company-name',
        '.jobs-unified-top-card__company-name a',
        '.topcard__org-name-link',
      ]),
      location: textFromSelectors([
        '.job-details-jobs-unified-top-card__bullet',
        '.jobs-unified-top-card__bullet',
        '.topcard__flavor--bullet',
      ]),
      description: textFromSelectors([
        '.jobs-description__content',
        '.jobs-description-content__text',
        '#job-details',
      ]).substring(0, 5000),
      salary: textFromSelectors([
        '.job-details-jobs-unified-top-card__job-insight--highlight span',
        '.salary-main-rail__data-body',
      ]),
      postedDate: textFromSelectors([
        '.jobs-unified-top-card__posted-date',
        '.posted-time-ago__text',
      ]),
    };
  }

  function extractIndeed() {
    return {
      title: textFromSelectors([
        '.jobsearch-JobInfoHeader-title',
        'h1.jobTitle',
        'h2.jobTitle',
        '[data-testid="jobsearch-JobInfoHeader-title"]',
      ]),
      company: textFromSelectors([
        '[data-testid="inlineHeader-companyName"] a',
        '[data-testid="inlineHeader-companyName"]',
        '.jobsearch-InlineCompanyRating a',
        'div.companyName',
      ]),
      location: textFromSelectors([
        '[data-testid="inlineHeader-companyLocation"]',
        '[data-testid="job-location"]',
        'div.companyLocation',
      ]),
      description: textFromSelectors([
        '#jobDescriptionText',
        '.jobsearch-jobDescriptionText',
      ]).substring(0, 5000),
      salary: textFromSelectors([
        '#salaryInfoAndJobType',
        '[data-testid="attribute_snippet_testid"]',
        '.salary-snippet-container',
      ]),
      postedDate: textFromSelectors([
        '.jobsearch-HiringInsights-entry--bullet',
        '.date',
      ]),
    };
  }

  function extractGlassdoor() {
    return {
      title: textFromSelectors([
        '[data-test="jobTitle"]',
        '.css-1vg6q84',
        'h1.heading_Heading__BqX5J',
      ]),
      company: textFromSelectors([
        '[data-test="employerName"]',
        '.css-87uc0g',
        '.employer-name',
      ]),
      location: textFromSelectors([
        '[data-test="location"]',
        '.css-56kyx5',
      ]),
      description: textFromSelectors([
        '.jobDescriptionContent',
        '[data-test="jobDescription"]',
      ]).substring(0, 5000),
      salary: textFromSelectors([
        '[data-test="detailSalary"]',
        '.css-1blnmhq',
      ]),
      postedDate: '',
    };
  }

  function extractGreenhouse() {
    let company = textFromSelectors(['.company-name', '.heading--sub']);
    if (!company) {
      const pathMatch = window.location.pathname.match(/^\/(\w+)/);
      if (pathMatch) company = pathMatch[1];
    }
    return {
      title: textFromSelectors(['.app-title', 'h1.heading', 'h1']),
      company,
      location: textFromSelectors(['.location', '.body--metadata']),
      description: textFromSelectors([
        '#content',
        '.content',
        '.job__description',
      ]).substring(0, 5000),
      salary: '',
      postedDate: '',
    };
  }

  function extractLever() {
    let company = '';
    const parts = window.location.pathname.split('/');
    if (parts.length >= 2) {
      company = parts[1].replace(/-/g, ' ');
      company = company.charAt(0).toUpperCase() + company.slice(1);
    }
    const sections = document.querySelectorAll('.posting-page .content');
    let desc = '';
    sections.forEach((s) => (desc += s.textContent.trim() + '\n\n'));
    if (!desc) desc = textFromSelectors(['.posting-page']);

    return {
      title: textFromSelectors(['.posting-headline h2', 'h2']),
      company,
      location: textFromSelectors([
        '.posting-categories .location',
        '.posting-category:first-child',
      ]),
      description: desc.substring(0, 5000),
      salary: '',
      postedDate: '',
    };
  }

  function extractWorkday() {
    let company = textFromSelectors([
      '[data-automation-id="jobPostingCompanyName"]',
    ]);
    if (!company) {
      const subMatch = window.location.hostname.match(/^(\w+)\./);
      if (subMatch) {
        company = subMatch[1].replace(/-/g, ' ');
        company = company.charAt(0).toUpperCase() + company.slice(1);
      }
    }
    return {
      title: textFromSelectors([
        '[data-automation-id="jobPostingHeader"] h2',
        'h2[data-automation-id="jobPostingTitle"]',
        'h1',
      ]),
      company,
      location: textFromSelectors([
        '[data-automation-id="locations"]',
        '[data-automation-id="jobPostingLocation"]',
      ]),
      description: textFromSelectors([
        '[data-automation-id="jobPostingDescription"]',
      ]).substring(0, 5000),
      salary: '',
      postedDate: textFromSelectors(['[data-automation-id="postedOn"]']),
    };
  }

  function extractGeneric() {
    return {
      title: textFromSelectors([
        'h1',
        '[class*="job-title"]',
        '[class*="jobTitle"]',
      ]),
      company: textFromSelectors([
        '[class*="company"]',
        '[class*="employer"]',
      ]),
      location: textFromSelectors(['[class*="location"]']),
      description: textFromSelectors([
        '[class*="description"]',
        'article',
        'main',
      ]).substring(0, 5000),
      salary: '',
      postedDate: '',
    };
  }

  function extractJobData() {
    const board = detectJobBoard(window.location.hostname);
    let data;
    switch (board) {
      case 'linkedin':
        data = extractLinkedIn();
        break;
      case 'indeed':
        data = extractIndeed();
        break;
      case 'glassdoor':
        data = extractGlassdoor();
        break;
      case 'greenhouse':
        data = extractGreenhouse();
        break;
      case 'lever':
        data = extractLever();
        break;
      case 'workday':
        data = extractWorkday();
        break;
      default:
        data = extractGeneric();
        break;
    }
    data.url = window.location.href;
    data.source = board || 'other';
    data.remote = isRemoteText(
      (data.location || '') + ' ' + (data.title || '')
    );
    if (data.title || data.company) return data;
    return null;
  }

  // ── Floating Button ────────────────────────────────────────────────────────

  function createFloatingButton() {
    if (document.getElementById(BUTTON_ID)) return;

    const btn = document.createElement('button');
    btn.id = BUTTON_ID;
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;vertical-align:middle;">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
      </svg>
      <span style="vertical-align:middle;">Save to JobAgent</span>
    `;

    Object.assign(btn.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: '2147483647',
      padding: '12px 20px',
      backgroundColor: ACCENT,
      color: '#1a1a2e',
      border: 'none',
      borderRadius: '50px',
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer',
      boxShadow: '0 4px 20px rgba(242, 204, 13, 0.4)',
      transition: 'all 0.2s ease',
      display: 'flex',
      alignItems: 'center',
    });

    btn.addEventListener('mouseenter', () => {
      btn.style.backgroundColor = ACCENT_HOVER;
      btn.style.transform = 'translateY(-2px)';
      btn.style.boxShadow = '0 6px 24px rgba(242, 204, 13, 0.5)';
    });

    btn.addEventListener('mouseleave', () => {
      btn.style.backgroundColor = ACCENT;
      btn.style.transform = 'translateY(0)';
      btn.style.boxShadow = '0 4px 20px rgba(242, 204, 13, 0.4)';
    });

    btn.addEventListener('click', handleSaveClick);

    document.body.appendChild(btn);
  }

  // ── Toast Notification ─────────────────────────────────────────────────────

  function showToast(message, type = 'success') {
    // Remove existing toast
    const existing = document.getElementById(TOAST_ID);
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = TOAST_ID;
    toast.textContent = message;

    const bgColor =
      type === 'success'
        ? '#16a34a'
        : type === 'error'
          ? '#dc2626'
          : '#2563eb';

    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '80px',
      right: '24px',
      zIndex: '2147483647',
      padding: '12px 20px',
      backgroundColor: bgColor,
      color: '#fff',
      borderRadius: '8px',
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      fontSize: '14px',
      fontWeight: '500',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      transition: 'opacity 0.3s ease, transform 0.3s ease',
      opacity: '0',
      transform: 'translateY(10px)',
    });

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
    });

    // Animate out and remove
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // ── Save Handler ───────────────────────────────────────────────────────────

  async function handleSaveClick() {
    const btn = document.getElementById(BUTTON_ID);
    if (!btn) return;

    // Disable button during save
    btn.disabled = true;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="jobagent-spinner" style="margin-right:6px;vertical-align:middle;">
        <circle cx="12" cy="12" r="10"/>
      </svg>
      <span style="vertical-align:middle;">Saving...</span>
    `;

    // Add spinner animation
    if (!document.getElementById('jobagent-spinner-style')) {
      const style = document.createElement('style');
      style.id = 'jobagent-spinner-style';
      style.textContent = `
        @keyframes jobagent-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .jobagent-spinner {
          animation: jobagent-spin 1s linear infinite;
        }
      `;
      document.head.appendChild(style);
    }

    try {
      const jobData = extractJobData();

      if (!jobData) {
        showToast('Could not detect job details on this page.', 'error');
        return;
      }

      // Send to background service worker
      const response = await chrome.runtime.sendMessage({
        type: 'SAVE_JOB',
        data: jobData,
      });

      if (response && response.success) {
        if (response.duplicate) {
          showToast('This job is already saved.', 'info');
        } else {
          showToast('Job saved to JobAgent!', 'success');
          // Update button to show saved state
          btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;vertical-align:middle;">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span style="vertical-align:middle;">Saved!</span>
          `;
          btn.style.backgroundColor = '#16a34a';
          setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.backgroundColor = ACCENT;
          }, 2000);
        }
      } else {
        showToast(response?.error || 'Failed to save job.', 'error');
      }
    } catch (err) {
      console.error('[JobAgent] Save error:', err);
      showToast('Failed to save job. Extension error.', 'error');
    } finally {
      btn.disabled = false;
      // Restore original if not already restored by success handler
      setTimeout(() => {
        if (btn.querySelector('.jobagent-spinner')) {
          btn.innerHTML = originalHTML;
        }
      }, 500);
    }
  }

  // ── Message Listener ───────────────────────────────────────────────────────

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'EXTRACT_JOB') {
      const data = extractJobData();
      sendResponse({ success: !!data, data });
      return true;
    }

    if (message.type === 'CHECK_JOB_PAGE') {
      const board = detectJobBoard(window.location.hostname);
      const hasData = !!extractJobData();
      sendResponse({ isJobPage: hasData, board });
      return true;
    }

    return false;
  });

  // ── Initialization ─────────────────────────────────────────────────────────

  async function init() {
    // Check settings for auto-detect preference
    const result = await chrome.storage.local.get(['settings']);
    const settings = result.settings || {};
    const autoDetect = settings.autoDetect !== false;

    if (!autoDetect) return;

    const board = detectJobBoard(window.location.hostname);
    if (!board) return;

    // Wait a moment for dynamic content to load
    setTimeout(() => {
      const jobData = extractJobData();
      if (jobData && (jobData.title || jobData.company)) {
        createFloatingButton();
      }
    }, 1500);

    // Also watch for SPA navigation (LinkedIn, etc.)
    let lastUrl = window.location.href;
    const observer = new MutationObserver(() => {
      if (window.location.href !== lastUrl) {
        lastUrl = window.location.href;
        // Remove old button
        const oldBtn = document.getElementById(BUTTON_ID);
        if (oldBtn) oldBtn.remove();
        // Re-check after content loads
        setTimeout(() => {
          const jobData = extractJobData();
          if (jobData && (jobData.title || jobData.company)) {
            createFloatingButton();
          }
        }, 2000);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
