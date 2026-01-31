// ========== VARIABLES GLOBALES ==========
let grimoireMonsters = [];
let grimoireSpells = [];
let grimoireRules = [];

let currentImage = null;
let currentVideo = null;
let currentYouTubeId = null;

// Variables Pizarra
let masterCanvas = null;
let currentTool = 'brush';
let isDrawingShape = false;
let shapeOrigX = 0;
let shapeOrigY = 0;
let activeShape = null;
let showGrid = true;
const gridSize = 50;

// Modal / contenido actual
let currentContentType = null;
let currentContentSlug = null;
let currentContentHtml = null;
let currentContentTitle = null;

// Audio
let masterAudioElement = null;

// ========== EXPORT (compat) ==========
window.addCharacter = addCharacter;
window.deleteCharacter = deleteCharacter;
window.updateHP = updateHP;
window.nextTurn = nextTurn;
window.prevTurn = prevTurn;
window.clearInitiative = clearInitiative;
window.showModal = showModal;
window.hideModal = hideModal;
window.showContentDetail = showContentDetail;
window.addMonsterToInitiative = addMonsterToInitiative;
window.filterContent = filterContent;
window.openTab = openTab;
window.showImage = showImage;
window.playVideo = playVideo;
window.stopVideo = stopVideo;
window.playYouTube = playYouTube;
window.toggleYoutubePlayback = toggleYoutubePlayback;
window.showInitiativeOnScreen = showInitiativeOnScreen;
window.projectCurrentCard = projectCurrentCard;
window.clearScreen = clearScreen;
window.blackoutScreen = blackoutScreen;
window.openFilePicker = openFilePicker;
window.initWhiteboard = initWhiteboard;
window.clearCanvas = clearCanvas;
window.projectWhiteboard = projectWhiteboard;
window.stopProjectingWhiteboard = stopProjectingWhiteboard;
window.setTool = setTool;
window.toggleWhiteboardFullscreen = toggleWhiteboardFullscreen;
window.playMasterAudio = playMasterAudio;
window.pauseMasterAudio = pauseMasterAudio;
window.stopMasterAudio = stopMasterAudio;
window.updateMasterVolume = updateMasterVolume;
window.openAudioPicker = openAudioPicker;
window.toggleCenterView = toggleCenterView;
window.loadLocalMarkdown = loadLocalMarkdown;
window.projectCustomMarkdown = projectCustomMarkdown;

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
  console.log("🎮 RPG Master Control iniciando...");

  loadGrimoireDataAndRender();
  loadGameState();

  setupEventListeners();

  if (typeof fabric !== 'undefined') initWhiteboard();

  initAudio();

  setInterval(loadGameState, 3000);
});

