// shell.js -- Chat overlay, launchDashboard, profile card, navigation, sidebar, waitlist
// Extracted from app.js lines 320-463. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ── Dashboard launch ───────────────────────────────
function toggleChatOverlay() {
  const overlay = document.getElementById('chatOverlay');
  const fab = document.getElementById('chatFabIcon');
  const isOpen = overlay.style.display !== 'none';
  overlay.style.display = isOpen ? 'none' : 'flex';
  fab.textContent = isOpen ? 'smart_toy' : 'close';
  if (!isOpen) {
    const input = document.getElementById('chatInput');
    if (input) setTimeout(() => input.focus(), 100);
  }
}

function launchDashboard(p) {
  currentProfile = p;
  document.getElementById('landing').style.display = 'none';
  document.getElementById('app').style.display = 'block';
  document.getElementById('chatFab').style.display = 'flex';
  document.getElementById('sidebarName').textContent = p.name;
  document.getElementById('sidebarRole').textContent = (p.desired_roles && p.desired_roles[0]) || p.experience_level;
  document.getElementById('sidebarAvatar').textContent = p.name.charAt(0).toUpperCase();
  updateProfileCard(p);
  checkHealth();
  initSidebarState();
  // Land on Dashboard first (not Job Search) — guided-journey pattern
  nav('dashboard');
}

function updateProfileCard(p) {
  const avatar = document.getElementById('profileCardAvatar');
  const name = document.getElementById('profileCardName');
  const role = document.getElementById('profileCardRole');
  const fields = document.getElementById('profileCardFields');
  if (!avatar) return;
  avatar.textContent = p.name ? p.name.charAt(0).toUpperCase() : '?';
  if (name) name.textContent = p.name || '--';
  if (role) role.textContent = (p.desired_roles && p.desired_roles[0]) ? p.desired_roles[0] + ' · ' + (p.experience_level || '') : (p.experience_level || '--');
  if (fields) {
    const rows = [
      ['Email', p.email], ['Location', p.location],
      ['Skills', (p.skills || []).slice(0, 6).join(', ') || '--'],
      ['Experience', (p.years_of_experience || 0) + ' yrs · ' + (p.experience_level || '--')],
      ['Roles', (p.desired_roles || []).join(', ') || '--'],
      ['Currency', p.preferred_currency || 'USD'],
      ['LinkedIn', p.linkedin_url || '--'],
    ];
    const fieldsHtml = rows.map(([l, v]) =>
      `<div class="profile-field"><span class="profile-field-label">${l}</span><span class="profile-field-value">${v || '--'}</span></div>`
    ).join('');
    if (typeof DOMPurify !== 'undefined') { fields.innerHTML = DOMPurify.sanitize(fieldsHtml); }
    else { fields.textContent = rows.map(([l, v]) => l + ': ' + (v || '--')).join(' | '); }
  }
}

// ── Navigation ─────────────────────────────────────
const VIEWS = ['dashboard', 'jobs', 'feed', 'market', 'docs', 'tracker', 'salary', 'career', 'interview', 'analytics', 'offers', 'feedback', 'profile', 'employers'];
const TITLES = {
  dashboard: 'Dashboard',
  jobs: 'Job Search',
  feed: 'Daily Feed',
  market: 'Market Intelligence',
  docs: 'Documents',
  tracker: 'Application Tracker',
  salary: 'Salary Calibration',
  career: 'Career Dreamer',
  interview: 'Interview Prep',
  analytics: 'Insights',
  offers: 'Offers',
  feedback: 'Feedback Analysis',
  profile: 'My Profile',
  employers: 'For Employers',
};

let currentView = null;  // null until first nav() call, so the initial land-on-dashboard is not skipped
let selectedJobId = null;

function nav(page) {
  if (page === currentView) return;  // clicking the active tab is a no-op
  currentView = page;
  VIEWS.forEach(v => {
    const el = document.getElementById('view-' + v);
    if (el) el.style.display = v === page ? 'block' : 'none';
    const ni = document.getElementById('nav-' + v);
    if (ni) { ni.classList.remove('active-nav'); if (v === page) ni.classList.add('active-nav'); }
    const mn = document.getElementById('mn-' + v);
    if (mn) { mn.classList.remove('active'); if (v === page) mn.classList.add('active'); }
  });
  document.getElementById('pageTitle').textContent = TITLES[page] || page;
  // Load-on-demand for data-driven views
  if (page === 'profile' && currentProfile) updateProfileCard(currentProfile);
  if (page === 'dashboard') loadDashboard();
  if (page === 'tracker') loadKanbanBoard();
  if (page === 'docs') loadTemplates();
  if (page === 'feed') loadDailyFeed();
  if (page === 'career') loadCareerDreams();
  if (page === 'offers') loadOffers();
  if (page === 'salary') prefillSalaryForm();
  if (page === 'jobs') autoFillJobLocation();
}

// ── Sidebar toggle ─────────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const isCollapsed = sb.classList.toggle('collapsed');
  localStorage.setItem('jpai_sidebar', isCollapsed ? 'collapsed' : 'expanded');
}

function initSidebarState() {
  const sb = document.getElementById('sidebar');
  const isMd = window.innerWidth >= 768 && window.innerWidth < 1024;
  const isLg = window.innerWidth >= 1024;
  if (isLg) {
    // Restore saved state on desktop
    const saved = localStorage.getItem('jpai_sidebar');
    if (saved === 'collapsed') sb.classList.add('collapsed');
    else sb.classList.remove('collapsed');
  }
  // Tablet auto-collapses via CSS, no JS needed
}

window.addEventListener('resize', () => {
  if (document.getElementById('app').style.display !== 'none') initSidebarState();
});

// ── Employer waitlist ──────────────────────────────
async function joinWaitlist() {
  const email = document.getElementById('waitlistEmail').value.trim();
  if (!email) { toast('Please enter your work email.', 'error'); return; }
  const resultEl = document.getElementById('waitlistResult');
  resultEl.style.display = 'block';
  resultEl.className = 'response-area text-sm';
  resultEl.innerHTML = '<div class="flex items-center gap-2"><div class="spinner"></div><span>Joining waitlist…</span></div>';
  try {
    const d = await api('POST', '/api/employer/waitlist', {
      email,
      company_name: document.getElementById('waitlistCompany').value.trim(),
      company_size: document.getElementById('waitlistSize').value,
    });
    resultEl.innerHTML = `<div class="flex items-center gap-2 text-primary font-semibold"><span class="material-symbols-outlined">check_circle</span>${DOMPurify.sanitize(d.message)} You're #${d.position} on the list.</div>`;
    toast('You\'re on the waitlist!', 'success');
  } catch (e) {
    resultEl.innerHTML = `<span class="text-red-400">${DOMPurify.sanitize(e.message || 'Something went wrong. Please try again.')}</span>`;
  }
}
