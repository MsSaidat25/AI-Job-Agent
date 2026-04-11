// dashboard.js -- Dashboard page loaders: KPIs, activity, skills, nudges, feed preview, guided journey
// Extracted from app.js lines 819-992. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.


// ═══════════════════════════════════════════════════
// DASHBOARD LOADERS
// ═══════════════════════════════════════════════════
async function loadDashboard() {
  if (!currentProfile) return;
  const firstName = (currentProfile.name || 'there').split(' ')[0];
  document.getElementById('dashGreetingText').textContent = 'Welcome back, ' + firstName + '!';
  document.getElementById('dashGreetingSub').textContent = 'Here is your personalized action plan.';

  let summary = null;
  try { summary = await api('GET', '/api/dashboard/summary'); }
  catch (e) { /* ignore -- treat as new user */ }

  const total = summary ? summary.total_applications : 0;
  const journeyEl = document.getElementById('dashJourney');
  const kpisEl = document.getElementById('dashKpis');
  const activeEl = document.getElementById('dashActiveContent');

  if (total === 0) {
    // New user: show guided journey
    journeyEl.style.display = 'block';
    kpisEl.style.display = 'none';
    activeEl.style.display = 'none';
    renderGuidedJourney();
    // Still try to show daily feed preview
    loadDashboardFeedPreview();
  } else {
    journeyEl.style.display = 'none';
    kpisEl.style.display = 'block';
    activeEl.style.display = 'block';
    renderKpiCards(summary);
    // Kick off the rest in parallel
    loadDashboardActivity();
    loadDashboardSkills();
    loadDashboardNudges();
    loadDashboardFeedPreview();
  }
}

function renderGuidedJourney() {
  const steps = [
    { icon: 'person', label: 'Complete your profile', desc: 'Upload your resume or finish the wizard', target: 'profile', done: !!(currentProfile && currentProfile.skills && currentProfile.skills.length) },
    { icon: 'payments', label: 'Calibrate your salary', desc: 'Know your market worth before applying', target: 'salary', done: false },
    { icon: 'auto_awesome', label: 'Explore career dreams', desc: 'Score the feasibility of your ideal role', target: 'career', done: false },
    { icon: 'psychology', label: 'Review skill gaps', desc: 'See how you stack up against market demand', target: 'dashboard', done: false },
    { icon: 'send', label: 'Apply to your first job', desc: 'Search, tailor a resume, and track it', target: 'jobs', done: false },
  ];
  const container = document.getElementById('journeySteps');
  container.innerHTML = '';
  steps.forEach(s => {
    const row = document.createElement('div');
    row.className = 'journey-step' + (s.done ? ' done' : '');
    const icon = document.createElement('div'); icon.className = 'journey-icon';
    icon.innerHTML = '<span class="material-symbols-outlined text-base">' + (s.done ? 'check_circle' : s.icon) + '</span>';
    const body = document.createElement('div'); body.style.flex = '1'; body.style.minWidth = '0';
    const label = document.createElement('div'); label.className = 'journey-label'; label.textContent = s.label;
    const desc = document.createElement('div'); desc.className = 'journey-desc'; desc.textContent = s.desc;
    body.appendChild(label); body.appendChild(desc);
    const btn = document.createElement('button');
    btn.className = 'journey-btn' + (s.done ? ' done-btn' : '');
    btn.textContent = s.done ? 'Done' : 'Start';
    btn.addEventListener('click', () => nav(s.target));
    row.appendChild(icon); row.appendChild(body); row.appendChild(btn);
    container.appendChild(row);
  });
}

function renderKpiCards(summary) {
  const grid = document.getElementById('kpiGrid');
  const pct = v => (v != null ? (Math.round(v * 1000) / 10) + '%' : '–');
  const cards = [
    { label: 'Total Apps', value: summary.total_applications || 0, sub: summary.submitted + ' submitted' },
    { label: 'Response Rate', value: pct(summary.response_rate), sub: summary.avg_days_to_reply != null ? '~' + Math.round(summary.avg_days_to_reply) + ' days avg' : 'No replies yet' },
    { label: 'Interview Rate', value: pct(summary.interview_rate), sub: (summary.by_status && summary.by_status.interview_scheduled) ? summary.by_status.interview_scheduled + ' scheduled' : 'None yet' },
    { label: 'Offer Rate', value: pct(summary.offer_rate), sub: (summary.by_status && summary.by_status.offer_received) ? summary.by_status.offer_received + ' offers' : 'None yet' },
  ];
  grid.innerHTML = '';
  cards.forEach(c => {
    const el = document.createElement('div'); el.className = 'kpi-card';
    el.innerHTML = '<div class="kpi-label">' + escapeHtml(c.label) + '</div><div class="kpi-value">' + escapeHtml(String(c.value)) + '</div><div class="kpi-sub">' + escapeHtml(c.sub) + '</div>';
    grid.appendChild(el);
  });
}