// ========== EVENT LISTENERS ==========
function setupEventListeners() {
  // 1) Acciones genéricas por data-action
  document.addEventListener('click', (e) => {
    const actionEl = e.target.closest('[data-action]');
    if (!actionEl) return;

    const action = actionEl.getAttribute('data-action');

    switch (action) {
      // Iniciativa
      case 'add-character': addCharacter(); break;
      case 'prev-turn': prevTurn(); break;
      case 'next-turn': nextTurn(); break;
      case 'show-initiative': showInitiativeOnScreen(); break;
      case 'reset-game': clearInitiative(); break;

      // Media
      case 'pick-image': openFilePicker('image'); break;
      case 'pick-video': openFilePicker('video'); break;
      case 'send-image': showImage(); break;
      case 'send-video': playVideo(); break;
      case 'send-youtube': playYouTube(); break;
      case 'toggle-youtube': toggleYoutubePlayback(); break;
      case 'clear-screen': clearScreen(); break;
      case 'blackout': blackoutScreen(); break;

      // Whiteboard
      case 'wb-clear': clearCanvas(); break;
      case 'wb-project': projectWhiteboard(); break;
      case 'wb-toggle-grid': toggleGrid(); break;
      case 'wb-fullscreen': toggleWhiteboardFullscreen(); break;

      // Markdown viewer
      case 'md-open':
        document.getElementById('mdFileInput')?.click();
        break;
      case 'md-project':
        projectCustomMarkdown();
        break;

      // Modal
      case 'modal-close': hideModal(); break;
      case 'modal-add-to-initiative': addMonsterToInitiative(); break;
      case 'modal-project-card': projectCurrentCard(); break;

      // Audio
      case 'audio-play': playMasterAudio(); break;
      case 'audio-pause': pauseMasterAudio(); break;
      case 'audio-stop': stopMasterAudio(); break;
      case 'audio-upload': openAudioPicker(); break;

      default:
        break;
    }
  });

  // 2) Tabs derecha (Grimorio/Conjuros/Reglas)
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => openTab(btn.dataset.tab, btn));
  });

  // 3) Tabs centro (Pizarra/Markdown)
  document.querySelectorAll('.center-tab-btn[data-center-tab]').forEach(btn => {
    btn.addEventListener('click', () => toggleCenterView(btn.dataset.centerTab));
  });

  // 4) Herramientas de pizarra
  document.querySelectorAll('.tool-btn[data-tool]').forEach(btn => {
    btn.addEventListener('click', () => setTool(btn.dataset.tool));
  });

  // 5) Filtros de grimorio
  document.querySelectorAll('input[data-filter]').forEach(inp => {
    inp.addEventListener('keyup', () => filterContent(inp.dataset.filter));
  });

  // 6) Click en tarjeta grimorio (delegación)
  document.addEventListener('click', (e) => {
    const card = e.target.closest('.tarjeta[data-ctype][data-slug]');
    if (!card) return;
    showContentDetail(card.dataset.ctype, card.dataset.slug);
  });

  // 7) Inputs especiales
  const ytInput = document.getElementById('youtubeUrl');
  if (ytInput) ytInput.addEventListener('input', updateYoutubePreview);

  const charNameInput = document.getElementById('charName');
  if (charNameInput) {
    charNameInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addCharacter();
      }
    });
  }

  // Markdown file input
  const mdFileInput = document.getElementById('mdFileInput');
  if (mdFileInput) {
    mdFileInput.addEventListener('change', () => loadLocalMarkdown(mdFileInput));
  }

  // Whiteboard brush settings
  document.getElementById('drawingColor')?.addEventListener('change', updateBrushProperties);
  document.getElementById('drawingLineWidth')?.addEventListener('change', updateBrushProperties);

  // Audio volume
  document.getElementById('masterVolume')?.addEventListener('input', (e) => updateMasterVolume(e.target.value));

  // Modal close click outside
  window.addEventListener('click', (event) => {
    const modal = document.getElementById('monsterModal');
    if (event.target === modal) hideModal();
  });

  // Delegación: HP y delete dentro de initiative list
  const list = document.getElementById('initiativeList');
  if (list) {
    list.addEventListener('click', (e) => {
      const del = e.target.closest('[data-del-id]');
      if (del) {
        const id = parseInt(del.dataset.delId, 10);
        if (!Number.isNaN(id)) deleteCharacter(id);
      }
    });

    list.addEventListener('change', (e) => {
      const hp = e.target.closest('[data-hp-id]');
      if (hp) {
        const id = parseInt(hp.dataset.hpId, 10);
        const val = parseInt(hp.value, 10);
        if (!Number.isNaN(id)) updateHP(id, Number.isNaN(val) ? 0 : val);
      }
    });
  }
}

// ========== TABS (GRIMORIO / CONJUROS / REGLAS) ==========
function openTab(tabId, btnEl) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

  const tab = document.getElementById(tabId);
  if (tab) tab.classList.add('active');
  if (btnEl) btnEl.classList.add('active');
}

// ========== TABS CENTRO ==========
function toggleCenterView(mode) {
  const wb = document.getElementById('whiteboard-wrapper');
  const md = document.getElementById('markdown-viewer-wrapper');
  const btns = document.querySelectorAll('.center-tab-btn');

  if (mode === 'whiteboard') {
    wb.classList.add('visible');
    md.classList.remove('visible');
    btns[0]?.classList.add('active');
    btns[1]?.classList.remove('active');
    if (masterCanvas) masterCanvas.calcOffset();
  } else {
    wb.classList.remove('visible');
    md.classList.add('visible');
    btns[0]?.classList.remove('active');
    btns[1]?.classList.add('active');
  }
}

// ========== GRIMORIO ==========
function loadGrimoireDataAndRender() {
  try {
    grimoireMonsters = JSON.parse(document.getElementById('grimorio-data').textContent);
    grimoireSpells = JSON.parse(document.getElementById('spells-data').textContent);
    grimoireRules = JSON.parse(document.getElementById('rules-data').textContent);
    console.log("📚 Datos del grimorio cargados:", grimoireMonsters.length, "monstruos");
  } catch (e) {
    console.error("Error cargando datos del grimorio:", e);
  }
}

