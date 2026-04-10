/**
 * Job Data Extractors
 *
 * Site-specific extraction functions for supported job boards.
 * Each extractor returns a normalized job data object.
 */

/**
 * @typedef {Object} ExtractedJob
 * @property {string} title
 * @property {string} company
 * @property {string} location
 * @property {string} description
 * @property {string} salary
 * @property {string} url
 * @property {string} source
 * @property {boolean} remote
 * @property {string} postedDate
 */

/**
 * Detect which job board the current page belongs to.
 * @param {string} hostname
 * @returns {string|null}
 */
function detectJobBoard(hostname) {
  if (hostname.includes('linkedin.com')) return 'linkedin';
  if (hostname.includes('indeed.com')) return 'indeed';
  if (hostname.includes('glassdoor.com')) return 'glassdoor';
  if (hostname.includes('boards.greenhouse.io')) return 'greenhouse';
  if (hostname.includes('jobs.lever.co')) return 'lever';
  if (hostname.includes('myworkdayjobs.com')) return 'workday';
  return null;
}

/**
 * Extract text content from a DOM element, with fallback.
 * @param {string} selector
 * @param {Element} [context=document]
 * @returns {string}
 */
function textFromSelector(selector, context = document) {
  const el = context.querySelector(selector);
  return el ? el.textContent.trim() : '';
}

/**
 * Try multiple selectors, return first match.
 * @param {string[]} selectors
 * @param {Element} [context=document]
 * @returns {string}
 */
function textFromSelectors(selectors, context = document) {
  for (const sel of selectors) {
    const text = textFromSelector(sel, context);
    if (text) return text;
  }
  return '';
}

/**
 * Check if text indicates a remote position.
 * @param {string} text
 * @returns {boolean}
 */
function isRemote(text) {
  return /\b(remote|work from home|wfh|telecommute|distributed)\b/i.test(text);
}

// ── LinkedIn Extractor ────────────────────────────────────────────────────────

function extractLinkedIn() {
  const title = textFromSelectors([
    '.job-details-jobs-unified-top-card__job-title h1',
    '.jobs-unified-top-card__job-title',
    '.t-24.job-details-jobs-unified-top-card__job-title',
    'h1.topcard__title',
    'h2.t-24',
  ]);

  const company = textFromSelectors([
    '.job-details-jobs-unified-top-card__company-name a',
    '.job-details-jobs-unified-top-card__company-name',
    '.jobs-unified-top-card__company-name a',
    '.topcard__org-name-link',
    'a.topcard__org-name-link',
  ]);

  const location = textFromSelectors([
    '.job-details-jobs-unified-top-card__bullet',
    '.jobs-unified-top-card__bullet',
    '.topcard__flavor--bullet',
  ]);

  const description = textFromSelectors([
    '.jobs-description__content',
    '.jobs-description-content__text',
    '.jobs-box__html-content',
    '#job-details',
  ]);

  const salary = textFromSelectors([
    '.job-details-jobs-unified-top-card__job-insight--highlight span',
    '.salary-main-rail__data-body',
    '.compensation__salary',
  ]);

  const postedDate = textFromSelectors([
    '.jobs-unified-top-card__posted-date',
    '.posted-time-ago__text',
  ]);

  const locationAndType = location + ' ' + title;

  return {
    title,
    company,
    location,
    description: description.substring(0, 5000),
    salary,
    url: window.location.href,
    source: 'linkedin',
    remote: isRemote(locationAndType),
    postedDate,
  };
}

// ── Indeed Extractor ──────────────────────────────────────────────────────────

function extractIndeed() {
  const title = textFromSelectors([
    '.jobsearch-JobInfoHeader-title',
    'h1.jobTitle',
    '[data-testid="jobsearch-JobInfoHeader-title"]',
    'h1[data-testid="jobTitle"]',
    'h2.jobTitle',
  ]);

  const company = textFromSelectors([
    '[data-testid="inlineHeader-companyName"] a',
    '[data-testid="inlineHeader-companyName"]',
    '.jobsearch-InlineCompanyRating-companyHeader a',
    '.jobsearch-InlineCompanyRating a',
    'div.companyName',
  ]);

  const location = textFromSelectors([
    '[data-testid="inlineHeader-companyLocation"]',
    '[data-testid="job-location"]',
    '.jobsearch-JobInfoHeader-subtitle > div:last-child',
    'div.companyLocation',
  ]);

  const description = textFromSelectors([
    '#jobDescriptionText',
    '.jobsearch-jobDescriptionText',
    '.jobsearch-JobComponent-description',
  ]);

  const salary = textFromSelectors([
    '#salaryInfoAndJobType',
    '[data-testid="attribute_snippet_testid"]',
    '.jobsearch-JobMetadataHeader-item',
    '.salary-snippet-container',
  ]);

  const postedDate = textFromSelectors([
    '.jobsearch-HiringInsights-entry--bullet',
    '.date',
  ]);

  return {
    title,
    company,
    location,
    description: description.substring(0, 5000),
    salary,
    url: window.location.href,
    source: 'indeed',
    remote: isRemote(location + ' ' + title),
    postedDate,
  };
}

