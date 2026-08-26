/**
 * Vista tablet "PNJs": ver el roster guardado y crear PNJs nuevos con el
 * mismo generador de PNJ Rápido que la pantalla de máster (mismos
 * endpoints, sin lógica de servidor propia). SYSTEM_ID viene inyectado
 * como literal desde la plantilla (patrón de las demás vistas de tablet).
 */

let pnjTabletUltimoResultado = null;

function pnjTabletCargarCategorias() {
  const select = document.getElementById('pnj-cat-select');
  fetch('/api/pnj-categorias?sistema=' + SYSTEM_ID)
    .then(r => r.json())
    .then(cats => {
      if (!cats.length) {
        select.innerHTML = '<option value="">Sin categorías creadas</option>';
        return;
      }
      select.innerHTML = cats.map(c => `<option value="${c.id}">${c.nombre}</option>`).join('');
    })
    .catch(err => console.error('Error cargando categorías:', err));
}

function pnjTabletCargarRasgos() {
  const cont = document.getElementById('pnj-rasgos');
  fetch('/api/pnj-categorias/rasgos')
    .then(r => r.json())
    .then(rasgos => {
      cont.innerHTML = rasgos.map(r => `<label><input type="checkbox" value="${r.id}"> ${r.label}</label>`).join('');
    })
    .catch(err => console.error('Error cargando rasgos:', err));
}

function pnjTabletRasgosSeleccionados() {
  return Array.from(document.querySelectorAll('#pnj-rasgos input:checked')).map(cb => cb.value);
}

function pnjTabletCargarModelosIa() {
  const select = document.getElementById('pnj-modelo-ia');
  fetch('/api/assistant/models')
    .then(r => r.json())
    .then(data => {
      select.innerHTML = '';
      (data.ollama || []).forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id; opt.textContent = m.label;
        select.appendChild(opt);
      });
      (data.claude || []).forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.label + (data.has_claude_key ? '' : ' 🔑');
        select.appendChild(opt);
      });
    })
    .catch(err => console.error('Error cargando modelos de IA:', err));
}

function pnjTabletGenerar() {
  const select = document.getElementById('pnj-cat-select');
  const azar = document.getElementById('pnj-cat-azar').checked;
  const dg = parseInt(document.getElementById('pnj-dg').value, 10) || 1;
  const genero = document.getElementById('pnj-genero').value;
  const resultado = document.getElementById('pnj-result');

  const body = { dg, genero, sistema: SYSTEM_ID };
  if (!azar && select.value) body.categoria_id = parseInt(select.value, 10);

  fetch('/api/pnj-categorias/generar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { resultado.innerHTML = `<p>${data.error}</p>`; return; }
      pnjTabletUltimoResultado = data;
      pnjTabletUltimoResultado.rasgos = [];
      pnjTabletUltimoResultado.descripcion = '';
      document.getElementById('pnj-descripcion-result').innerHTML = '';
      pnjTabletPintarResultado(data);
    })
    .catch(err => console.error('Error generando PNJ:', err));
}

function pnjTabletPintarResultado(data) {
  const resultado = document.getElementById('pnj-result');
  const statsHtml = Object.entries(data.stats || {})
    .map(([k, v]) => `<span class="pnj-stat"><b>${k.toUpperCase()}</b> ${v}</span>`).join('');
  const equipoHtml = (data.equipo || []).length
    ? `<div>${data.equipo.map(e => `<span class="chip">${e}</span>`).join('')}</div>`
    : '';
  resultado.innerHTML = `
    <div><strong>${data.nombre}</strong> — ${data.categoria} — ${data.dg} DG</div>
    <div>${statsHtml}</div>
    ${equipoHtml}
    <button class="add-confirm-btn pnj-add-btn" style="margin-top:6px;" onclick="pnjTabletAnadirAIniciativa()">⚔️ Añadir a Iniciativa</button>
  `;
}

/**
 * Añade el último PNJ generado al tracker de iniciativa (tipo "monster").
 * Pide los puntos de golpe con un prompt, ya que el generador no los
 * calcula (solo las 6 características).
 * @returns {void}
 */
function pnjTabletAnadirAIniciativa() {
  if (!pnjTabletUltimoResultado) { alert('Genera un PNJ primero.'); return; }
  pnjTabletPedirHpYAnadir(pnjTabletUltimoResultado.nombre, pnjTabletUltimoResultado.dg);
}

function pnjTabletPedirHpYAnadir(nombre, dg) {
  const sugerido = Math.max(1, dg) * 4;
  const hp = prompt(`Puntos de golpe para "${nombre}" (sugerido ${sugerido}, según sus DG):`, sugerido);
  if (hp === null) return;
  const hpNum = parseInt(hp, 10) || 0;
  fetch('/api/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: nombre, hp: hpNum, max_hp: hpNum, type: 'monster' }),
  })
    .then(r => r.json())
    .then(data => { if (!data.success) alert('No se pudo añadir a iniciativa.'); })
    .catch(err => console.error('Error añadiendo a iniciativa:', err));
}