// ========== FILTROS ==========
function filterContent(type) {
  let filterInput, listContainer;

  if (type === 'monster') {
    filterInput = document.getElementById('grimoireFilter');
    listContainer = document.getElementById('grimoireList');
  } else if (type === 'spell') {
    filterInput = document.getElementById('spellFilter');
    listContainer = document.getElementById('spellList');
  } else if (type === 'rule') {
    filterInput = document.getElementById('ruleFilter');
    listContainer = document.getElementById('ruleList');
  }

  if (!filterInput || !listContainer) return;

  const filter = filterInput.value.toLowerCase();
  const cards = listContainer.querySelectorAll('.tarjeta');

  cards.forEach(card => {
    const name = (card.getAttribute('data-nombre') || '').toLowerCase();
    card.style.display = name.includes(filter) ? 'block' : 'none';
  });
}

// ========== MODAL ==========
function showModal() {
  document.getElementById('monsterModal').style.display = 'block';
}

function hideModal() {
  document.getElementById('monsterModal').style.display = 'none';
}

// ========== CARGAR DETALLE DE CONTENIDO ==========
function showContentDetail(type, slug) {
  currentContentType = type;
  currentContentSlug = slug;

  fetch(`/content/${type}/${slug}`)
    .then(response => response.text())
    .then(html => {
      currentContentHtml = html;

      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = html;
      const h1 = tempDiv.querySelector('h1');
      currentContentTitle = h1 ? h1.textContent : slug;

      document.getElementById('monsterDetailContent').innerHTML = html;
      showModal();
    })
    .catch(error => console.error("Error cargando detalle:", error));
}

function addMonsterToInitiative() {
  if (!currentContentType || !currentContentSlug) return;

  const initiative = parseInt(document.getElementById('modalMonsterIni').value, 10) || 10;

  let itemData;
  if (currentContentType === 'monster') itemData = grimoireMonsters.find(m => m.slug === currentContentSlug);
  else if (currentContentType === 'spell') itemData = grimoireSpells.find(s => s.slug === currentContentSlug);
  else if (currentContentType === 'rule') itemData = grimoireRules.find(r => r.slug === currentContentSlug);

  if (!itemData) return;

  const name = itemData.nombre;

  fetch('/api/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      initiative,
      hp: itemData.hp || 10,
      max_hp: itemData.hp || 10,
      type: currentContentType === 'monster' ? 'monster' : currentContentType,
      slug: currentContentSlug
    })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        hideModal();
        updateStatus(`${name} añadido a la iniciativa`);
      }
    });
}

function projectCurrentCard() {
  if (!currentContentHtml) return;

  fetch('/api/screen/show-card', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: currentContentTitle || "Información",
      html: currentContentHtml
    })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Tarjeta proyectada");
    });
}

// ========== INICIATIVA ==========
function addCharacter() {
  const name = document.getElementById('charName').value.trim();
  const initiative = parseInt(document.getElementById('charInitiative').value, 10) || 0;
  const hp = parseInt(document.getElementById('charHP').value, 10) || 0;

  if (!name) return;

  fetch('/api/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, initiative, hp, max_hp: hp, type: 'player' })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        document.getElementById('charName').value = '';
        document.getElementById('charInitiative').value = '';
        document.getElementById('charHP').value = '';
        loadGameState();
        updateStatus(`${name} añadido`);
      }
    });
}

