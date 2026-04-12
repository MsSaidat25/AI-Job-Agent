// client.js -- Chat, settings, account, theme, resume upload, boot
// Extracted from app.js lines 1580-1841. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ── Chat ───────────────────────────────────────────
function appendChatMsg(role, html) {
  const w = document.getElementById('chatMessages');
  const init = document.getElementById('sidebarAvatar').textContent || '?';
  const d = document.createElement('div');
  const isDark = document.documentElement.classList.contains('dark');
  d.style.cssText = 'display:flex;gap:8px;' + (role === 'user' ? 'flex-direction:row-reverse;' : 'flex-direction:row;');
  if (role === 'user') {
    const avatar = document.createElement('div');
    avatar.style.cssText = 'width:28px;height:28px;border-radius:8px;background:rgba(140,85,67,0.2);display:flex;align-items:center;justify-content:center;color:#8C5543;font-weight:700;font-size:12px;flex-shrink:0;';
    avatar.textContent = init;
    d.appendChild(avatar);
  }
  const bubble = document.createElement('div');
  bubble.style.cssText = role === 'user'
    ? 'max-width:80%;padding:10px 14px;border-radius:12px;font-size:0.875rem;line-height:1.7;background:#8C5543;color:#fff;font-weight:500;'
    : 'max-width:90%;padding:10px 14px;border-radius:12px;font-size:0.875rem;line-height:1.7;'
      + (isDark ? 'background:rgba(255,255,255,0.05);border:1px solid rgba(140,85,67,0.1);color:#cbd5e1;'
                : 'background:#f1f5f9;border:1px solid #e2e8f0;color:#1e293b;');
  if (role === 'user') { bubble.textContent = html; } else { bubble.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : ''; }
  d.appendChild(bubble);
  w.appendChild(d); w.scrollTop = w.scrollHeight; return d;
}

async function sendChat() {
  const i = document.getElementById('chatInput'); const m = i.value.trim(); if (!m) return; i.value = '';
  appendChatMsg('user', m);
  const el = appendChatMsg('agent', '');
  const bubbleEl = el.querySelectorAll('div')[1];
  bubbleEl.innerHTML = '<div style="display:flex;align-items:center;gap:8px;color:#475569;font-size:0.75rem;"><div class="spinner"></div>Thinking…</div>';
  // Prefix message with current view + selected job context so the agent can tailor answers
  const contextParts = [];
  if (currentView) contextParts.push('view=' + currentView);
  if (selectedJobId) contextParts.push('job_id=' + selectedJobId);
  const contextPrefix = contextParts.length ? '[context: ' + contextParts.join(', ') + '] ' : '';
  try { const d = await api('POST', '/api/chat', { message: contextPrefix + m }); bubbleEl.innerHTML = md(d.response); }
  catch (err) { el.querySelectorAll('div')[1].textContent = '⚠ ' + err.message; toast(err.message, 'error'); }
}

async function resetChat() {
  try {
    await api('DELETE', '/api/chat/reset');
    document.getElementById('chatMessages').innerHTML = '';
    appendChatMsg('agent', md('Conversation reset. How can I help you?'));
    toast('Chat reset', 'info');
  } catch (err) { toast(err.message, 'error'); }
}
function chatKeydown(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } }

// ── Settings ────────────────────────────────────────
async function updateSetting(key, value) {
  try {
    if (key === 'auto_apply') await api('PUT', '/api/auto-apply/settings', { enabled: value });
    else if (key === 'nudges') await api('PUT', '/api/nudges/settings', { enabled: value });
    else if (key === 'feed') { /* stored locally for now */ }
    localStorage.setItem('jpai_setting_' + key, JSON.stringify(value));
    toast('Setting updated', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

// ── Account actions ──────────────────────────────────
async function doLogout() {
  try { await api('DELETE', '/api/auth/session'); } catch(e) { /* ok if no session */ }
  localStorage.removeItem('jpai_session');
  localStorage.removeItem('jpai_profile');
  sessionId = null; currentProfile = null;
  document.getElementById('app').style.display = 'none';
  document.getElementById('chatFab').style.display = 'none';
  document.getElementById('chatOverlay').style.display = 'none';
  document.getElementById('landing').style.display = 'block';
  toast('Signed out', 'info');
}
async function doExportData() {
  try {
    const data = await api('GET', '/api/account/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'jobpath-export.json';
    a.click();
    toast('Data exported', 'success');
  } catch (err) { toast(err.message, 'error'); }
}
async function doDeleteAccount() {
  if (!confirm('This will permanently delete all your data. Are you sure?')) return;
  try {
    await api('DELETE', '/api/account');
    localStorage.clear();
    sessionId = null; currentProfile = null;
    document.getElementById('app').style.display = 'none';
    document.getElementById('chatFab').style.display = 'none';
    document.getElementById('chatOverlay').style.display = 'none';
    document.getElementById('landing').style.display = 'block';
    toast('Account deleted', 'info');
  } catch (err) { toast(err.message, 'error'); }
}

// ── Theme ──────────────────────────────────────────
function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('jpai_theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
}
function updateThemeIcons(isDark) {
  const icon = isDark ? 'light_mode' : 'dark_mode';
  ['themeIconLanding', 'themeIconDash'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = icon; }
  });
}
function initTheme() {
  const saved = localStorage.getItem('jpai_theme');
  const isDark = saved ? saved === 'dark' : false;
  document.documentElement.classList.toggle('dark', isDark);
  updateThemeIcons(isDark);
}

// ── LinkedIn helper ────────────────────────────────
function openLinkedIn() {
  const url = document.getElementById('pLinkedin').value.trim();
  window.open(url || 'https://www.linkedin.com', '_blank');
}

// ══════════════════════════════════════════════════
// RESUME UPLOAD + AI PARSE (setup & dashboard)
// ══════════════════════════════════════════════════
async function handleResumeUpload(e, context) {
  const file = e.target.files[0]; if (!file) return;

  // Determine which UI elements to update
  const isSetup = context === 'setup';
  const statusEl = document.getElementById(isSetup ? 'resumeParseStatus' : 'dashParseStatus');
  const msgEl    = document.getElementById(isSetup ? 'resumeParseMsg'    : 'dashParseMsg');
  const dropzone = document.getElementById(isSetup ? 'resumeDropzone'    : 'dashResumeDropzone');

  if (statusEl) statusEl.style.display = 'flex';
  if (msgEl)    msgEl.textContent = 'Reading file…';
  if (dropzone) {
    // Show filename in dropzone
    const inner = dropzone.querySelector('p');
    if (inner) inner.textContent = file.name;
  }

  try {
    if (msgEl) msgEl.textContent = 'Sending to server…';
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch('/api/parse-resume', {
      method: 'POST',
      headers: sessionId ? { 'X-Session-ID': sessionId } : {},
      body: formData
    });
    if (!resp.ok) { const err = await resp.json().catch(() => ({})); throw new Error(err.detail || 'Parse failed'); }
    const parsed = await resp.json();

    if (isSetup) {
      applyParsedResume(parsed);
      if (msgEl) msgEl.textContent = '✓ Profile auto-filled!';
      setTimeout(() => { if (statusEl) statusEl.style.display = 'none'; }, 3000);
      toast('Resume parsed  -  fields auto-filled!', 'success');
    } else {
      // Dashboard: update profile via API and refresh profile card
      await applyDashboardResumeParse(parsed);
    }
  } catch (err) {
    console.error(err);
    if (msgEl) msgEl.textContent = 'Could not parse  -  please fill manually.';
    toast('Could not auto-parse resume', 'error');
    setTimeout(() => { if (statusEl) statusEl.style.display = 'none'; }, 3000);
  }
}

// Apply parsed resume to setup form fields
function applyParsedResume(p) {
  const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
  set('pName', p.name); set('pEmail', p.email); set('pPhone', p.phone);
  set('pLocation', p.location); set('pLinkedin', p.linkedin_url); set('pPortfolio', p.portfolio_url);
  if (p.experience_level) set('pExpLevel', p.experience_level);
  if (p.years_of_experience) set('pYears', p.years_of_experience);
  if (Array.isArray(p.skills)) p.skills.forEach(v => { if (v && !skills.includes(v)) { skills.push(v); addTag('skillsTagsInput', skills, v, 'skillsInput'); } });
  if (Array.isArray(p.desired_roles)) p.desired_roles.forEach(v => { if (v && !roles.includes(v)) { roles.push(v); addTag('rolesTagsInput', roles, v, 'rolesInput'); } });
  if (Array.isArray(p.certifications)) p.certifications.forEach(v => { if (v && !certs.includes(v)) { certs.push(v); addTag('certsTagsInput', certs, v, 'certsInput'); } });
  if (Array.isArray(p.languages)) p.languages.forEach(v => { if (v && !langs.includes(v)) { langs.push(v); addTag('langsTagsInput', langs, v, 'langsInput'); } });
}

// Apply parsed resume to existing dashboard profile
async function applyDashboardResumeParse(parsed) {
  const statusEl = document.getElementById('dashParseStatus');
  const msgEl    = document.getElementById('dashParseMsg');
  const resultEl = document.getElementById('dashParseResult');

  try {
    if (msgEl) msgEl.textContent = 'Updating your profile…';

    // Merge with existing profile
    const updated = Object.assign({}, currentProfile);
    if (parsed.name)                        updated.name = parsed.name;
    if (parsed.email)                       updated.email = parsed.email;
    if (parsed.phone)                       updated.phone = parsed.phone;
    if (parsed.location)                    updated.location = parsed.location;
    if (parsed.experience_level)            updated.experience_level = parsed.experience_level;
    if (parsed.years_of_experience)         updated.years_of_experience = parsed.years_of_experience;
    if (parsed.linkedin_url)                updated.linkedin_url = parsed.linkedin_url;
    if (parsed.portfolio_url)               updated.portfolio_url = parsed.portfolio_url;
    // Merge arrays (deduplicate)
    if (Array.isArray(parsed.skills))       updated.skills = [...new Set([...(updated.skills||[]), ...parsed.skills])];
    if (Array.isArray(parsed.certifications)) updated.certifications = [...new Set([...(updated.certifications||[]), ...parsed.certifications])];
    if (Array.isArray(parsed.languages))    updated.languages = [...new Set([...(updated.languages||[]), ...parsed.languages])];
    if (Array.isArray(parsed.desired_roles)) updated.desired_roles = [...new Set([...(updated.desired_roles||[]), ...parsed.desired_roles])];

    await api('POST', '/api/profile', updated);
    currentProfile = updated;

    // Update sidebar & profile card
    document.getElementById('sidebarName').textContent = updated.name;
    document.getElementById('sidebarAvatar').textContent = updated.name.charAt(0).toUpperCase();
    updateProfileCard(updated);

    if (msgEl) msgEl.textContent = '✓ Profile updated!';
    setTimeout(() => { if (statusEl) statusEl.style.display = 'none'; }, 2000);

    // Show summary
    if (resultEl) {
      resultEl.style.display = 'block';
      resultEl.innerHTML = md(
        '## ✓ Resume Parsed & Profile Updated\n\n' +
        '**Name:** ' + (updated.name || '--') + '\n' +
        '**Skills added:** ' + (parsed.skills || []).join(', ') + '\n' +
        '**Roles:** ' + (updated.desired_roles || []).join(', ') + '\n' +
        '**Experience:** ' + (updated.years_of_experience || 0) + ' yrs · ' + (updated.experience_level || '--')
      );
    }
    toast('Profile updated from resume!', 'success');
  } catch (err) {
    if (msgEl) msgEl.textContent = '⚠ Update failed: ' + err.message;
    toast('Profile update failed', 'error');
  }
}

// ── Boot ───────────────────────────────────────────
async function boot() {
  initTheme();
  setupTags('skillsInput', 'skillsTagsInput', skills);
  setupTags('rolesInput', 'rolesTagsInput', roles);
  setupTags('certsInput', 'certsTagsInput', certs);
  setupTags('langsInput', 'langsTagsInput', langs);
  if (sessionId) {
    // Probe /api/session/status first so a fresh (no-profile) session does
    // not trigger a 404 on /api/profile, which can't be silenced from JS
    // under the strict CSP.
    try {
      const status = await api('GET', '/api/session/status');
      if (status && status.has_profile) {
        const p = await api('GET', '/api/profile');
        launchDashboard(p);
        document.getElementById('landing').style.display = 'none';
        return;
      }
      // Valid session but no profile yet -- stay on landing page. The
      // Get Started button will drive the setup flow from here.
    } catch (err) {
      localStorage.removeItem('jpai_session');
      sessionId = null;
      await initSession();
    }
  } else { await initSession(); }
  checkHealth();
}
boot();
setInterval(checkHealth, 30000);
