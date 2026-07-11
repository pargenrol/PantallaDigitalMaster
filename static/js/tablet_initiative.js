/* ============================================================
   tablet_initiative.js — Tracker de combate para tablet
   Polling liviano cada 1.5s. Actualiza solo si cambió el estado.
   ============================================================ */

'use strict';

let lastUpdated   = null;
let characters    = [];
let currentTurn   = 0;
let roundNumber   = 1;

// ── Polling ───────────────────────────────────────────────

async function poll() {
  try {
    const res = await fetch('/api/game/poll', { cache: 'no-store' });
    if (!res.ok) { setPollStatus(false); return; }
    const data = await res.json();
    setPollStatus(true);

    if (data.last_updated !== lastUpdated || data.character_count !== characters.length) {
      lastUpdated = data.last_updated;
      await fetchAndRender();
    }
  } catch {
    setPollStatus(false);
  }
}

async function fetchAndRender() {
  try {
    const res = await fetch('/api/characters', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();

    characters  = data.characters  || [];
    currentTurn = data.current_turn ?? 0;
    roundNumber = data.round_number ?? 1;

    document.getElementById('round-number').textContent = roundNumber;
    renderList();
  } catch { /* silent */ }
}

function setPollStatus(ok) {
  const dot = document.getElementById('poll-dot');
  if (!dot) return;
  dot.classList.toggle('ok',  ok);
  dot.classList.toggle('err', !ok);
}

// ── Render ────────────────────────────────────────────────

function renderList() {
  const list = document.getElementById('char-list');
  if (!list) return;

  if (characters.length === 0) {
    list.innerHTML = '<div class="empty-state">Sin combatientes. Añade personajes para empezar.</div>';
    return;
  }

  list.innerHTML = characters.map(ch => charCard(ch)).join('');
}

function charCard(ch) {
  const pct = ch.max_hp > 0 ? Math.max(0, Math.min(100, (ch.hp / ch.max_hp) * 100)) : 0;
  const defeated = ch.hp <= 0;
  const active   = ch.isCurrent;

  const hpColor = pct > 50 ? 'hp-high' : pct > 25 ? 'hp-mid' : 'hp-low';

  return `
  <div class="char-card ${active ? 'active-turn' : ''} ${defeated ? 'defeated' : ''}" data-id="${ch.id}">
    <div class="char-main-row">
      <div class="char-identity">
        ${active ? '<span class="turn-arrow">▶</span>' : '<span class="turn-spacer"></span>'}
        <div class="char-names">
          <span class="char-name">${esc(ch.name)}</span>
          <span class="char-meta">${esc(CFG.iniLabel)}: ${ch.initiative} · ${esc(ch.type)}</span>
        </div>
      </div>
      <button class="delete-char-btn" onclick="deleteChar(${ch.id})" title="Eliminar">✕</button>
    </div>

    <div class="hp-row">
      <button class="hp-btn-big" onclick="changeHp(${ch.id}, -5)" title="-5">−5</button>
      <button class="hp-btn-big" onclick="changeHp(${ch.id}, -1)" title="-1">−</button>
      <div class="hp-block">
        <div class="hp-numbers">
          <span class="hp-cur">${ch.hp}</span>
          <span class="hp-slash">/</span>
          <span class="hp-max">${ch.max_hp}</span>
          <span class="hp-label-sm">${esc(CFG.hpLabel)}</span>
        </div>
        <div class="hp-bar-track">
          <div class="hp-bar-fill ${hpColor}" style="width:${pct}%"></div>
        </div>
      </div>
      <button class="hp-btn-big" onclick="changeHp(${ch.id}, 1)"  title="+1">+</button>
      <button class="hp-btn-big" onclick="changeHp(${ch.id}, 5)"  title="+5">+5</button>
    </div>

    ${CFG.hasStress ? stressRow(ch) : ''}
  </div>`;
}

function stressRow(ch) {
  return `
  <div class="stress-row">
    <span class="stress-label-sm">${esc(CFG.stressLabel)}</span>
    <button class="stress-btn" onclick="changeStress(${ch.id}, -1)">−</button>
    <span class="stress-val">${ch.stress}/${ch.max_stress}</span>
    <button class="stress-btn" onclick="changeStress(${ch.id}, 1)">+</button>
  </div>`;
}

// ── Actions ───────────────────────────────────────────────

async function changeHp(id, delta) {
  const ch = characters.find(c => c.id === id);
  if (!ch) return;
  const newHp = ch.hp + delta;

  // Optimistic update
  ch.hp = newHp;
  renderList();

  await fetch(`/api/characters/${id}/hp`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hp: newHp }),
  });
  lastUpdated = null;   // fuerza refresh en próximo poll
}

async function changeStress(id, delta) {
  const ch = characters.find(c => c.id === id);
  if (!ch) return;
  const newStress = Math.max(0, ch.stress + delta);

  ch.stress = newStress;
  renderList();

  await fetch(`/api/characters/${id}/stress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stress: newStress }),
  });
  lastUpdated = null;
}

async function nextTurn() {
  await fetch('/api/game/next-turn', { method: 'POST' });
  lastUpdated = null;
  await fetchAndRender();
}

async function prevTurn() {
  await fetch('/api/game/prev-turn', { method: 'POST' });
  lastUpdated = null;
  await fetchAndRender();
}

async function resetCombat() {
  if (!confirm('¿Resetear el combate? Se eliminarán todos los combatientes.')) return;
  await fetch('/api/game/reset', { method: 'POST' });
  lastUpdated = null;
  await fetchAndRender();
}

async function deleteChar(id) {
  await fetch(`/api/characters/${id}`, { method: 'DELETE' });
  lastUpdated = null;
  await fetchAndRender();
}

async function addCharacter() {
  const name = document.getElementById('add-name').value.trim();
  const ini  = parseInt(document.getElementById('add-ini').value)  || 0;
  const hp   = parseInt(document.getElementById('add-hp').value)   || 1;
  const type = document.getElementById('add-type').value;

  if (!name) {
    document.getElementById('add-name').focus();
    return;
  }

  await fetch('/api/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, initiative: ini, hp, max_hp: hp, type }),
  });

  // Clear form
  document.getElementById('add-name').value = '';
  document.getElementById('add-ini').value  = '';
  document.getElementById('add-hp').value   = '';
  document.getElementById('add-name').focus();

  lastUpdated = null;
  await fetchAndRender();
}

// Enter key on add form
document.addEventListener('DOMContentLoaded', () => {
  ['add-name', 'add-ini', 'add-hp'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') addCharacter(); });
  });
});

// ── Utils ─────────────────────────────────────────────────

function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Init ──────────────────────────────────────────────────

fetchAndRender();
setInterval(poll, 1500);
