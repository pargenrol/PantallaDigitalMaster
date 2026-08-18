/* ============================================================
   tablet_rules.js — Grimorio táctil para tablet
   ============================================================ */

'use strict';

let currentTab = 'monsters';
let allData    = { monsters: [], spells: [], rules: [] };
let filtered   = [];

// Filtros activos (solo tienen efecto en AD&D2e): clase/nivel para conjuros, DG para monstruos.
let activeClase = '';
let activeNivel = '';
let activeDg    = '';

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
  activeClase = '';
  activeNivel = '';
  activeDg    = '';
  document.querySelectorAll('.rtab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('rules-search').value = '';
  renderFilterControls();
  filterCards();
}

function renderFilterControls() {
  const wrap = document.getElementById('rules-filter-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';
  if (!IS_ADND2E) return;

  if (currentTab === 'spells') {
    wrap.appendChild(buildFilterRow('Clase', [['', 'Todas'], ['Mago', 'Mago'], ['Clérigo', 'Clérigo']], activeClase, v => {
      activeClase = v; filterCards();
    }));
    const niveles = [['', 'Todos']];
    for (let n = 1; n <= 9; n++) niveles.push([String(n), String(n)]);
    niveles.push(['?', 'Sin confirmar']);
    wrap.appendChild(buildFilterRow('Nivel', niveles, activeNivel, v => {
      activeNivel = v; filterCards();
    }));
  } else if (currentTab === 'monsters') {
    const dgs = [['', 'Todos']];
    for (let n = 1; n <= 10; n++) dgs.push([String(n), String(n)]);
    dgs.push(['11+', '11+']);
    dgs.push(['?', 'Sin confirmar']);
    wrap.appendChild(buildFilterRow('DG', dgs, activeDg, v => {
      activeDg = v; filterCards();
    }));
  }
}

function buildFilterRow(label, options, activeValue, onPick) {
  const row = document.createElement('div');
  row.className = 'rules-filter-row';
  const lbl = document.createElement('span');
  lbl.className = 'rules-filter-label';
  lbl.textContent = label + ':';
  row.appendChild(lbl);
  options.forEach(([value, text]) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rfilter-btn' + (value === activeValue ? ' active' : '');
    btn.textContent = text;
    btn.addEventListener('click', () => {
      onPick(value);
      row.querySelectorAll('.rfilter-btn').forEach(b => b.classList.toggle('active', b === btn));
    });
    row.appendChild(btn);
  });
  return row;
}

function filterCards() {
  const q = document.getElementById('rules-search').value.trim().toLowerCase();
  let data = allData[currentTab];

  if (currentTab === 'spells') {
    if (activeClase) data = data.filter(item => item.clase === activeClase);
    if (activeNivel) {
      data = data.filter(item => {
        const nivel = (item.nivel === undefined || item.nivel === null) ? '' : String(item.nivel);
        return activeNivel === '?' ? nivel === '' : nivel === activeNivel;
      });
    }
  } else if (currentTab === 'monsters') {
    if (activeDg) {
      data = data.filter(item => {
        const dg = (item.dg_num === undefined || item.dg_num === null) ? '' : String(item.dg_num);
        if (activeDg === '?') return dg === '';
        if (activeDg === '11+') return dg !== '' && parseInt(dg, 10) >= 11;
        return dg === activeDg;
      });
    }
  }

  if (q) {
    data = data.filter(item => {
      const title = (item.title || item.nombre || item.name || '').toLowerCase();
      return title.includes(q);
    });
  }

  renderCards(data);
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
    let sub = item.type || item.category || item.tipo || '';
    if (IS_ADND2E && currentTab === 'spells' && (item.clase || item.nivel !== undefined || item.escuela)) {
      const nivel = (item.nivel === undefined || item.nivel === null) ? '?' : item.nivel;
      sub = `${item.clase || '¿clase?'} · Nv. ${nivel}${item.escuela ? ' · ' + item.escuela : ''}`;
    } else if (IS_ADND2E && currentTab === 'monsters') {
      const dg = (item.dg_num === undefined || item.dg_num === null) ? (item.dg || '?') : item.dg_num;
      sub = `DG: ${dg}${item.tamaño ? ' · ' + item.tamaño : ''}`;
    }
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
