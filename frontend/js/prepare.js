// prepare.js -- Salary calibration, Daily Feed, Career Dreamer, Interview Prep
// Extracted from app.js lines 1194-1432. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ═══════════════════════════════════════════════════
// SALARY
// ═══════════════════════════════════════════════════
function prefillSalaryForm() {
  if (!currentProfile) return;
  const roleInput = document.getElementById('salaryRole');
  const locInput = document.getElementById('salaryLocations');
  if (roleInput && !roleInput.value && currentProfile.desired_roles && currentProfile.desired_roles[0]) {
    roleInput.value = currentProfile.desired_roles[0];
  }
  if (locInput && !locInput.value && currentProfile.location) {
    locInput.value = currentProfile.location;
  }
  const negRoleInput = document.getElementById('negRole');
  if (negRoleInput && !negRoleInput.value && currentProfile.desired_roles && currentProfile.desired_roles[0]) {
    negRoleInput.value = currentProfile.desired_roles[0];
  }
}

async function calibrateSalary() {
  const role = document.getElementById('salaryRole').value.trim();
  const locs = document.getElementById('salaryLocations').value.split(',').map(s => s.trim()).filter(Boolean);
  if (!role) { toast('Enter a role', 'error'); return; }
  const panel = document.getElementById('salaryResults');
  const dataEl = document.getElementById('salaryDataPoints');
  const sumEl = document.getElementById('salaryMarketSummary');
  panel.style.display = 'block';
  dataEl.innerHTML = '<div class="text-center py-4"><div class="spinner inline-block"></div><div class="text-xs text-slate-500 mt-2">Calibrating…</div></div>';
  sumEl.innerHTML = '';
  try {
    const d = await api('POST', '/api/salary/calibrate', { role, locations: locs.length ? locs : ['United States'], skills: (currentProfile && currentProfile.skills) || [] });
    dataEl.innerHTML = '';
    (d.data_points || []).forEach(dp => {
      const card = document.createElement('div'); card.className = 'salary-card';
      const loc = dp.location || dp.city || 'Unknown';
      const range = (dp.min != null && dp.max != null) ? (dp.currency || '$') + Math.round(dp.min/1000) + 'k – ' + Math.round(dp.max/1000) + 'k' : (dp.median ? (dp.currency || '$') + Math.round(dp.median/1000) + 'k' : '–');
      const source = dp.source || dp.sample_size || '';
      card.innerHTML = '<div class="salary-location">' + escapeHtml(loc) + '</div><div class="salary-range">' + escapeHtml(range) + '</div><div class="salary-meta">' + escapeHtml(String(source)) + '</div>';
      dataEl.appendChild(card);
    });
    sumEl.innerHTML = md(d.market_summary || '') + (d.arbitrage_analysis ? '<h3>Arbitrage</h3>' + md(d.arbitrage_analysis) : '');
    if (typeof DOMPurify !== 'undefined') sumEl.innerHTML = DOMPurify.sanitize(sumEl.innerHTML);
  } catch (err) {
    dataEl.innerHTML = '<div class="text-xs text-red-400">⚠ ' + escapeHtml(err.message) + '</div>';
  }
}