function deleteCharacter(id) {
  fetch(`/api/characters/${id}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        updateStatus("Personaje eliminado");
      }
    });
}

function updateHP(id, hp) {
  fetch(`/api/characters/${id}/hp`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hp })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) loadGameState();
    });
}

function nextTurn() {
  fetch('/api/game/next-turn', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        showInitiativeOnScreen();
      }
    });
}

function prevTurn() {
  fetch('/api/game/prev-turn', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        showInitiativeOnScreen();
      }
    });
}

function clearInitiative() {
  if (!confirm("¿Resetear iniciativa?")) return;

  fetch('/api/game/reset', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        clearScreen();
        updateStatus("Iniciativa reseteada");
      }
    });
}

// ========== CARGAR ESTADO ==========
function loadGameState() {
  fetch('/api/characters')
    .then(r => r.json())
    .then(data => {
      if (!data.success) return;

      renderInitiative(data.characters, data.current_turn, data.round_number);
      document.getElementById('roundNumber').textContent = data.round_number;

      const currentChar = data.characters.find(c => c.isCurrent);
      if (currentChar) {
        document.getElementById('currentTurnName').textContent = currentChar.name;
        updateActiveTurnDisplay(currentChar);
      } else {
        document.getElementById('currentTurnName').textContent = "N/A";
        document.getElementById('active-turn-container').style.display = 'none';
      }
    });
}

function renderInitiative(characters, currentTurn, roundNumber) {
  const list = document.getElementById('initiativeList');
  list.innerHTML = '';

  characters.forEach((char, index) => {
    const item = document.createElement('div');
    item.className = 'initiative-item';
    if (index === currentTurn) item.classList.add('active-turn');
    if ((char.hp ?? 0) <= 0) item.classList.add('defeated');

    item.innerHTML = `
      <div>
        <strong>${escapeHtml(char.name)}</strong> (${char.initiative})
        <div style="font-size:0.8em;color:#aaa">${escapeHtml(char.type || '')}</div>
      </div>
      <div style="display:flex;align-items:center;gap:5px">
        <input type="number" class="hp-input" value="${char.hp ?? 0}" data-hp-id="${char.id}">
        <button class="danger" data-del-id="${char.id}">×</button>
      </div>
    `;

    list.appendChild(item);
  });
}

// ========== RETRATO TURNO ACTUAL ==========
function updateActiveTurnDisplay(char) {
  const container = document.getElementById('active-turn-container');
  const img = document.getElementById('active-turn-img');
  const name = document.getElementById('active-turn-name');

  if (char.type === 'monster' && char.portrait_path) {
    container.style.display = 'block';
    img.src = char.portrait_path;
    name.textContent = char.name;
  } else {
    container.style.display = 'none';
  }
}

// ========== MEDIA ==========
function openFilePicker(type) {
  const input = document.createElement('input');
  input.type = 'file';
  if (type === 'image') input.accept = 'image/*';
  if (type === 'video') input.accept = 'video/*';
  if (type === 'audio') input.accept = '.mp3,.wav,.ogg';

  input.onchange = function (e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch(`/api/media/upload?type=${type}`, {
      method: 'POST',
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (!data.success) return;

        if (type === 'image') {
          currentImage = data.url;
          updateStatus("Imagen cargada");
        } else if (type === 'video') {
          currentVideo = data.url;
          updateStatus("Video cargado");
        } else {
          loadAudioList();
          updateStatus("Audio subido");
        }
      });
  };

  input.click();
}

function showImage() {
  if (!currentImage) return;

  fetch('/api/screen/show-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: currentImage })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Imagen enviada");
    });
}

function playVideo() {
  if (!currentVideo) return;

  fetch('/api/screen/show-video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: currentVideo })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Video enviado");
    });
}

function stopVideo() {
  currentVideo = null;
}

function extractYouTubeId(url) {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
}

function updateYoutubePreview() {
  const url = document.getElementById('youtubeUrl').value;
  currentYouTubeId = extractYouTubeId(url);
}

function playYouTube() {
  const url = document.getElementById('youtubeUrl').value;
  const videoId = extractYouTubeId(url);
  if (!videoId) return;

  currentYouTubeId = videoId;

  fetch('/api/screen/show-youtube', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("YouTube enviado");
    });
}

function toggleYoutubePlayback() {
  fetch('/api/screen/youtube-control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'toggle' })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("YouTube toggle");
    });
}

// ========== PANTALLA ==========
function showInitiativeOnScreen() {
  fetch('/api/screen/show-initiative', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Iniciativa en pantalla");
    });
}

function clearScreen() {
  fetch('/api/screen/clear', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Pantalla limpia");
    });
}

function blackoutScreen() {
  fetch('/api/screen/blackout', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Blackout");
    });
}

// ========== WHITEBOARD ==========
function initWhiteboard() {
  const canvasContainer = document.getElementById('canvasContainer');
  const canvas = document.getElementById('masterCanvas');

  canvas.width = canvasContainer.clientWidth;
  canvas.height = canvasContainer.clientHeight;

  masterCanvas = new fabric.Canvas('masterCanvas', {
    isDrawingMode: true,
    backgroundColor: 'white'
  });

  masterCanvas.freeDrawingBrush.width = parseInt(document.getElementById('drawingLineWidth').value, 10);
  masterCanvas.freeDrawingBrush.color = document.getElementById('drawingColor').value;

  loadWhiteboardState();

  masterCanvas.on('path:created', saveWhiteboardState);
  masterCanvas.on('object:modified', saveWhiteboardState);
  masterCanvas.on('object:added', function (e) {
    if (e.target && e.target.gridLine) return;
    if (!isDrawingShape) saveWhiteboardState();
  });

  setupShapeDrawing();
  drawGrid();

  window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
  if (!masterCanvas) return;
  const canvasContainer = document.getElementById('canvasContainer');
  masterCanvas.setWidth(canvasContainer.clientWidth);
  masterCanvas.setHeight(canvasContainer.clientHeight);
  masterCanvas.renderAll();
  drawGrid();
}

function updateBrushProperties() {
  if (!masterCanvas) return;
  const color = document.getElementById('drawingColor').value;
  const width = parseInt(document.getElementById('drawingLineWidth').value, 10);

  masterCanvas.freeDrawingBrush.color = currentTool === 'eraser' ? 'white' : color;
  masterCanvas.freeDrawingBrush.width = width;
}

function setTool(tool) {
  currentTool = tool;

  document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
  const id = 'tool' + tool.charAt(0).toUpperCase() + tool.slice(1);
  document.getElementById(id)?.classList.add('active');

  if (tool === 'brush' || tool === 'eraser') {
    masterCanvas.isDrawingMode = true;
    updateBrushProperties();
  } else {
    masterCanvas.isDrawingMode = false;
  }
}

function setupShapeDrawing() {
  masterCanvas.on('mouse:down', function (o) {
    if (currentTool === 'brush' || currentTool === 'eraser') return;

    isDrawingShape = true;
    const pointer = masterCanvas.getPointer(o.e);
    shapeOrigX = pointer.x;
    shapeOrigY = pointer.y;

    const color = document.getElementById('drawingColor').value;
    const width = parseInt(document.getElementById('drawingLineWidth').value, 10);

    if (currentTool === 'rect') {
      activeShape = new fabric.Rect({ left: shapeOrigX, top: shapeOrigY, width: 0, height: 0, fill: 'transparent', stroke: color, strokeWidth: width });
    } else if (currentTool === 'circle') {
      activeShape = new fabric.Circle({ left: shapeOrigX, top: shapeOrigY, radius: 1, fill: 'transparent', stroke: color, strokeWidth: width });
    } else if (currentTool === 'line') {
      activeShape = new fabric.Line([shapeOrigX, shapeOrigY, shapeOrigX, shapeOrigY], { stroke: color, strokeWidth: width });
    }

    if (activeShape) masterCanvas.add(activeShape);
  });

  masterCanvas.on('mouse:move', function (o) {
    if (!isDrawingShape || !activeShape) return;
    const pointer = masterCanvas.getPointer(o.e);

    if (currentTool === 'rect') {
      activeShape.set({
        width: Math.abs(shapeOrigX - pointer.x),
        height: Math.abs(shapeOrigY - pointer.y),
        left: Math.min(shapeOrigX, pointer.x),
        top: Math.min(shapeOrigY, pointer.y)
      });
    } else if (currentTool === 'circle') {
      const radius = Math.sqrt(Math.pow(shapeOrigX - pointer.x, 2) + Math.pow(shapeOrigY - pointer.y, 2)) / 2;
      activeShape.set({ radius });
    } else if (currentTool === 'line') {
      activeShape.set({ x2: pointer.x, y2: pointer.y });
    }

    masterCanvas.renderAll();
  });

  masterCanvas.on('mouse:up', function () {
    if (isDrawingShape) {
      isDrawingShape = false;
      if (activeShape) {
        activeShape.setCoords();
        saveWhiteboardState();
        activeShape = null;
      }
    }
  });
}

function drawGrid() {
  if (!masterCanvas) return;

  // Remove existing grid
  masterCanvas.getObjects().forEach(obj => {
    if (obj.gridLine) masterCanvas.remove(obj);
  });

  if (!showGrid) {
    masterCanvas.renderAll();
    return;
  }

  const width = masterCanvas.getWidth();
  const height = masterCanvas.getHeight();

  for (let i = 0; i < width; i += gridSize) {
    const line = new fabric.Line([i, 0, i, height], { stroke: '#ddd', selectable: false, evented: false, gridLine: true });
    masterCanvas.add(line);
    masterCanvas.sendToBack(line);
  }

  for (let i = 0; i < height; i += gridSize) {
    const line = new fabric.Line([0, i, width, i], { stroke: '#ddd', selectable: false, evented: false, gridLine: true });
    masterCanvas.add(line);
    masterCanvas.sendToBack(line);
  }

  masterCanvas.renderAll();
}

function toggleGrid() {
  showGrid = !showGrid;
  drawGrid();

  fetch('/api/screen/toggle-grid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ show: showGrid })
  }).catch(() => {});
}

function clearCanvas() {
  if (!confirm("¿Limpiar pizarra?")) return;
  masterCanvas.clear();
  masterCanvas.backgroundColor = 'white';
  drawGrid();
  saveWhiteboardState();
}

function saveWhiteboardState() {
  if (!masterCanvas) return;

  const objects = masterCanvas.getObjects().filter(obj => !obj.gridLine);
  const json = JSON.stringify({
    version: masterCanvas.version,
    objects,
    background: 'white'
  });

  fetch('/api/whiteboard/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state: json })
  }).catch(() => {});
}

function loadWhiteboardState() {
  fetch('/api/whiteboard/load')
    .then(r => r.json())
    .then(data => {
      if (data.state && masterCanvas) {
        masterCanvas.loadFromJSON(data.state, function () {
          drawGrid();
          masterCanvas.renderAll();
        });
      }
    })
    .catch(() => {});
}

function projectWhiteboard() {
  fetch('/api/screen/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'whiteboard' })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Pizarra proyectada");
    });
}

function stopProjectingWhiteboard() {
  // reservado
}

function toggleWhiteboardFullscreen() {
  const wrapper = document.getElementById('whiteboard-wrapper');
  wrapper.classList.toggle('wb-fullscreen');
  resizeCanvas();
}

// ========== AUDIO ==========
function initAudio() {
  masterAudioElement = document.getElementById('master-audio-element');
  loadAudioList();
}

function loadAudioList() {
  fetch('/api/audio/list')
    .then(r => r.json())
    .then(files => {
      const select = document.getElementById('audioList');
      select.innerHTML = '';

      if (!files || files.length === 0) {
        select.innerHTML = '<option value="">No hay audios</option>';
        return;
      }

      files.forEach(file => {
        const opt = document.createElement('option');
        opt.value = file;
        opt.textContent = file;
        select.appendChild(opt);
      });
    })
    .catch(err => console.error("Error cargando audios:", err));
}

function openAudioPicker() {
  openFilePicker('audio');
}

function playMasterAudio() {
  if (!masterAudioElement) return;

  const selected = document.getElementById('audioList').value;
  if (!selected) return;

  masterAudioElement.src = `/static/uploads/audio/${selected}`;
  masterAudioElement.volume = parseFloat(document.getElementById('masterVolume').value);
  masterAudioElement.play().catch(() => {});
}

function pauseMasterAudio() {
  if (masterAudioElement) masterAudioElement.pause();
}

function stopMasterAudio() {
  if (!masterAudioElement) return;
  masterAudioElement.pause();
  masterAudioElement.currentTime = 0;
}

function updateMasterVolume(value) {
  if (masterAudioElement) masterAudioElement.volume = parseFloat(value);
}

// ========== MARKDOWN VIEWER ==========
async function loadLocalMarkdown(input) {
  const file = input.files[0];
  if (!file) return;

  document.getElementById('mdFileName').textContent = file.name;

  const reader = new FileReader();
  reader.onload = async function (e) {
    const text = e.target.result;
    const result = await fetchData('/api/render-markdown-text', 'POST', { text });

    if (result && result.html) {
      document.getElementById('md-content-area').innerHTML = result.html;
    } else {
      document.getElementById('md-content-area').innerHTML = '<p style="color:red">Error al renderizar el archivo.</p>';
    }
  };
  reader.readAsText(file);
}

async function projectCustomMarkdown() {
  const contentDiv = document.getElementById('md-content-area');
  if (!contentDiv) return;

  const h1 = contentDiv.querySelector('h1');
  const title = h1 ? h1.textContent : (document.getElementById('mdFileName').textContent || "Documento");

  await fetchData('/api/screen/show-card', 'POST', { title, html: contentDiv.innerHTML });
  updateStatus('Documento proyectado');
}

// ========== UTILIDADES ==========
function updateStatus(message, isError = false) {
  document.getElementById('statusText').textContent = message;
  const indicator = document.querySelector('.status-indicator');
  if (indicator) indicator.style.background = isError ? 'red' : '#00bfa5';
}

async function fetchData(url, method = 'GET', data = null) {
  const options = { method };
  if (data) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
  const response = await fetch(url, options);
  return await response.json();
}

function escapeHtml(str) {
  return String(str ?? '')
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}