function pnjTabletGenerarDescripcion() {
  if (!pnjTabletUltimoResultado) { alert('Genera un PNJ primero.'); return; }
  const usarIa = document.getElementById('pnj-usar-ia').checked;
  const modelo = document.getElementById('pnj-modelo-ia').value;
  const rasgos = pnjTabletRasgosSeleccionados();
  const resultado = document.getElementById('pnj-descripcion-result');
  resultado.innerHTML = '<p>Generando...</p>';

  fetch('/api/pnj-categorias/descripcion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre: pnjTabletUltimoResultado.nombre,
      categoria: pnjTabletUltimoResultado.categoria,
      dg: pnjTabletUltimoResultado.dg,
      genero: pnjTabletUltimoResultado.genero,
      rasgos, usar_ia: usarIa, model: modelo, sistema: SYSTEM_ID,
    }),
  })
    .then(r => r.json())
    .then(data => {
      pnjTabletUltimoResultado.rasgos = rasgos;
      pnjTabletUltimoResultado.descripcion = data.descripcion || '';
      const aviso = data.fuente === 'plantilla_fallback'
        ? '<p>⚠️ IA no disponible — se usó una descripción de plantilla.</p>' : '';
      resultado.innerHTML = `<p>${data.descripcion || ''}</p>${aviso}`;
    })
    .catch(err => console.error('Error generando descripción:', err));
}

function pnjTabletGuardar() {
  if (!pnjTabletUltimoResultado) { alert('Genera un PNJ primero.'); return; }
  const notasInput = document.getElementById('pnj-notas');
  fetch('/api/pnj-roster', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre: pnjTabletUltimoResultado.nombre,
      categoria: pnjTabletUltimoResultado.categoria,
      dg: pnjTabletUltimoResultado.dg,
      genero: pnjTabletUltimoResultado.genero,
      stats: pnjTabletUltimoResultado.stats,
      equipo: pnjTabletUltimoResultado.equipo,
      rasgos: pnjTabletUltimoResultado.rasgos || [],
      descripcion: pnjTabletUltimoResultado.descripcion || '',
      notas: notasInput.value.trim(),
      sistema: SYSTEM_ID,
    }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      notasInput.value = '';
      pnjTabletCargarRoster();
    })
    .catch(err => console.error('Error guardando en el roster:', err));
}

function pnjTabletCargarRoster() {
  const list = document.getElementById('pnj-roster-list');
  fetch('/api/pnj-roster?sistema=' + SYSTEM_ID)
    .then(r => r.json())
    .then(entradas => {
      if (!entradas.length) {
        list.innerHTML = '<div class="empty-state">Sin PNJs guardados todavía.</div>';
        return;
      }
      list.innerHTML = entradas.map(e => `
        <div class="rules-card" onclick="pnjTabletAbrirModal(${e.id})">
          <strong class="card-title">${e.nombre}</strong>
          <span class="card-sub">${e.categoria} — ${e.dg} DG</span>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error cargando el roster:', err));
}

function pnjTabletAbrirModal(entryId) {
  const modal = document.getElementById('pnj-modal');
  const body = document.getElementById('pnj-modal-body');
  body.innerHTML = '<div class="loading-state">Cargando...</div>';
  modal.classList.remove('hidden');

  fetch(`/api/pnj-roster/${entryId}`)
    .then(r => r.json())
    .then(e => {
      const statsHtml = Object.entries(e.stats || {})
        .map(([k, v]) => `<span class="pnj-stat"><b>${k.toUpperCase()}</b> ${v}</span>`).join('');
      const equipoHtml = (e.equipo || []).length
        ? `<p>${e.equipo.map(x => `<span class="chip">${x}</span>`).join('')}</p>` : '';
      body.innerHTML = `
        <h2>${e.nombre}</h2>
        <p class="card-sub">${e.categoria} — ${e.dg} DG — ${e.genero}</p>
        <p>${statsHtml}</p>
        ${equipoHtml}
        ${e.descripcion ? `<p>${e.descripcion}</p>` : ''}
        ${e.notas ? `<p><em>${e.notas}</em></p>` : ''}
        <button class="add-confirm-btn" onclick="pnjTabletPedirHpYAnadir('${e.nombre.replace(/'/g, "\\'")}', ${e.dg})">⚔️ Añadir a Iniciativa</button>
        <button class="add-confirm-btn" onclick="pnjTabletBorrar(${e.id})">🗑️ Eliminar del roster</button>
      `;
    })
    .catch(err => console.error('Error cargando detalle del PNJ:', err));
}

function pnjTabletBorrar(entryId) {
  if (!confirm('¿Eliminar este PNJ del roster?')) return;
  fetch(`/api/pnj-roster/${entryId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      pnjTabletCerrarModal();
      pnjTabletCargarRoster();
    })
    .catch(err => console.error('Error borrando PNJ:', err));
}

function pnjTabletCerrarModal() {
  document.getElementById('pnj-modal').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
  pnjTabletCargarCategorias();
  pnjTabletCargarRasgos();
  pnjTabletCargarModelosIa();
  pnjTabletCargarRoster();
});