// ── Glassdoor Extractor ──────────────────────────────────────────────────────

function extractGlassdoor() {
  const title = textFromSelectors([
    '[data-test="jobTitle"]',
    '.css-1vg6q84',
    'h1.heading_Heading__BqX5J',
    '.job-title',
  ]);

  const company = textFromSelectors([
    '[data-test="employerName"]',
    '.css-87uc0g',
    '.employer-name',
    '.e1wnkr790',
  ]);

  const location = textFromSelectors([
    '[data-test="location"]',
    '.css-56kyx5',
    '.location',
    '.e1wnkr790 + span',
  ]);

  const description = textFromSelectors([
    '.jobDescriptionContent',
    '[data-test="jobDescription"]',
    '.desc',
    '.jobDescriptionContent__text',
  ]);

  const salary = textFromSelectors([
    '[data-test="detailSalary"]',
    '.css-1blnmhq',
    '.salary-estimate',
  ]);

  return {
    title,
    company,
    location,
    description: description.substring(0, 5000),
    salary,
    url: window.location.href,
    source: 'glassdoor',
    remote: isRemote(location + ' ' + title),
    postedDate: '',
  };
}

// ── Greenhouse Extractor ─────────────────────────────────────────────────────

function extractGreenhouse() {
  const title = textFromSelectors([
    '.app-title',
    'h1.heading',
    '.job__title',
    'h1',
  ]);

  const company = textFromSelectors([
    '.company-name',
    '.heading--sub',
    '#header .company-name',
  ]);

  // If company name isn't found in DOM, try extracting from URL
  let companyName = company;
  if (!companyName) {
    const match = window.location.hostname.match(
      /boards\.greenhouse\.io\/(\w+)/
    );
    if (!match) {
      const pathMatch = window.location.pathname.match(/^\/(\w+)/);
      if (pathMatch) companyName = pathMatch[1];
    } else {
      companyName = match[1];
    }
  }

  const location = textFromSelectors([
    '.location',
    '.body--metadata',
    '.location-name',
  ]);

  const description = textFromSelectors([
    '#content',
    '.content',
    '#app_body',
    '.job__description',
  ]);

  return {
    title,
    company: companyName,
    location,
    description: description.substring(0, 5000),
    salary: '',
    url: window.location.href,
    source: 'greenhouse',
    remote: isRemote(location + ' ' + title),
    postedDate: '',
  };
}

// ── Lever Extractor ──────────────────────────────────────────────────────────

function extractLever() {
  const title = textFromSelectors([
    '.posting-headline h2',
    '.posting-headline .posting-title',
    'h2',
  ]);

  // Company from URL path
  let company = '';
  const pathParts = window.location.pathname.split('/');
  if (pathParts.length >= 2) {
    company = pathParts[1].replace(/-/g, ' ');
    company = company.charAt(0).toUpperCase() + company.slice(1);
  }

  const location = textFromSelectors([
    '.posting-categories .location',
    '.sort-by-time .posting-category',
    '.posting-category:first-child',
  ]);

  const commitment = textFromSelectors([
    '.posting-categories .commitment',
    '.posting-category.commitment',
  ]);

  // Combine all content sections for description
  const sections = document.querySelectorAll('.posting-page .content');
  let description = '';
  sections.forEach((section) => {
    description += section.textContent.trim() + '\n\n';
  });
  if (!description) {
    description = textFromSelector('.posting-page');
  }

  return {
    title,
    company,
    location,
    description: description.substring(0, 5000),
    salary: '',
    url: window.location.href,
    source: 'lever',
    remote: isRemote(location + ' ' + title + ' ' + commitment),
    postedDate: '',
  };
}

