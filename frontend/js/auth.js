// auth.js -- Setup modal, auth flow, onboarding, wizard, submitProfile
// Extracted from app.js lines 86-319. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ── Setup modal ────────────────────────────────────
function openSetup() { document.getElementById('authModal').classList.remove('hidden'); }

// ── Auth flow ──
function _hideAllAuthPanels() {
  document.getElementById('authLogin').style.display = 'none';
  document.getElementById('authSignup').style.display = 'none';
  document.getElementById('authForgot').style.display = 'none';
}
function showAuthSignup() {
  _hideAllAuthPanels();
  document.getElementById('authSignup').style.display = '';
}
function showAuthLogin() {
  _hideAllAuthPanels();
  document.getElementById('authLogin').style.display = '';
}
function showForgotPassword() {
  _hideAllAuthPanels();
  document.getElementById('authForgot').style.display = '';
}
async function doForgotPassword() {
  const email = document.getElementById('authForgotEmail').value;
  if (!email) { toast('Please enter your email.', 'error'); return; }
  try {
    await api('POST', '/api/auth/forgot-password', { email });
    toast('If that email is registered, a reset link has been sent.', 'success');
    showAuthLogin();
  } catch (e) {
    toast(e.message || 'Failed to send reset email.', 'error');
  }
}
async function doChangePassword() {
  const token = localStorage.getItem('id_token');
  const newPw = document.getElementById('changePasswordInput').value;
  if (!token) { toast('You must be signed in to change your password.', 'error'); return; }
  if (!newPw || newPw.length < 6) { toast('Password must be at least 6 characters.', 'error'); return; }
  try {
    await api('POST', '/api/auth/change-password', { id_token: token, new_password: newPw });
    toast('Password updated successfully.', 'success');
    document.getElementById('changePasswordInput').value = '';
    document.getElementById('changePasswordSection').style.display = 'none';
  } catch (e) {
    toast(e.message || 'Failed to change password.', 'error');
  }
}
async function doLogin() {
  const email = document.getElementById('authEmail').value;
  const password = document.getElementById('authPassword').value;
  if (!email || !password) { toast('Please fill in email and password.', 'error'); return; }
  try {
    const r = await api('POST', '/api/auth/login', { email, password });
    if (r.id_token) localStorage.setItem('id_token', r.id_token);
    if (r.refresh_token) localStorage.setItem('refresh_token', r.refresh_token);
    if (r.user_id) localStorage.setItem('user_id', r.user_id);
    toast('Signed in!', 'success');
    document.getElementById('authModal').classList.add('hidden');
    showOnboardingPath();
  } catch (e) {
    // Auth not configured or invalid -- fall through to onboarding
    toast('Auth service not available. Continuing as guest.', 'info');
    document.getElementById('authModal').classList.add('hidden');
    showOnboardingPath();
  }
}
async function doSignup() {
  const name = document.getElementById('authSignupName').value;
  const email = document.getElementById('authSignupEmail').value;
  const password = document.getElementById('authSignupPassword').value;
  if (!name || !email || !password) { toast('Please fill in all fields.', 'error'); return; }
  if (password.length < 6) { toast('Password must be at least 6 characters.', 'error'); return; }
  try {
    const r = await api('POST', '/api/auth/signup', { name, email, password });
    if (r.id_token) localStorage.setItem('id_token', r.id_token);
    if (r.refresh_token) localStorage.setItem('refresh_token', r.refresh_token);
    if (r.user_id) localStorage.setItem('user_id', r.user_id);
    toast('Account created!', 'success');
    document.getElementById('authModal').classList.add('hidden');
    // Pre-fill name and email in profile form
    document.getElementById('pName').value = name;
    document.getElementById('pEmail').value = email;
    showOnboardingPath();
  } catch (e) {
    toast('Auth service not available. Continuing as guest.', 'info');
    document.getElementById('authModal').classList.add('hidden');
    showOnboardingPath();
  }
}
function doGoogleAuth() {
  toast('Google sign-in requires server configuration.', 'info');
}
function skipAuth() {
  document.getElementById('authModal').classList.add('hidden');
  showOnboardingPath();
}

