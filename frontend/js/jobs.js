// jobs.js -- Jobs V2 search, filters, cards, pagination, detail panel, save
// Extracted from app.js lines 464-756. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ── API calls ──────────────────────────────────────
function copyId(id) { navigator.clipboard.writeText(id).then(() => toast('Copied!', 'success')); }

// ═══════════════════════════════════════════════════
// JOB SEARCH V2 — filters, cards, pagination, details
// ═══════════════════════════════════════════════════
let currentJobsPage = 1;
let currentJobsTotal = 0;
let currentJobsHasMore = false;

function toggleAdvancedFilters() {
  const el = document.getElementById('advancedFilters');
  const label = document.getElementById('advFiltersLabel');
  const show = el.style.display === 'none';
  el.style.display = show ? 'grid' : 'none';
  if (label) label.textContent = show ? 'Hide filters' : 'More filters';
}

function autoFillJobLocation() {
  const input = document.getElementById('jobLocation');
  if (input && !input.value && currentProfile && currentProfile.location) {
    input.value = currentProfile.location;
  }
}

async function searchJobsV2(page) {
  page = page || 1;
  currentJobsPage = page;
  const container = document.getElementById('jobsResultsContainer');
  container.innerHTML = '<div class="bg-background-dark border border-primary/10 rounded-2xl p-8 dash-panel text-center"><div class="spinner inline-block"></div><div class="text-xs text-slate-500 mt-3">Searching jobs…</div></div>';
  document.getElementById('jobsPagination').innerHTML = '';

  const remoteFilter = document.getElementById('jobRemoteFilter').value;
  const includeRemote = remoteFilter !== 'onsite';

  const payload = {
    location_filter: document.getElementById('jobLocation').value.trim(),
    include_remote: includeRemote,
    max_results: 10,
    page,
    sort_by: document.getElementById('jobSortBy').value || 'relevance',
  };
  const jt = document.getElementById('jobTypeFilter').value;
  if (jt) payload.job_type = jt;
  const exp = document.getElementById('jobExpLevel').value;
  if (exp) payload.experience_level = exp;
  const smin = parseInt(document.getElementById('jobSalaryMin').value);
  if (!isNaN(smin) && smin > 0) payload.salary_min = smin;
  const smax = parseInt(document.getElementById('jobSalaryMax').value);
  if (!isNaN(smax) && smax > 0) payload.salary_max = smax;
  const dp = document.getElementById('jobDatePosted').value;
  if (dp) payload.date_posted = dp;

  try {
    const d = await api('POST', '/api/jobs/search/v2', payload);
    const jobs = d.jobs || [];
    currentJobsTotal = d.total || 0;
    currentJobsHasMore = !!d.has_more;
    renderJobCards(jobs);
    renderJobPagination();
    if (jobs.length) {
      showJobsAiInsight();
      toast('Found ' + jobs.length + ' jobs', 'success');
    } else {
      showEmptyJobsState();
    }
  } catch (err) {
    container.innerHTML = '<div class="bg-background-dark border border-primary/10 rounded-2xl p-6 dash-panel text-center text-sm text-red-400">⚠ ' + escapeHtml(err.message) + '</div>';
    toast(err.message, 'error');
  }
}

// escapeHtml / matchBadgeClass / workTypeLabel / formatSalary live in core.js — they
// are cross-cutting helpers used by kanban.js, dashboard.js, prepare.js, and insights.js.

