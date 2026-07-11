/* ============================================================
   tablet_rules.js — Grimorio táctil para tablet
   ============================================================ */

'use strict';

let currentTab = 'monsters';
let allData    = { monsters: [], spells: [], rules: [] };
let filtered   = [];

// ── Init ──────────────────────────────────────────────────

function init() {
  try {
    allData.monsters = JSON.parse(document.getElementById('grim-monsters').textContent || '[]');
    allData.spells   = JSON.parse(document.getElementById('grim-spells').textContent   || '[]');
    allData.rules    = JSON.parse(document.getElementById('grim-rules').textContent    || '[]');
  } catch { /* silent */ }

  switchTab('monsters');
}

// ── Tabs ──────────────────────────────────────────────────

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.rtab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('rules-search').value = '';
  renderCards(allData[tab]);
}

function filterCards() {
  const q = document.getElementById('rules-search').value.trim().toLowerCase();
  const data = allData[currentTab];
  if (!q) { renderCards(data); return; }
  renderCards(data.filter(item => {
    const title = (item.title || item.nombre || item.name || '').toLowerCase();
    return title.includes(q);
  }));
}

// ── Render cards ──────────────────────────────────────────

function renderCards(items) {
  filtered = items;
  const list = document.getElementById('rules-card-list');
  if (!list) return;

  if (!items || items.length === 0) {
    list.innerHTML = '<div class="empty-state">Sin resultados</div>';
    return;
  }

  list.innerHTML = items.map((item, i) => {
    const title = item.title || item.nombre || item.name || '(sin nombre)';
    const sub   = item.type || item.category || item.tipo || '';
    const slug  = item.slug || slugify(title);
    const ctype = tabToCtype(currentTab);
    return `
    <div class="rules-card" onclick="openDetail('${esc(ctype)}', '${esc(slug)}')">
      <strong class="card-title">${esc(title)}</strong>
      ${sub ? `<span class="card-sub">${esc(sub)}</span>` : ''}
    </div>`;
  }).join('');
}

// ── Detail modal ──────────────────────────────────────────

async function openDetail(ctype, slug) {
  const modal = document.getElementById('rt-modal');
  const body  = document.getElementById('rt-modal-body');
  body.innerHTML = '<div class="loading-state">Cargando...</div>';
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  try {
    const res = await fetch(`/content/${ctype}/${slug}`);
    if (!res.ok) throw new Error('not found');
    const html = await res.text();
    body.innerHTML = html;
  } catch {
    body.innerHTML = '<div class="error-state">No se pudo cargar el contenido.</div>';
  }
}

function closeModal() {
  document.getElementById('rt-modal').classList.add('hidden');
  document.body.style.overflow = '';
}

// Close on Escape
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── Helpers ───────────────────────────────────────────────

function tabToCtype(tab) {
  if (tab === 'monsters') return 'monster';
  if (tab === 'spells')   return 'spell';
  return 'rule';
}

function slugify(s) {
  return String(s).toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Boot ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