// ── Onboarding path selection ──
function showOnboardingPath() {
  document.getElementById('onboardingPathModal').classList.remove('hidden');
}
function startOnboardingPath(path) {
  document.getElementById('onboardingPathModal').classList.add('hidden');
  if (path === 'resume') {
    // Jump to step 2 (resume upload) in setup modal
    document.getElementById('setupModal').classList.remove('hidden');
    goStep(2);
  } else if (path === 'wizard') {
    // Start from step 0 (guided form)
    document.getElementById('setupModal').classList.remove('hidden');
    goStep(0);
  } else if (path === 'browse') {
    // Create minimal profile and launch dashboard
    launchBrowseMode();
  }
}
async function launchBrowseMode() {
  try {
    await api('POST', '/api/profile', {
      name: 'Guest User', email: 'guest@jobpath.ai', location: 'Anywhere',
      skills: [], desired_roles: [], experience_level: 'mid', years_of_experience: 0,
    });
    const p = await api('GET', '/api/profile');
    document.getElementById('landing').style.display = 'none';
    launchDashboard(p);
    toast('Browse mode active. Set up your full profile anytime from Settings.', 'info');
  } catch(e) { toast('Could not start browse mode.', 'error'); }
}

function setupTags(inp, con, arr) {
  const i = document.getElementById(inp); if (!i) return;
  i.addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.key === ',') && i.value.trim()) {
      e.preventDefault(); const v = i.value.trim().replace(/,$/, '');
      if (v && !arr.includes(v)) { arr.push(v); addTag(con, arr, v, inp); }
      i.value = '';
    }
  });
}
function addTag(con, arr, val, inp) {
  const c = document.getElementById(con); const i = document.getElementById(inp);
  const t = document.createElement('div');
  t.style.cssText = 'display:inline-flex;align-items:center;gap:4px;background:rgba(140,85,67,0.1);color:#8C5543;border:1px solid rgba(140,85,67,0.2);border-radius:6px;padding:2px 8px;font-size:11px;font-weight:500;';
  t.textContent = val;
  const closeSpan = document.createElement('span');
  closeSpan.style.cssText = 'cursor:pointer;opacity:0.6;margin-left:2px;font-size:12px;';
  closeSpan.textContent = '×';
  t.appendChild(closeSpan);
  closeSpan.addEventListener('click', () => { const idx = arr.indexOf(val); if (idx > -1) arr.splice(idx, 1); t.remove(); });
  c.insertBefore(t, i);
}