function renderJobCards(jobs) {
  const container = document.getElementById('jobsResultsContainer');
  if (!jobs || !jobs.length) { showEmptyJobsState(); return; }

  const frag = document.createDocumentFragment();
  const wrap = document.createElement('div');
  wrap.className = 'bg-background-dark border border-primary/10 rounded-2xl p-4 md:p-5 dash-panel';
  const header = document.createElement('div');
  header.className = 'flex items-center justify-between mb-3';
  header.innerHTML = '<div class="text-sm font-bold">Showing ' + jobs.length + ' of ' + currentJobsTotal + ' jobs</div>';
  wrap.appendChild(header);

  jobs.forEach(job => {
    const card = document.createElement('div');
    card.className = 'job-card';
    const scoreText = job.match_score != null ? Math.round(job.match_score) : '–';
    const badgeCls = matchBadgeClass(job.match_score);
    const salary = formatSalary(job);
    const workTag = workTypeLabel(job);

    const head = document.createElement('div');
    head.className = 'job-card-head';
    const titleWrap = document.createElement('div');
    titleWrap.style.flex = '1';
    titleWrap.style.minWidth = '0';
    const tTitle = document.createElement('div'); tTitle.className = 'job-card-title'; tTitle.textContent = job.title || 'Untitled';
    const tCompany = document.createElement('div'); tCompany.className = 'job-card-company'; tCompany.textContent = (job.company || '') + (job.location ? ' · ' + job.location : '');
    titleWrap.appendChild(tTitle); titleWrap.appendChild(tCompany);
    const badge = document.createElement('div'); badge.className = 'match-badge ' + badgeCls; badge.textContent = scoreText;
    head.appendChild(titleWrap); head.appendChild(badge);
    card.appendChild(head);

    const meta = document.createElement('div'); meta.className = 'job-card-meta';
    const tagWork = document.createElement('span'); tagWork.className = 'work-tag'; tagWork.textContent = workTag; meta.appendChild(tagWork);
    if (salary) { const s = document.createElement('span'); s.innerHTML = '<span class="material-symbols-outlined text-xs">payments</span> ' + escapeHtml(salary); meta.appendChild(s); }
    if (job.posted_date) { const d = document.createElement('span'); d.innerHTML = '<span class="material-symbols-outlined text-xs">schedule</span> ' + escapeHtml(job.posted_date); meta.appendChild(d); }
    card.appendChild(meta);

    if (job.match_rationale) {
      const rat = document.createElement('div');
      rat.className = 'text-xs text-slate-500 mt-2 leading-relaxed';
      rat.textContent = job.match_rationale.slice(0, 180) + (job.match_rationale.length > 180 ? '…' : '');
      card.appendChild(rat);
    }

    const actions = document.createElement('div'); actions.className = 'job-card-actions';
    const viewBtn = document.createElement('button'); viewBtn.className = 'primary';
    viewBtn.innerHTML = '<span class="material-symbols-outlined text-sm">visibility</span> View';
    viewBtn.addEventListener('click', () => openJobDetail(job.id));
    const saveBtn = document.createElement('button');
    saveBtn.innerHTML = job.is_saved
      ? '<span class="material-symbols-outlined text-sm">bookmark</span> Saved'
      : '<span class="material-symbols-outlined text-sm">bookmark_border</span> Save';
    saveBtn.addEventListener('click', () => toggleSaveJob(job.id, !job.is_saved, saveBtn));
    actions.appendChild(viewBtn); actions.appendChild(saveBtn);
    card.appendChild(actions);

    wrap.appendChild(card);
  });

  frag.appendChild(wrap);
  container.innerHTML = '';
  container.appendChild(frag);
}

function renderJobPagination() {
  const p = document.getElementById('jobsPagination');
  if (!currentJobsTotal) { p.innerHTML = ''; return; }
  const div = document.createElement('div');
  div.className = 'pagination';
  const prev = document.createElement('button'); prev.textContent = '← Prev';
  prev.disabled = currentJobsPage <= 1;
  prev.addEventListener('click', () => searchJobsV2(currentJobsPage - 1));
  const info = document.createElement('span'); info.className = 'page-info'; info.textContent = 'Page ' + currentJobsPage;
  const next = document.createElement('button'); next.textContent = 'Next →';
  next.disabled = !currentJobsHasMore;
  next.addEventListener('click', () => searchJobsV2(currentJobsPage + 1));
  div.appendChild(prev); div.appendChild(info); div.appendChild(next);
  p.innerHTML = ''; p.appendChild(div);
}

function showEmptyJobsState() {
  document.getElementById('jobsResultsContainer').innerHTML =
    '<div class="bg-background-dark border border-primary/10 rounded-2xl p-8 dash-panel text-center">' +
    '<span class="material-symbols-outlined text-primary/30 text-5xl mb-3 block">search_off</span>' +
    '<div class="text-sm font-semibold text-slate-400 mb-1">No jobs matched those filters</div>' +
    '<div class="text-xs text-slate-500">Try a broader location, different job type, or lower the salary floor.</div></div>';
}

function showJobsAiInsight() {
  const el = document.getElementById('jobsAiInsight');
  const txt = document.getElementById('jobsAiInsightText');
  if (!el || !txt || !currentProfile) return;
  const skills = (currentProfile.skills || []).slice(0, 3).join(', ');
  const role = (currentProfile.desired_roles || [])[0] || 'your target role';
  if (skills) {
    txt.textContent = 'Your ' + skills + ' skills match well with ' + role + ' roles. Try adjusting the sort to "Newest" to surface fresh listings.';
    el.style.display = 'flex';
  }
}

async function toggleSaveJob(jobId, save, btn) {
  try {
    const d = await api(save ? 'POST' : 'DELETE', '/api/jobs/' + encodeURIComponent(jobId) + '/save');
    if (btn) {
      btn.innerHTML = d.saved
        ? '<span class="material-symbols-outlined text-sm">bookmark</span> Saved'
        : '<span class="material-symbols-outlined text-sm">bookmark_border</span> Save';
    }
    toast(d.message || (d.saved ? 'Saved' : 'Unsaved'), 'success');
  } catch (err) { toast(err.message, 'error'); }
}