// ── Workday Extractor ────────────────────────────────────────────────────────

function extractWorkday() {
  const title = textFromSelectors([
    '[data-automation-id="jobPostingHeader"] h2',
    '.css-1q2dra3',
    'h2[data-automation-id="jobPostingTitle"]',
    'h1',
  ]);

  const company = textFromSelectors([
    '[data-automation-id="jobPostingCompanyName"]',
    '.css-1fr3msi',
  ]);

  // Workday company from subdomain
  let companyName = company;
  if (!companyName) {
    const subMatch = window.location.hostname.match(/^(\w+)\./);
    if (subMatch) {
      companyName = subMatch[1].replace(/-/g, ' ');
      companyName = companyName.charAt(0).toUpperCase() + companyName.slice(1);
    }
  }

  const location = textFromSelectors([
    '[data-automation-id="locations"]',
    '.css-129m7dg',
    '[data-automation-id="jobPostingLocation"]',
  ]);

  const description = textFromSelectors([
    '[data-automation-id="jobPostingDescription"]',
    '.css-1e9hklg',
  ]);

  const postedDate = textFromSelectors([
    '[data-automation-id="postedOn"]',
    '.css-16dvcxv',
  ]);

  return {
    title,
    company: companyName,
    location,
    description: description.substring(0, 5000),
    salary: '',
    url: window.location.href,
    source: 'workday',
    remote: isRemote(location + ' ' + title),
    postedDate,
  };
}

// ── Generic Extractor (fallback) ─────────────────────────────────────────────

function extractGeneric() {
  // Best-effort extraction from any page using common patterns
  const title = textFromSelectors([
    'h1',
    '[class*="job-title"]',
    '[class*="jobTitle"]',
    '[data-testid*="title"]',
  ]);

  const company = textFromSelectors([
    '[class*="company"]',
    '[class*="employer"]',
    '[data-testid*="company"]',
  ]);

  const location = textFromSelectors([
    '[class*="location"]',
    '[data-testid*="location"]',
  ]);

  // Try to grab the main content
  const description = textFromSelectors([
    '[class*="description"]',
    '[class*="job-details"]',
    'article',
    'main',
  ]);

  return {
    title,
    company,
    location,
    description: description.substring(0, 5000),
    salary: '',
    url: window.location.href,
    source: 'other',
    remote: isRemote(location + ' ' + title + ' ' + document.title),
    postedDate: '',
  };
}

// ── Main Extraction Router ───────────────────────────────────────────────────

/**
 * Extract job data from the current page based on the detected job board.
 * @returns {ExtractedJob|null}
 */
function extractJobData() {
  const hostname = window.location.hostname;
  const board = detectJobBoard(hostname);

  let data = null;

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

  // Validate we got meaningful data
  if (data && (data.title || data.company)) {
    return data;
  }

  return null;
}

/**
 * Check if the current page looks like a job listing.
 * @returns {boolean}
 */
function isJobListingPage() {
  const hostname = window.location.hostname;
  const pathname = window.location.pathname;
  const board = detectJobBoard(hostname);

  if (!board) return false;

  switch (board) {
    case 'linkedin':
      return pathname.includes('/jobs/') || pathname.includes('/job/');
    case 'indeed':
      return (
        pathname.includes('/viewjob') ||
        pathname.includes('/rc/clk') ||
        document.querySelector('#jobDescriptionText') !== null
      );
    case 'glassdoor':
      return (
        pathname.includes('/job-listing/') ||
        pathname.includes('/Job/') ||
        document.querySelector('[data-test="jobDescription"]') !== null
      );
    case 'greenhouse':
      return pathname.split('/').length >= 3;
    case 'lever':
      // Lever job pages have at least company/job-id pattern
      return pathname.split('/').filter(Boolean).length >= 2;
    case 'workday':
      return (
        pathname.includes('/job/') ||
        document.querySelector(
          '[data-automation-id="jobPostingDescription"]'
        ) !== null
      );
    default:
      return false;
  }
}

// Export for content script
if (typeof globalThis !== 'undefined') {
  globalThis.Extractors = {
    detectJobBoard,
    extractJobData,
    isJobListingPage,
    extractLinkedIn,
    extractIndeed,
    extractGlassdoor,
    extractGreenhouse,
    extractLever,
    extractWorkday,
    extractGeneric,
  };
}
