// core.js -- Top-level state, api/toast/md helpers, loading utils, health/session, observers
// Extracted from app.js lines 1-85. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

const API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000' : '';
let sessionId = localStorage.getItem('jpai_session');
let setupPage = 0, updateTargetId = null;
const skills = [], roles = [], certs = [], langs = ['English'];
let currentProfile = null;

// ── API helper ──────────────────────────────────────
async function api(method, path, body = null) {
  const h = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('id_token');
  if (token) h['Authorization'] = 'Bearer ' + token;
  else if (sessionId) h['X-Session-ID'] = sessionId;
  let r = await fetch(API + path, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
  // Auto-refresh expired token once, then retry
  if (r.status === 401 && token) {
    const refreshed = await _tryRefreshToken();
    if (refreshed) {
      h['Authorization'] = 'Bearer ' + localStorage.getItem('id_token');
      r = await fetch(API + path, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
    }
  }
  if (r.status === 204) return null;
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || 'API error');
  return d;
}
async function _tryRefreshToken() {
  const rt = localStorage.getItem('refresh_token');
  if (!rt) return false;
  try {
    const r = await fetch(API + '/api/auth/refresh', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!r.ok) { _clearAuth(); return false; }
    const d = await r.json();
    if (d.id_token) localStorage.setItem('id_token', d.id_token);
    if (d.refresh_token) localStorage.setItem('refresh_token', d.refresh_token);
    return true;
  } catch { _clearAuth(); return false; }
}
function _clearAuth() {
  localStorage.removeItem('id_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_id');
}

// ── Toast ──────────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'show ' + type;
  setTimeout(() => el.className = '', 3200);
}

// ── Markdown renderer ──────────────────────────────
function md(t) {
  if (!t) return '';
  const html = t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/^### (.+)$/gm,'<h4>$1</h4>').replace(/^## (.+)$/gm,'<h3>$1</h3>').replace(/^# (.+)$/gm,'<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/^---+$/gm,'<hr/>')
    .replace(/^[*-] (.+)$/gm,'<div class="md-bullet"><span class="md-bullet-dot">•</span><span>$1</span></div>')
    .replace(/^(\d+)\. (.+)$/gm,'<div class="md-num"><span class="md-num-n">$1.</span><span>$2</span></div>')
    .replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\n/g,'<br/>');
  if (typeof DOMPurify !== 'undefined') return DOMPurify.sanitize(html);
  // Fallback: strip all HTML tags if DOMPurify failed to load
  const tmp = document.createElement('div'); tmp.textContent = t; return tmp.innerHTML;
}

// ── Loading / result helpers ───────────────────────
function setLoading(id) {
  const el = document.getElementById(id); if (!el) return;
  el.className = 'response-area';
  el.textContent = '';
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;align-items:center;gap:8px;color:#475569;font-size:0.75rem;';
  const spin = document.createElement('div'); spin.className = 'spinner';
  wrap.appendChild(spin); wrap.appendChild(document.createTextNode('Thinking…'));
  el.appendChild(wrap);
}
function setResult(id, t) {
  const el = document.getElementById(id); if (!el) return;
  el.className = 'response-area'; el.innerHTML = md(t);
}

// ── Health check ───────────────────────────────────
async function checkHealth() {
  try {
    await api('GET', '/api/health');
  } catch {
    // Health check failed silently -- no user-facing indicator needed
  }
}

// ── Session ────────────────────────────────────────
async function initSession() {
  try { const d = await api('POST', '/api/session'); sessionId = d.session_id; localStorage.setItem('jpai_session', sessionId); return true; }
  catch { return false; }
}

// ── Counter animations ─────────────────────────────
function animateCounters() {
  document.querySelectorAll('[data-target]').forEach(el => {
    const t = parseInt(el.dataset.target);
    if (isNaN(t)) return;
    let c = 0;
    const x = setInterval(() => { c = Math.min(c + t / 40, t); el.textContent = Math.floor(c); if (c >= t) clearInterval(x); }, 30);
  });
}
const hObs = new IntersectionObserver(e => { if (e[0].isIntersecting) { animateCounters(); hObs.disconnect(); } }, { threshold: 0.5 });
const hs = document.querySelector('[data-target]'); if (hs) hObs.observe(hs);

// ── Scroll reveal ──────────────────────────────────
const rObs = new IntersectionObserver(e => { e.forEach(x => { if (x.isIntersecting) x.target.classList.add('visible'); }); }, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(el => rObs.observe(el));

// ── Cross-cutting render helpers (used by jobs, dashboard, kanban, prepare, insights) ──
function escapeHtml(s) {
  if (s == null) return '';
  const d = document.createElement('div'); d.textContent = String(s);
  return d.innerHTML;
}
function matchBadgeClass(score) {
  if (score == null) return 'low';
  if (score >= 80) return 'high';
  if (score >= 60) return 'mid';
  return 'low';
}
function workTypeLabel(job) {
  if (job.remote_allowed) return 'Remote';
  const jt = (job.job_type || '').toLowerCase();
  if (jt.includes('contract')) return 'Contract';
  if (jt.includes('part')) return 'Part-time';
  if (jt.includes('intern')) return 'Internship';
  if (jt.includes('freelance')) return 'Freelance';
  return 'On-site';
}
function formatSalary(job) {
  if (!job.salary_min && !job.salary_max) return '';
  const cur = job.currency || 'USD';
  const fmt = n => (n >= 1000 ? Math.round(n / 1000) + 'k' : n);
  if (job.salary_min && job.salary_max) return cur + ' ' + fmt(job.salary_min) + '–' + fmt(job.salary_max);
  if (job.salary_min) return cur + ' ' + fmt(job.salary_min) + '+';
  return 'Up to ' + cur + ' ' + fmt(job.salary_max);
}