function goStep(n) {
  // Jump directly to a setup step (used by onboarding path selection)
  document.getElementById('step0').style.display = n === 0 ? '' : 'none';
  document.getElementById('step1').style.display = n === 1 ? '' : 'none';
  document.getElementById('step2').style.display = n === 2 ? '' : 'none';
  const titles = ['Create your profile', 'Skills & Preferences', 'Final Details & Resume Upload'];
  const subs = ['Tell us about you so AI can find the best opportunities.', 'What are you looking for?', 'Upload your resume for AI auto-fill, or skip to finish.'];
  document.getElementById('setupTitle').textContent = titles[n] || titles[0];
  document.getElementById('setupSub').textContent = subs[n] || subs[0];
  for (let i = 0; i < 3; i++) {
    document.getElementById('sb' + i).className = 'h-1 flex-1 rounded-full transition-all ' + (i <= n ? 'bg-primary' : 'bg-slate-200 dark:bg-white/10');
  }
  if (n > 0) document.getElementById('setupBackBtn').style.display = '';
  setupPage = n;
}
function setupNext() {
  if (setupPage === 0) {
    if (!document.getElementById('pName').value.trim() || !document.getElementById('pEmail').value.trim() || !document.getElementById('pLocation').value.trim()) { toast('Fill in name, email, and location', 'error'); return; }
    if (!document.getElementById('pExpLevel').value) { toast('Please select your experience level', 'error'); return; }
    if (!document.getElementById('pYears').value || parseInt(document.getElementById('pYears').value) < 0) { toast('Please enter your years of experience', 'error'); return; }
    document.getElementById('step0').style.display = 'none'; document.getElementById('step1').style.display = '';
    document.getElementById('sb1').className = 'h-1 flex-1 rounded-full bg-primary transition-all';
    document.getElementById('setupTitle').textContent = 'Skills & Preferences';
    document.getElementById('setupSub').textContent = 'What are you looking for and what do you bring?';
    document.getElementById('setupBackBtn').style.display = ''; setupPage = 1;
  } else if (setupPage === 1) {
    document.getElementById('step1').style.display = 'none'; document.getElementById('step2').style.display = '';
    document.getElementById('sb2').className = 'h-1 flex-1 rounded-full bg-primary transition-all';
    document.getElementById('setupTitle').textContent = 'Final Details';
    document.getElementById('setupSub').textContent = 'Add your links and certifications (optional).';
    document.getElementById('setupNextBtn').innerHTML = 'Create Profile <span class="material-symbols-outlined text-sm">check</span>';
    setupPage = 2;
  } else { submitProfile(); }
}
function setupPrev() {
  if (setupPage === 1) {
    document.getElementById('step1').style.display = 'none'; document.getElementById('step0').style.display = '';
    document.getElementById('sb1').className = 'h-1 flex-1 rounded-full bg-slate-200 dark:bg-white/10 transition-all';
    document.getElementById('setupTitle').textContent = 'Create your profile';
    document.getElementById('setupSub').textContent = 'Tell us about you so AI can find the best opportunities.';
    document.getElementById('setupBackBtn').style.display = 'none'; setupPage = 0;
  } else if (setupPage === 2) {
    document.getElementById('step2').style.display = 'none'; document.getElementById('step1').style.display = '';
    document.getElementById('sb2').className = 'h-1 flex-1 rounded-full bg-slate-200 dark:bg-white/10 transition-all';
    document.getElementById('setupTitle').textContent = 'Skills & Preferences';
    document.getElementById('setupSub').textContent = 'What are you looking for and what do you bring?';
    document.getElementById('setupNextBtn').innerHTML = 'Continue <span class="material-symbols-outlined text-sm">arrow_forward</span>';
    setupPage = 1;
  }
}

async function submitProfile() {
  const btn = document.getElementById('setupNextBtn'); btn.disabled = true; btn.textContent = 'Saving…';
  const jobTypes = Array.from(document.querySelectorAll('#jobTypesGroup input:checked')).map(i => i.value);
  try {
    if (!sessionId) await initSession();
    const p = {
      name: document.getElementById('pName').value.trim(),
      email: document.getElementById('pEmail').value.trim(),
      phone: document.getElementById('pPhone').value.trim() || null,
      location: document.getElementById('pLocation').value.trim(),
      experience_level: document.getElementById('pExpLevel').value,
      years_of_experience: parseInt(document.getElementById('pYears').value) || 0,
      skills, desired_roles: roles, desired_job_types: jobTypes,
      preferred_currency: document.getElementById('pCurrency').value,
      desired_salary_min: parseInt(document.getElementById('pSalMin').value) || null,
      desired_salary_max: parseInt(document.getElementById('pSalMax').value) || null,
      certifications: certs, languages: langs.length ? langs : ['English'],
      linkedin_url: document.getElementById('pLinkedin').value.trim() || null,
      portfolio_url: document.getElementById('pPortfolio').value.trim() || null
    };
    await api('POST', '/api/profile', p);
    currentProfile = p;
    launchDashboard(p);
    document.getElementById('setupModal').classList.add('hidden');
    toast('Welcome, ' + p.name.split(' ')[0] + '!', 'success');
  } catch (err) {
    toast('Failed: ' + err.message, 'error');
    btn.disabled = false;
    btn.innerHTML = 'Create Profile <span class="material-symbols-outlined text-sm">check</span>';
  }
}
