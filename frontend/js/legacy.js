// legacy.js -- Legacy single-call handlers: market/tips/docs/track/update/analytics/feedback
// Extracted from app.js lines 757-818. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.


async function getMarket() {
  const r = document.getElementById('mktRegion').value.trim(), i = document.getElementById('mktIndustry').value.trim();
  if (!r || !i) { toast('Enter both region and industry', 'error'); return; }
  setLoading('marketResult');
  try { const d = await api('POST', '/api/market-insights', { region: r, industry: i }); setResult('marketResult', d.response); }
  catch (err) { setResult('marketResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

async function getTips() {
  const r = document.getElementById('tipsRegion').value.trim(); if (!r) { toast('Enter a region', 'error'); return; }
  setLoading('tipsResult');
  try { const d = await api('POST', '/api/application-tips', { region: r }); setResult('tipsResult', d.response); }
  catch (err) { setResult('tipsResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

async function genResume() {
  const id = document.getElementById('resumeJobId').value.trim(); if (!id) { toast('Enter a Job ID', 'error'); return; }
  setLoading('resumeResult');
  try { const d = await api('POST', '/api/documents/resume', { job_id: id, tone: document.getElementById('resumeTone').value }); setResult('resumeResult', d.response); }
  catch (err) { setResult('resumeResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

async function genCoverLetter() {
  const id = document.getElementById('clJobId').value.trim(); if (!id) { toast('Enter a Job ID', 'error'); return; }
  setLoading('coverResult');
  try { const d = await api('POST', '/api/documents/cover-letter', { job_id: id }); setResult('coverResult', d.response); }
  catch (err) { setResult('coverResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

async function trackApp() {
  const id = document.getElementById('trackJobId').value.trim(); if (!id) { toast('Enter a Job ID', 'error'); return; }
  setLoading('trackResult');
  try { const d = await api('POST', '/api/applications', { job_id: id, notes: document.getElementById('trackNotes').value.trim() }); setResult('trackResult', d.response); toast('Application tracked!', 'success'); }
  catch (err) { setResult('trackResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

function openUpdateModal() {
  const id = document.getElementById('updateAppId').value.trim();
  if (!id) { toast('Enter an Application ID', 'error'); return; }
  updateTargetId = id; document.getElementById('updateModal').classList.remove('hidden');
}
function closeUpdateModal() { document.getElementById('updateModal').classList.add('hidden'); updateTargetId = null; }
async function submitUpdate() {
  if (!updateTargetId) return;
  try {
    await api('PUT', '/api/applications/' + updateTargetId, { new_status: document.getElementById('updateStatus').value, feedback: document.getElementById('updateFeedback').value.trim() || null, notes: document.getElementById('updateNotes').value.trim() || null });
    closeUpdateModal(); toast('Updated!', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

async function loadAnalytics() {
  setLoading('analyticsResult');
  try { const d = await api('GET', '/api/analytics'); setResult('analyticsResult', d.response); }
  catch (err) { setResult('analyticsResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}

async function loadFeedback() {
  setLoading('feedbackResult');
  try { const d = await api('GET', '/api/feedback'); setResult('feedbackResult', d.response); }
  catch (err) { setResult('feedbackResult', '⚠ ' + err.message); toast(err.message, 'error'); }
}
