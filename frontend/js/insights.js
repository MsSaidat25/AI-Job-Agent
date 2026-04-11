// insights.js -- Offers, Insights tabs, Document templates & export
// Extracted from app.js lines 1433-1579. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ═══════════════════════════════════════════════════
// OFFERS
// ═══════════════════════════════════════════════════
async function createOffer() {
  const payload = {
    company: document.getElementById('offerCompany').value.trim(),
    role: document.getElementById('offerRole').value.trim(),
    base_salary: parseInt(document.getElementById('offerBase').value) || 0,
    benefits: document.getElementById('offerBenefits').value.trim(),
    location: document.getElementById('offerLocation').value.trim(),
    remote: document.getElementById('offerRemote').value === 'true',
  };
  const bonus = parseInt(document.getElementById('offerBonus').value);
  if (!isNaN(bonus) && bonus > 0) payload.bonus = bonus;
  const eq = document.getElementById('offerEquity').value.trim(); if (eq) payload.equity = eq;
  const dl = document.getElementById('offerDeadline').value; if (dl) payload.deadline = dl;
  if (!payload.company || !payload.role || payload.base_salary <= 0) { toast('Company, role, and base salary are required', 'error'); return; }
  try {
    await api('POST', '/api/offers/', payload);
    toast('Offer saved', 'success');
    ['offerCompany','offerRole','offerBase','offerBonus','offerEquity','offerLocation','offerDeadline','offerBenefits'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    loadOffers();
  } catch (err) { toast(err.message, 'error'); }
}

async function loadOffers() {
  const el = document.getElementById('offersList');
  try {
    const d = await api('GET', '/api/offers/');
    if (!d.offers || !d.offers.length) { el.innerHTML = '<div class="text-xs text-slate-500">No offers logged yet.</div>'; return; }
    el.innerHTML = '';
    d.offers.forEach(o => {
      const card = document.createElement('div'); card.className = 'salary-card';
      const total = (o.base_salary || 0) + (o.bonus || 0);
      card.innerHTML =
        '<div class="flex items-center justify-between"><div class="salary-location">' + escapeHtml(o.company) + '</div><span class="work-tag">' + escapeHtml(o.status || 'pending') + '</span></div>' +
        '<div class="salary-range">' + escapeHtml(o.role) + '</div>' +
        '<div class="salary-meta">Base: $' + (o.base_salary || 0).toLocaleString() + (o.bonus ? ' · Bonus: $' + o.bonus.toLocaleString() : '') + (o.equity ? ' · Equity: ' + escapeHtml(o.equity) : '') + '</div>' +
        '<div class="salary-meta">Total comp: $' + total.toLocaleString() + ' · ' + escapeHtml(o.location || '–') + (o.remote ? ' (Remote)' : '') + '</div>';
      el.appendChild(card);
    });
  } catch (err) { el.innerHTML = '<div class="text-xs text-slate-500">Could not load offers.</div>'; }
}

async function compareOffers() {
  const panel = document.getElementById('offerComparePanel');
  panel.style.display = 'block';
  setLoading('offerCompareResult');
  try { const d = await api('GET', '/api/offers/compare'); setResult('offerCompareResult', d.response); }
  catch (err) { setResult('offerCompareResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

// ═══════════════════════════════════════════════════
// INSIGHTS TABS
// ═══════════════════════════════════════════════════
const _insightLoaded = {};
const INSIGHT_PANELS = {
  overview:  'insightOverview',
  outcome:   'insightOutcome',
  rejection: 'insightRejection',
  weekly:    'insightWeekly',
  restrat:   'insightRestrat',
};
const INSIGHT_FETCHERS = {
  overview:  () => api('GET', '/api/analytics').then(d => d.response),
  outcome:   () => api('GET', '/api/insights/outcome-learning').then(d =>
    (d.winning_patterns ? '## Winning Patterns\n' + d.winning_patterns.map(p => '- ' + p).join('\n') + '\n\n' : '') + (d.analysis || '')
  ),
  rejection: () => api('GET', '/api/insights/rejection-patterns').then(d =>
    (d.common_reasons ? '## Common Reasons\n' + d.common_reasons.map(p => '- ' + p).join('\n') + '\n\n' : '') + (d.analysis || '')
  ),
  weekly:    () => api('GET', '/api/insights/weekly-report').then(d => d.response),
  restrat:   () => api('GET', '/api/insights/restrategize').then(d => d.response),
};

async function switchInsightTab(tab) {
  document.querySelectorAll('#view-analytics .tab-item').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector('#view-analytics .tab-item[data-tab="' + tab + '"]');
  if (btn) btn.classList.add('active');
  Object.values(INSIGHT_PANELS).forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
  const panelId = INSIGHT_PANELS[tab];
  const show = document.getElementById(panelId);
  if (show) show.style.display = '';
  if (!panelId || _insightLoaded[tab]) return;

  setLoading(panelId);
  try {
    const body = await INSIGHT_FETCHERS[tab]();
    setResult(panelId, body);
    _insightLoaded[tab] = true;  // cache only on success so errors are retryable
  } catch (err) {
    setResult(panelId, '⚠ ' + err.message);
  }
}

// ═══════════════════════════════════════════════════
// DOCUMENTS — templates + export
// ═══════════════════════════════════════════════════
let selectedTemplateId = 'classic';
let lastGeneratedResumeContent = '';

async function loadTemplates() {
  const grid = document.getElementById('templateGrid');
  if (grid.dataset.loaded === '1' || grid.dataset.loading === '1') return;
  grid.dataset.loading = '1';  // set before await so rapid re-nav doesn't double-fetch
  try {
    const d = await api('GET', '/api/documents/templates');
    grid.innerHTML = '';
    (d.templates || []).forEach(t => {
      const card = document.createElement('div');
      card.className = 'template-card' + (t.id === selectedTemplateId ? ' selected' : '');
      card.dataset.templateId = t.id;
      card.innerHTML = '<div class="template-card-name">' + escapeHtml(t.name) + '</div><div class="template-card-desc">' + escapeHtml(t.description || '') + '</div>';
      card.addEventListener('click', () => {
        selectedTemplateId = t.id;
        grid.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
      });
      grid.appendChild(card);
    });
    grid.dataset.loaded = '1';
  } catch (err) {
    grid.innerHTML = '<div class="text-xs text-slate-500 col-span-full text-center py-4">Could not load templates.</div>';
  } finally {
    delete grid.dataset.loading;  // clear so a subsequent nav can retry after a failure
  }
}

async function downloadResume() {
  const jobId = document.getElementById('resumeJobId').value.trim();
  if (!jobId) { toast('Enter a Job ID', 'error'); return; }
  const format = document.getElementById('docFormat').value || 'pdf';
  const tone = document.getElementById('resumeTone').value || 'professional';
  try {
    toast('Generating ' + format.toUpperCase() + '…', 'info');
    const h = { 'Content-Type': 'application/json' };
    if (sessionId) h['X-Session-ID'] = sessionId;
    const r = await fetch(API + '/api/documents/export', {
      method: 'POST', headers: h,
      body: JSON.stringify({ job_id: jobId, template_id: selectedTemplateId, format, tone }),
    });
    if (!r.ok) { const err = await r.json().catch(() => ({})); throw new Error(err.detail || 'Export failed'); }
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'resume.' + format;
    a.click();
    toast('Downloaded', 'success');
  } catch (err) { toast(err.message, 'error'); }
}
