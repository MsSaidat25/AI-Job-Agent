// kanban.js -- Kanban board render, drag-drop, move card, card actions popover
// Extracted from app.js lines 993-1193. Runs as a regular <script> (deferred),
// so top-level declarations land on window and are visible to siblings.

// ═══════════════════════════════════════════════════
// KANBAN BOARD
// ═══════════════════════════════════════════════════
let kanbanDragCard = null;

async function loadKanbanBoard() {
  const container = document.getElementById('kanbanContainer');
  container.innerHTML = '<div class="text-center py-10 text-slate-500 text-sm"><div class="spinner inline-block"></div><div class="mt-3">Loading board…</div></div>';
  try {
    const d = await api('GET', '/api/kanban/board');
    renderKanbanBoard(d);
    checkStaleNudges(d);
  } catch (err) {
    container.innerHTML = '<div class="text-center py-10 text-red-400 text-sm">⚠ ' + escapeHtml(err.message) + '</div>';
  }
}

function renderKanbanBoard(data) {
  const container = document.getElementById('kanbanContainer');
  container.innerHTML = '';
  if (!data.columns || !data.columns.length) {
    container.innerHTML = '<div class="text-center py-10 text-xs text-slate-500">No applications yet. Track your first one above.</div>';
    return;
  }
  const scroll = document.createElement('div'); scroll.className = 'kanban-scroll';
  data.columns.forEach(col => {
    const colEl = document.createElement('div'); colEl.className = 'kanban-column'; colEl.dataset.status = col.status;
    colEl.addEventListener('dragover', e => { e.preventDefault(); colEl.classList.add('drag-over'); });
    colEl.addEventListener('dragleave', () => colEl.classList.remove('drag-over'));
    colEl.addEventListener('drop', async e => {
      e.preventDefault();
      colEl.classList.remove('drag-over');
      if (kanbanDragCard && kanbanDragCard.dataset.cardId && kanbanDragCard.dataset.status !== col.status) {
        await moveKanbanCard(kanbanDragCard.dataset.cardId, col.status);
      }
      kanbanDragCard = null;
    });

    const head = document.createElement('div'); head.className = 'kanban-col-head';
    head.innerHTML = '<div class="kanban-col-dot" style="background:' + col.color + '"></div><div class="kanban-col-label">' + escapeHtml(col.label) + '</div><div class="kanban-col-count">' + (col.cards ? col.cards.length : 0) + '</div>';
    colEl.appendChild(head);

    const cards = document.createElement('div'); cards.className = 'kanban-cards';
    (col.cards || []).forEach(card => {
      const c = document.createElement('div');
      c.className = 'kanban-card';
      c.draggable = true;
      c.dataset.cardId = card.id;
      c.dataset.status = col.status;
      c.addEventListener('dragstart', () => { kanbanDragCard = c; c.classList.add('dragging'); });
      c.addEventListener('dragend', () => c.classList.remove('dragging'));

      const score = card.match_score != null ? Math.round(card.match_score) : null;
      const staleNudge = isStale(card, col.status);
      c.innerHTML =
        '<div class="kanban-card-title">' + escapeHtml(card.job_title || 'Unknown') + '</div>' +
        '<div class="kanban-card-company">' + escapeHtml(card.company || '') + '</div>' +
        '<div class="kanban-card-meta">' +
          '<span>' + (card.submitted_at ? escapeHtml(new Date(card.submitted_at).toLocaleDateString()) : '–') + '</span>' +
          (score != null ? '<span class="match-badge ' + matchBadgeClass(score) + '" style="min-width:1.5rem;height:1.5rem;font-size:0.65rem">' + score + '</span>' : '') +
        '</div>' +
        (card.notes ? '<div class="kanban-card-notes">' + escapeHtml(card.notes) + '</div>' : '') +
        (staleNudge ? '<div class="kanban-nudge"><span class="material-symbols-outlined text-xs">notifications_active</span> Follow up</div>' : '');

      c.addEventListener('click', (e) => openKanbanCardActions(card, e));
      cards.appendChild(c);
    });
    colEl.appendChild(cards);
    scroll.appendChild(colEl);
  });
  container.appendChild(scroll);
}

function isStale(card, status) {
  if (status !== 'submitted') return false;
  if (!card.submitted_at) return false;
  const days = (Date.now() - new Date(card.submitted_at).getTime()) / 86400000;
  return days > 7;
}