async function openJobDetail(jobId) {
  // Close any previously-open panel so clicking another card doesn't stack orphans.
  document.querySelectorAll('.job-detail-backdrop, .job-detail-panel').forEach(el => el.remove());
  selectedJobId = jobId;
  const backdrop = document.createElement('div'); backdrop.className = 'job-detail-backdrop';
  const panel = document.createElement('div'); panel.className = 'job-detail-panel';
  panel.innerHTML = '<button class="job-detail-close" title="Close"><span class="material-symbols-outlined">close</span></button><div class="text-center py-8"><div class="spinner inline-block"></div><div class="text-xs text-slate-500 mt-3">Loading details…</div></div>';
  document.body.appendChild(backdrop);
  document.body.appendChild(panel);
  const close = () => { backdrop.remove(); panel.remove(); selectedJobId = null; };
  backdrop.addEventListener('click', close);
  panel.querySelector('.job-detail-close').addEventListener('click', close);

  try {
    const j = await api('GET', '/api/jobs/' + encodeURIComponent(jobId));
    const scoreText = j.match_score != null ? Math.round(j.match_score) : '–';
    const badgeCls = matchBadgeClass(j.match_score);
    const salary = formatSalary(j);
    const reqsHtml = (j.requirements || []).map(r => '<li class="md-bullet"><span class="md-bullet-dot">•</span><span>' + escapeHtml(r) + '</span></li>').join('');
    const niceHtml = (j.nice_to_have || []).map(r => '<li class="md-bullet"><span class="md-bullet-dot">•</span><span>' + escapeHtml(r) + '</span></li>').join('');

    const html =
      '<button class="job-detail-close" title="Close"><span class="material-symbols-outlined">close</span></button>' +
      '<div class="flex items-start gap-3 mb-4 pr-10">' +
        '<div class="flex-1 min-w-0">' +
          '<div class="text-xl font-bold mb-1">' + escapeHtml(j.title) + '</div>' +
          '<div class="text-sm text-sage mb-1">' + escapeHtml(j.company) + ' · ' + escapeHtml(j.location || '') + '</div>' +
          '<div class="flex flex-wrap gap-2 mt-2">' +
            '<span class="work-tag">' + escapeHtml(workTypeLabel(j)) + '</span>' +
            (salary ? '<span class="work-tag">' + escapeHtml(salary) + '</span>' : '') +
            (j.source_platform ? '<span class="work-tag">' + escapeHtml(j.source_platform) + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<div class="match-badge ' + badgeCls + '">' + scoreText + '</div>' +
      '</div>' +
      (j.match_rationale ? '<div class="ai-insight"><span class="material-symbols-outlined ai-icon">auto_awesome</span><div>' + escapeHtml(j.match_rationale) + '</div></div>' : '') +
      '<div class="response-area text-sm mb-3"><h3>Description</h3>' + md(j.description || 'No description available.') + '</div>' +
      (reqsHtml ? '<div class="response-area text-sm mb-3"><h3>Requirements</h3><ul>' + reqsHtml + '</ul></div>' : '') +
      (niceHtml ? '<div class="response-area text-sm mb-3"><h3>Nice to have</h3><ul>' + niceHtml + '</ul></div>' : '') +
      '<div class="flex flex-col gap-2 mt-4">' +
        '<button data-action="resume" class="bg-primary text-white font-bold py-2.5 px-4 rounded-xl text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-sm">description</span> Generate Resume</button>' +
        '<button data-action="cover" class="border border-primary/25 text-primary font-bold py-2.5 px-4 rounded-xl text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-sm">mail</span> Generate Cover Letter</button>' +
        '<button data-action="track" class="border border-primary/25 text-primary font-bold py-2.5 px-4 rounded-xl text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-sm">add_task</span> Track Application</button>' +
        (j.source_url ? '<a href="' + escapeHtml(j.source_url) + '" target="_blank" rel="noopener" class="text-center border border-primary/25 text-primary font-bold py-2.5 px-4 rounded-xl text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-sm">open_in_new</span> Apply externally</a>' : '') +
      '</div>';

    panel.innerHTML = typeof DOMPurify !== 'undefined'
      ? DOMPurify.sanitize(html, { ADD_ATTR: ['target', 'rel', 'data-action'] })
      : html;
    // Re-wire close + action buttons after innerHTML replacement
    const newClose = panel.querySelector('.job-detail-close');
    if (newClose) newClose.addEventListener('click', close);
    const rBtn = panel.querySelector('[data-action="resume"]');
    if (rBtn) rBtn.addEventListener('click', () => { close(); fromDetailGenerateResume(j.id); });
    const cBtn = panel.querySelector('[data-action="cover"]');
    if (cBtn) cBtn.addEventListener('click', () => { close(); fromDetailGenerateCoverLetter(j.id); });
    const tBtn = panel.querySelector('[data-action="track"]');
    if (tBtn) tBtn.addEventListener('click', () => { close(); fromDetailTrackApp(j.id); });
  } catch (err) {
    panel.innerHTML = '<button class="job-detail-close"><span class="material-symbols-outlined">close</span></button><div class="text-center py-8 text-red-400 text-sm">⚠ ' + escapeHtml(err.message) + '</div>';
    panel.querySelector('.job-detail-close').addEventListener('click', close);
  }
}

function fromDetailGenerateResume(id) {
  nav('docs');
  setTimeout(() => { document.getElementById('resumeJobId').value = id; genResume(); }, 150);
}
function fromDetailGenerateCoverLetter(id) {
  nav('docs');
  setTimeout(() => { document.getElementById('clJobId').value = id; genCoverLetter(); }, 150);
}
function fromDetailTrackApp(id) {
  nav('tracker');
  setTimeout(() => { document.getElementById('trackJobId').value = id; trackApp(); }, 150);
}