async function loadDashboardActivity() {
  const el = document.getElementById('dashActivity');
  try {
    const d = await api('GET', '/api/dashboard/activity');
    const events = (d.activity || []).slice(0, 10);
    if (!events.length) {
      el.innerHTML = '<div class="text-center py-4 text-xs text-slate-500">No activity yet. Apply to your first job to see it here.</div>';
      return;
    }
    const html = events.map(e => {
      const when = e.timestamp ? new Date(e.timestamp).toLocaleDateString() + ' ' + new Date(e.timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : '';
      return '<div class="timeline-item"><div class="timeline-dot ' + escapeHtml(e.event || '') + '"></div><div class="timeline-content"><div class="t-detail">' + escapeHtml(e.detail) + '</div><div class="t-time">' + escapeHtml(when) + '</div></div></div>';
    }).join('');
    el.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
  } catch (err) {
    el.innerHTML = '<div class="text-xs text-slate-500">Activity unavailable.</div>';
  }
}

async function loadDashboardSkills() {
  const el = document.getElementById('dashSkills');
  try {
    const d = await api('GET', '/api/dashboard/skills');
    const matching = (d.matching_skills || []).slice(0, 10);
    const gaps = (d.gap_skills || []).slice(0, 10);
    if (!matching.length && !gaps.length) {
      el.innerHTML = '<div class="text-xs text-slate-500">Search for jobs first — we will then compare your skills to what is in demand.</div>';
      return;
    }
    const pct = d.match_pct != null ? Math.round(d.match_pct) : 0;
    let html = '<div class="text-xs text-slate-500 mb-2">You match <strong style="color:#10b981">' + pct + '%</strong> of in-demand skills from your recent searches.</div>';
    if (matching.length) {
      html += '<div class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">You have</div><div class="flex flex-wrap">';
      matching.forEach(s => { html += '<span class="skill-tag match">' + escapeHtml(s) + '</span>'; });
      html += '</div>';
    }
    if (gaps.length) {
      html += '<div class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1 mt-3">Consider learning</div><div class="flex flex-wrap">';
      gaps.forEach(s => { html += '<span class="skill-tag gap">' + escapeHtml(s) + '</span>'; });
      html += '</div>';
    }
    el.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
  } catch (err) {
    el.innerHTML = '<div class="text-xs text-slate-500">Skill gap unavailable.</div>';
  }
}

async function loadDashboardNudges() {
  const el = document.getElementById('dashNudges');
  try {
    const d = await api('GET', '/api/nudges/pending');
    const top = (d.nudges || []).slice(0, 3);
    if (!top.length) {
      el.innerHTML = '<div class="text-xs text-slate-500">No pending nudges — nice work staying on top of things.</div>';
      return;
    }
    const html = top.map(n =>
      '<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content">' +
      '<div class="t-detail">' + escapeHtml(n.job_title) + ' · ' + escapeHtml(n.company) + '</div>' +
      '<div class="t-time">Nudge #' + escapeHtml(String(n.nudge_count || 1)) + ' · ' + escapeHtml(n.nudge_type || 'check_in') + '</div>' +
      '</div></div>'
    ).join('');
    el.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
  } catch (err) {
    el.innerHTML = '<div class="text-xs text-slate-500">No nudges.</div>';
  }
}

async function loadDashboardFeedPreview() {
  const el = document.getElementById('dashFeedPreview');
  try {
    const d = await api('GET', '/api/feed/daily');
    const top = (d.items || []).slice(0, 3);
    if (!top.length) {
      el.innerHTML = '<div class="text-xs text-slate-500">No picks yet. Try the Daily Feed to refresh.</div>';
      return;
    }
    const html = top.map(i => {
      const score = i.match_score != null ? Math.round(i.match_score) : '–';
      return '<div class="timeline-item"><div class="match-badge ' + matchBadgeClass(i.match_score) + '" style="min-width:2rem;height:2rem;font-size:0.75rem">' + score + '</div>' +
        '<div class="timeline-content"><div class="t-detail">' + escapeHtml(i.title) + '</div>' +
        '<div class="t-time">' + escapeHtml(i.company) + ' · ' + escapeHtml(i.location || '') + '</div></div></div>';
    }).join('');
    el.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
  } catch (err) {
    el.innerHTML = '<div class="text-xs text-slate-500">Feed unavailable.</div>';
  }
}