function checkStaleNudges(data) {
  let staleCount = 0;
  (data.columns || []).forEach(col => {
    if (col.status === 'submitted') {
      (col.cards || []).forEach(c => { if (isStale(c, col.status)) staleCount++; });
    }
  });
  const el = document.getElementById('kanbanAiInsight');
  const txt = document.getElementById('kanbanAiInsightText');
  if (staleCount > 0) {
    txt.textContent = staleCount + ' application' + (staleCount > 1 ? 's have' : ' has') + ' been in "Applied" for over a week. Consider a follow-up nudge.';
    el.style.display = 'flex';
  } else {
    el.style.display = 'none';
  }
}

async function moveKanbanCard(cardId, newStatus) {
  try {
    await api('PUT', '/api/kanban/cards/' + encodeURIComponent(cardId) + '/move', { new_status: newStatus });
    toast('Moved to ' + newStatus.replace(/_/g, ' '), 'success');
    loadKanbanBoard();
  } catch (err) { toast(err.message, 'error'); }
}

const KANBAN_STATUSES = [
  { key: 'draft',               label: 'Saved',        color: '#6b7280' },
  { key: 'submitted',           label: 'Applied',      color: '#3b82f6' },
  { key: 'under_review',        label: 'Under Review', color: '#f59e0b' },
  { key: 'interview_scheduled', label: 'Interview',    color: '#8b5cf6' },
  { key: 'offer_received',      label: 'Offer',        color: '#10b981' },
  { key: 'rejected',            label: 'Rejected',     color: '#ef4444' },
  { key: 'withdrawn',           label: 'Withdrawn',    color: '#9ca3af' },
];

let _kanbanPopover = null;

function closeKanbanPopover() {
  if (_kanbanPopover) {
    _kanbanPopover.remove();
    _kanbanPopover = null;
    document.removeEventListener('click', _kanbanPopoverOutside, true);
    document.removeEventListener('keydown', _kanbanPopoverEsc);
  }
}
function _kanbanPopoverOutside(e) {
  if (_kanbanPopover && !_kanbanPopover.contains(e.target)) closeKanbanPopover();
}
function _kanbanPopoverEsc(e) { if (e.key === 'Escape') closeKanbanPopover(); }

function openKanbanCardActions(card, event) {
  // Stop the event so the outside-click handler we're about to install does not
  // immediately close the popover we're about to open.
  if (event) event.stopPropagation();
  closeKanbanPopover();

  const pop = document.createElement('div');
  pop.className = 'kanban-popover';

  const header = document.createElement('div');
  header.className = 'kanban-popover-header';
  header.textContent = 'Move "' + (card.job_title || 'card') + '" to';
  pop.appendChild(header);

  KANBAN_STATUSES.forEach(s => {
    if (s.key === card.status) return;  // skip current column
    const btn = document.createElement('button');
    btn.innerHTML = '<span class="kanban-popover-dot" style="background:' + s.color + '"></span><span>' + s.label + '</span>';
    btn.addEventListener('click', () => {
      closeKanbanPopover();
      moveKanbanCard(card.id, s.key);
    });
    pop.appendChild(btn);
  });

  const divider = document.createElement('div');
  divider.className = 'kanban-popover-divider';
  pop.appendChild(divider);

  if (card.source_url) {
    const openBtn = document.createElement('button');
    openBtn.innerHTML = '<span class="material-symbols-outlined text-sm" style="font-size:1rem">open_in_new</span><span>Open job posting</span>';
    openBtn.addEventListener('click', () => {
      closeKanbanPopover();
      window.open(card.source_url, '_blank', 'noopener');
    });
    pop.appendChild(openBtn);
  }
  const viewBtn = document.createElement('button');
  viewBtn.innerHTML = '<span class="material-symbols-outlined text-sm" style="font-size:1rem">visibility</span><span>View job details</span>';
  viewBtn.addEventListener('click', () => {
    closeKanbanPopover();
    if (card.job_id) openJobDetail(card.job_id);
  });
  pop.appendChild(viewBtn);

  document.body.appendChild(pop);

  // Position near click (default: below-right), clamped to viewport
  let x = 20, y = 20;
  if (event) {
    x = event.clientX;
    y = event.clientY + 6;
  }
  const rect = pop.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  if (x + rect.width > vw - 8) x = vw - rect.width - 8;
  if (y + rect.height > vh - 8) y = Math.max(8, vh - rect.height - 8);
  pop.style.left = x + 'px';
  pop.style.top = y + 'px';

  _kanbanPopover = pop;
  // stopPropagation on the opening click (above) keeps this event from reaching
  // the document-level handler we're registering right now — no setTimeout needed.
  document.addEventListener('click', _kanbanPopoverOutside, true);
  document.addEventListener('keydown', _kanbanPopoverEsc);
}
