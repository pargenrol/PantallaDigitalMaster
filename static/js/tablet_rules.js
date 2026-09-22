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
    <div class="rules-card" onclick="openDetail('${esc(ctype)}', '${esc(slug)}', '${esc(title)}')">
      <strong class="card-title">${esc(title)}</strong>
      ${sub ? `<span class="card-sub">${esc(sub)}</span>` : ''}
    </div>`;
  }).join('');
}

// ── Detail modal ──────────────────────────────────────────

// Guarda lo que hay abierto actualmente en el modal, para poder fijarlo
// como panel flotante sin tener que volver a pedirlo al servidor.
let currentDetail = null;

async function openDetail(ctype, slug, titulo) {
  const modal = document.getElementById('rt-modal');
  const body  = document.getElementById('rt-modal-body');
  body.innerHTML = '<div class="loading-state">Cargando...</div>';
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  document.body.classList.add('rt-modal-open');
  currentDetail = null;

  try {
    const res = await fetch(`/content/${ctype}/${slug}`);
    if (!res.ok) throw new Error('not found');
    const html = await res.text();
    body.innerHTML = html;
    currentDetail = { ctype, slug, titulo: titulo || slug, html };
  } catch {
    body.innerHTML = '<div class="error-state">No se pudo cargar el contenido.</div>';
  }
}

function closeModal() {
  document.getElementById('rt-modal').classList.add('hidden');
  document.body.style.overflow = '';
  document.body.classList.remove('rt-modal-open');
}

// Close on Escape
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── Paneles fijados: varias reglas/tablas a la vez, flotantes y
// redimensionables (mismo patrón que en /master). ─────────────────────────

/** Fija el contenido actualmente abierto en el modal como panel flotante,
 * cerrando el modal — así se pueden tener varias tablas a la vez en pantalla
 * en vez de un solo modal que sustituye al anterior. */
function pinCurrentDetail() {
  if (!currentDetail) return;
  crearPanelFijado({ tipo: currentDetail.ctype, slug: currentDetail.slug, titulo: currentDetail.titulo, html: currentDetail.html });
  closeModal();
}

let panelSeq = 0;

/** Crea un panel flotante y arrastrable con el contenido dado, y lo añade
 * a #pinnedPanelsHost. Guarda tipo/slug/título en el propio elemento para
 * poder guardarlos luego en una "programación de pantalla" (mismo patrón
 * que en /master). Si no se da x/y, se coloca en cascada. */
function crearPanelFijado(opts) {
  const { tipo, slug, titulo, html, x, y } = opts;
  const host = document.getElementById('pinnedPanelsHost');
  const panel = document.createElement('div');
  panel.className = 'pinned-panel';
  panel.dataset.tipo = tipo || '';
  panel.dataset.slug = slug || '';
  panel.dataset.titulo = titulo || '';
  panelSeq += 1;
  if (x !== undefined && y !== undefined) {
    panel.style.left = x + 'px';
    panel.style.top = y + 'px';
  } else {
    const offset = (panelSeq % 6) * 24;
    panel.style.right = (16 + offset) + 'px';
    panel.style.bottom = (16 + offset) + 'px';
  }
  panel.innerHTML = `
    <div class="pinned-panel__header">
      <span class="pinned-panel__titulo">${esc(titulo)}</span>
      <button type="button" class="pinned-panel__cerrar" title="Quitar este panel">✕</button>
    </div>
    <div class="pinned-panel__body markdown-body">${html}</div>
  `;
  panel.querySelector('.pinned-panel__cerrar').addEventListener('click', () => panel.remove());
  host.appendChild(panel);
  return panel;
}

// ── Programaciones de pantalla guardadas (cargar/guardar la disposición
// de paneles fijados) — mismo patrón/API que /master. ──────────────────────

function pantallaConfigCargarSelect() {
  const select = document.getElementById('pantallaConfigSelect');
  if (!select) return;
  fetch('/api/screen-configs?sistema=' + encodeURIComponent(SYSTEM_ID))
    .then(r => r.json())
    .then(configs => {
      select.innerHTML = '<option value="">— Pantallas —</option>' +
        configs.map(c => `<option value="${c.id}">${esc(c.nombre)}</option>`).join('');
    })
    .catch(() => {});
}
document.addEventListener('DOMContentLoaded', pantallaConfigCargarSelect);

/** Guarda los paneles fijados ahora mismo (tipo/slug/posición) con un nombre elegido por el usuario. */
function guardarPantallaConfig() {
  const paneles = [...document.querySelectorAll('.pinned-panel')].map(p => ({
    tipo: p.dataset.tipo, slug: p.dataset.slug || null, titulo: p.dataset.titulo,
    x: parseInt(p.style.left, 10) || 0, y: parseInt(p.style.top, 10) || 0,
  }));
  if (!paneles.length) { alert('No hay ningún panel fijado ahora mismo para guardar.'); return; }
  const nombre = prompt('Nombre para esta programación de pantalla:');
  if (!nombre || !nombre.trim()) return;
  fetch('/api/screen-configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sistema: SYSTEM_ID, nombre: nombre.trim(), paneles }),
  })
    .then(r => r.json())
    .then(() => pantallaConfigCargarSelect())
    .catch(err => console.error('Error guardando programación de pantalla:', err));
}
window.guardarPantallaConfig = guardarPantallaConfig;

/** Carga la programación de pantalla elegida en el <select>, recreando cada panel en su posición guardada. */
function cargarPantallaConfig() {
  const select = document.getElementById('pantallaConfigSelect');
  const configId = select && select.value;
  if (!configId) return;
  fetch('/api/screen-configs?sistema=' + encodeURIComponent(SYSTEM_ID))
    .then(r => r.json())
    .then(configs => {
      const config = configs.find(c => String(c.id) === String(configId));
      if (!config) return;
      document.querySelectorAll('.pinned-panel').forEach(p => p.remove());
      config.paneles.forEach(p => {
        fetch(`/content/${p.tipo}/${p.slug}`)
          .then(r => r.text())
          .then(html => crearPanelFijado({ tipo: p.tipo, slug: p.slug, titulo: p.titulo, html, x: p.x, y: p.y }))
          .catch(() => {});
      });
    })
    .catch(err => console.error('Error cargando programación de pantalla:', err));
}
window.cargarPantallaConfig = cargarPantallaConfig;

// Arrastre libre de paneles fijados, por su cabecera.
let dragInfo = null;

function iniciarArrastre(clientX, clientY, target) {
  if (target.closest('button, input, textarea, select, a, label')) return null;
  const header = target.closest('.pinned-panel__header');
  if (!header) return null;
  const panel = header.closest('.pinned-panel');
  const rect = panel.getBoundingClientRect();
  panel.style.right = '';
  panel.style.bottom = '';
  panel.style.left = rect.left + 'px';
  panel.style.top = rect.top + 'px';
  return { el: panel, offsetX: clientX - rect.left, offsetY: clientY - rect.top };
}

function moverArrastre(clientX, clientY) {
  if (!dragInfo) return;
  const { el, offsetX, offsetY } = dragInfo;
  el.style.left = Math.max(0, clientX - offsetX) + 'px';
  el.style.top = Math.max(0, clientY - offsetY) + 'px';
}

document.addEventListener('mousedown', (e) => {
  const info = iniciarArrastre(e.clientX, e.clientY, e.target);
  if (info) { dragInfo = info; e.preventDefault(); }
});
document.addEventListener('mousemove', (e) => moverArrastre(e.clientX, e.clientY));
document.addEventListener('mouseup', () => { dragInfo = null; });

document.addEventListener('touchstart', (e) => {
  const t = e.touches[0];
  const info = iniciarArrastre(t.clientX, t.clientY, e.target);
  if (info) dragInfo = info;
}, { passive: true });
document.addEventListener('touchmove', (e) => {
  if (!dragInfo) return;
  const t = e.touches[0];
  moverArrastre(t.clientX, t.clientY);
}, { passive: true });
document.addEventListener('touchend', () => { dragInfo = null; });

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