async function negotiateSalary() {
  const curr = parseInt(document.getElementById('negCurrentOffer').value);
  if (!curr || curr < 0) { toast('Enter your current offer', 'error'); return; }
  const role = document.getElementById('negRole').value.trim() || 'this role';
  const payload = {
    current_offer: curr,
    role,
    company: document.getElementById('negCompany').value.trim(),
    leverage_points: document.getElementById('negLeverage').value.split('\n').map(s => s.trim()).filter(Boolean),
  };
  const comp = parseInt(document.getElementById('negCompetingOffer').value);
  if (!isNaN(comp) && comp > 0) payload.competing_offer = comp;
  setLoading('negResult');
  try { const d = await api('POST', '/api/salary/negotiate', payload); setResult('negResult', d.response); }
  catch (err) { setResult('negResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

// ═══════════════════════════════════════════════════
// DAILY FEED
// ═══════════════════════════════════════════════════
async function loadDailyFeed() {
  const list = document.getElementById('feedItems');
  list.innerHTML = '<div class="text-center py-8 text-slate-500 text-sm"><div class="spinner inline-block"></div><div class="mt-3">Loading your daily feed…</div></div>';
  try { const d = await api('GET', '/api/feed/daily'); renderFeed(d); }
  catch (err) { list.innerHTML = '<div class="text-xs text-red-400 text-center py-6">⚠ ' + escapeHtml(err.message) + '</div>'; }
}

async function refreshFeed() {
  const list = document.getElementById('feedItems');
  list.innerHTML = '<div class="text-center py-8 text-slate-500 text-sm"><div class="spinner inline-block"></div><div class="mt-3">Refreshing…</div></div>';
  try { const d = await api('POST', '/api/feed/refresh'); renderFeed(d); toast('Feed refreshed', 'success'); }
  catch (err) { list.innerHTML = '<div class="text-xs text-red-400 text-center py-6">⚠ ' + escapeHtml(err.message) + '</div>'; }
}

function renderFeed(d) {
  const sumEl = document.getElementById('feedSummary');
  const sumTxt = document.getElementById('feedSummaryText');
  if (d.summary) {
    sumEl.style.display = 'block';
    sumTxt.textContent = d.summary;
  } else { sumEl.style.display = 'none'; }
  const list = document.getElementById('feedItems');
  const items = d.items || [];
  if (!items.length) {
    list.innerHTML = '<div class="text-center py-8 text-xs text-slate-500">No picks yet. Try refreshing or search jobs directly.</div>';
    return;
  }
  list.innerHTML = '';
  items.forEach(i => {
    const card = document.createElement('div'); card.className = 'job-card';
    const score = i.match_score != null ? Math.round(i.match_score) : '–';
    const badgeCls = matchBadgeClass(i.match_score);
    card.innerHTML =
      '<div class="job-card-head">' +
        '<div style="flex:1;min-width:0">' +
          '<div class="job-card-title">' + escapeHtml(i.title) + '</div>' +
          '<div class="job-card-company">' + escapeHtml(i.company) + ' · ' + escapeHtml(i.location || '') + '</div>' +
        '</div>' +
        '<div class="match-badge ' + badgeCls + '">' + score + '</div>' +
      '</div>' +
      (i.annotation ? '<div class="text-xs text-slate-500 mt-2 leading-relaxed">' + escapeHtml(i.annotation) + '</div>' : '');
    const actions = document.createElement('div'); actions.className = 'job-card-actions';
    const viewBtn = document.createElement('button'); viewBtn.className = 'primary';
    viewBtn.innerHTML = '<span class="material-symbols-outlined text-sm">visibility</span> View';
    viewBtn.addEventListener('click', () => openJobDetail(i.job_id));
    actions.appendChild(viewBtn);
    card.appendChild(actions);
    list.appendChild(card);
  });
}

// ═══════════════════════════════════════════════════
// CAREER DREAMER
// ═══════════════════════════════════════════════════
let currentDreamId = null;

async function createDream() {
  const role = document.getElementById('dreamRole').value.trim();
  if (!role) { toast('Enter a dream role', 'error'); return; }
  const payload = {
    dream_role: role,
    dream_industry: document.getElementById('dreamIndustry').value.trim(),
    dream_location: document.getElementById('dreamLocation').value.trim(),
    timeline_months: parseInt(document.getElementById('dreamTimeline').value) || 12,
  };
  try {
    const d = await api('POST', '/api/career/dream', payload);
    currentDreamId = d.dream_id;
    document.getElementById('dreamResult').style.display = 'block';
    const score = d.feasibility_score != null ? Math.round(d.feasibility_score) : '–';
    document.getElementById('dreamScore').textContent = score + (score !== '–' ? '/100' : '');
    document.getElementById('dreamMeterFill').style.width = (d.feasibility_score != null ? d.feasibility_score : 0) + '%';
    document.getElementById('dreamAnalysis').innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(md(d.analysis || '')) : md(d.analysis || '');
    toast('Dream analyzed', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

async function saveDream() {
  if (!currentDreamId) { toast('Analyze a dream first', 'error'); return; }
  try { await api('POST', '/api/career/dream/' + encodeURIComponent(currentDreamId) + '/save', { analysis: null }); toast('Dream saved', 'success'); loadCareerDreams(); }
  catch (err) { toast(err.message, 'error'); }
}

async function findJobsForDream() {
  if (!currentDreamId) { toast('Analyze a dream first', 'error'); return; }
  try {
    const d = await api('POST', '/api/career/dream/' + encodeURIComponent(currentDreamId) + '/find-jobs');
    nav('jobs');
    setTimeout(() => {
      const loc = document.getElementById('jobLocation');
      if (loc && d.search_terms && d.search_terms.length) { loc.value = d.search_terms.join(' '); }
      searchJobsV2(1);
    }, 200);
  } catch (err) { toast(err.message, 'error'); }
}

async function loadCareerDreams() {
  const el = document.getElementById('dreamsList');
  try {
    const d = await api('GET', '/api/career/dreams');
    if (!d.dreams || !d.dreams.length) { el.innerHTML = '<div class="text-xs text-slate-500">No saved dreams yet.</div>'; return; }
    el.innerHTML = '';
    d.dreams.forEach(dream => {
      const card = document.createElement('div'); card.className = 'salary-card cursor-pointer';
      const feas = dream.feasibility_score != null ? Math.round(dream.feasibility_score) + '/100' : '–';
      card.innerHTML = '<div class="salary-location">' + escapeHtml(dream.dream_industry || 'general') + '</div><div class="salary-range">' + escapeHtml(dream.dream_role) + '</div><div class="salary-meta">Feasibility: ' + escapeHtml(feas) + '</div>';
      el.appendChild(card);
    });
  } catch (err) { el.innerHTML = '<div class="text-xs text-slate-500">Could not load dreams.</div>'; }
}

// ═══════════════════════════════════════════════════
// INTERVIEW PREP
// ═══════════════════════════════════════════════════
const INTERVIEW_PANELS = {
  prep:      'interviewPrep',
  brief:     'interviewBrief',
  questions: 'interviewQuestions',
  debrief:   'interviewDebriefPanel',
};

function switchInterviewTab(tab) {
  document.querySelectorAll('#view-interview .tab-item').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector('#view-interview .tab-item[data-tab="' + tab + '"]');
  if (btn) btn.classList.add('active');
  Object.values(INTERVIEW_PANELS).forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
  const show = document.getElementById(INTERVIEW_PANELS[tab]);
  if (show) show.style.display = '';
}

async function loadPrepPackage() {
  const id = document.getElementById('interviewAppId').value.trim();
  if (!id) { toast('Enter an Application ID', 'error'); return; }
  const prepEl = document.getElementById('interviewPrep');
  const briefEl = document.getElementById('interviewBrief');
  const qEl = document.getElementById('interviewQuestions');
  prepEl.className = 'response-area'; prepEl.innerHTML = '<div class="spinner inline-block"></div> Loading prep…';
  try {
    const [pkg, brief, qs] = await Promise.all([
      api('GET', '/api/interview/' + encodeURIComponent(id) + '/prep'),
      api('GET', '/api/interview/' + encodeURIComponent(id) + '/company-brief').catch(() => null),
      api('GET', '/api/interview/' + encodeURIComponent(id) + '/questions').catch(() => null),
    ]);
    prepEl.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(md(pkg.full_prep || '')) : md(pkg.full_prep || '');
    if (brief) {
      briefEl.className = 'response-area';
      briefEl.innerHTML = '<h3>' + escapeHtml(brief.company || '') + '</h3>' + (typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(md(brief.brief || '')) : md(brief.brief || ''));
    }
    if (qs && qs.questions) {
      qEl.className = 'response-area';
      qEl.innerHTML = qs.questions.map((q, i) =>
        '<div style="margin-bottom:1rem"><div style="font-weight:600;color:#f1f5f9">' + (i + 1) + '. ' + escapeHtml(q.question || '') + '</div>' +
        '<div style="font-size:0.8rem;color:#94a3b8;margin-top:0.25rem">' + escapeHtml(q.suggested_answer || '') + '</div></div>'
      ).join('');
      if (typeof DOMPurify !== 'undefined') qEl.innerHTML = DOMPurify.sanitize(qEl.innerHTML);
    }
    toast('Prep package ready', 'success');
  } catch (err) { prepEl.innerHTML = '⚠ ' + escapeHtml(err.message); toast(err.message, 'error'); }
}

async function submitDebrief() {
  const id = document.getElementById('interviewAppId').value.trim();
  if (!id) { toast('Enter an Application ID above first', 'error'); return; }
  const payload = {
    went_well: document.getElementById('debriefWentWell').value.split('\n').map(s => s.trim()).filter(Boolean),
    could_improve: document.getElementById('debriefImprove').value.split('\n').map(s => s.trim()).filter(Boolean),
    questions_asked: document.getElementById('debriefQuestionsAsked').value.split('\n').map(s => s.trim()).filter(Boolean),
    overall_feeling: document.getElementById('debriefFeeling').value,
    notes: document.getElementById('debriefNotes').value.trim(),
  };
  setLoading('debriefResult');
  try { const d = await api('POST', '/api/interview/' + encodeURIComponent(id) + '/debrief', payload); setResult('debriefResult', d.response); toast('Debrief saved', 'success'); }
  catch (err) { setResult('debriefResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}
