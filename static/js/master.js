/**
 * Master Screen Controller (DM Control Center)
 * -------------------------------------------
 * This script powers the "DM / Master" control panel:
 * - Loads grimoire data (monsters, spells, rules) embedded in the DOM.
 * - Manages initiative order (CRUD characters, next/prev turn, reset).
 * - Projects content to the Player Screen via backend "screen commands".
 * - Handles media uploads (image/video/audio) and projection (image/video/YouTube).
 * - Provides a Fabric.js whiteboard with drawing tools, shape tools, and grid overlay.
 * - Offers a Markdown viewer that can render local .md files via backend and project as an info card.
 *
 * External dependencies:
 * - fabric.js (global `fabric`) for whiteboard drawing.
 *
 * Key backend endpoints (expected):
 * - Initiative:
 *   - GET  /api/characters
 *   - POST /api/characters
 *   - DELETE /api/characters/:id
 *   - PUT /api/characters/:id/hp
 *   - POST /api/game/next-turn
 *   - POST /api/game/prev-turn
 *   - POST /api/game/reset
 * - Screen projection:
 *   - POST /api/screen/show-initiative
 *   - POST /api/screen/show-image
 *   - POST /api/screen/show-video
 *   - POST /api/screen/show-youtube
 *   - POST /api/screen/youtube-control
 *   - POST /api/screen/show-card
 *   - POST /api/screen/clear
 *   - POST /api/screen/blackout
 *   - POST /api/screen/command             (used to project whiteboard)
 *   - POST /api/screen/toggle-grid         (optional sync of grid preference)
 * - Whiteboard persistence:
 *   - POST /api/whiteboard/save
 *   - GET  /api/whiteboard/load
 * - Media upload:
 *   - POST /api/media/upload?type=image|video|audio
 * - Audio list:
 *   - GET  /api/audio/list
 * - Markdown rendering:
 *   - POST /api/render-markdown-text
 * - Content detail:
 *   - GET  /content/:type/:slug            (HTML fragment page)
 */

// ========== GLOBAL VARIABLES ==========

/**
 * Grimoire dataset: monsters.
 * Populated by parsing JSON from #grimorio-data.
 * @type {Array<GrimoireMonster>}
 */
let grimoireMonsters = [];

/**
 * Grimoire dataset: spells.
 * Populated by parsing JSON from #spells-data.
 * @type {Array<GrimoireSpell>}
 */
let grimoireSpells = [];

/**
 * Grimoire dataset: rules.
 * Populated by parsing JSON from #rules-data.
 * @type {Array<GrimoireRule>}
 */
let grimoireRules = [];

/**
 * Currently selected image URL (after upload).
 * Used by showImage() to project to the player screen.
 * @type {string|null}
 */
let currentImage = null;

/**
 * Currently selected video URL (after upload).
 * Used by playVideo() to project to the player screen.
 * @type {string|null}
 */
let currentVideo = null;

/**
 * Currently selected YouTube video ID.
 * Derived from the YouTube URL input.
 * Used by playYouTube() / toggleYoutubePlayback().
 * @type {string|null}
 */
let currentYouTubeId = null;

// ===== Whiteboard state =====

/**
 * Fabric.js canvas instance used for the master whiteboard.
 * @type {fabric.Canvas|null}
 */
let masterCanvas = null;

/**
 * Active drawing tool in the whiteboard.
 * Supported values in this script: 'brush' | 'eraser' | 'rect' | 'circle' | 'line'
 * @type {string}
 */
let currentTool = 'brush';

/**
 * Whether the user is currently drawing a shape (rect/circle/line).
 * @type {boolean}
 */
let isDrawingShape = false;

/**
 * Shape drawing start X coordinate in canvas space.
 * @type {number}
 */
let shapeOrigX = 0;

/**
 * Shape drawing start Y coordinate in canvas space.
 * @type {number}
 */
let shapeOrigY = 0;

/**
 * The currently drawn shape object while dragging.
 * @type {fabric.Object|null}
 */
let activeShape = null;

/**
 * Whether the grid overlay is enabled on the whiteboard.
 * @type {boolean}
 */
let showGrid = true;

/**
 * Grid cell size in pixels.
 * @type {number}
 */
const gridSize = 50;

// ===== Modal / current detail =====

/**
 * Type of the currently opened detail content in the modal.
 * Expected: 'monster' | 'spell' | 'rule' (based on data attributes).
 * @type {string|null}
 */
let currentContentType = null;

/**
 * Slug identifier of the currently opened detail content.
 * @type {string|null}
 */
let currentContentSlug = null;

/**
 * Raw HTML string of the currently loaded content detail (modal content).
 * @type {string|null}
 */
let currentContentHtml = null;

/**
 * Title extracted from the loaded HTML (usually first <h1>).
 * @type {string|null}
 */
let currentContentTitle = null;

// ===== Audio =====

/**
 * Master audio HTML element used to play ambient tracks locally in the DM UI.
 * @type {HTMLAudioElement|null}
 */
let masterAudioElement = null;

// ========== TYPE DEFINITIONS (JSDoc typedefs) ==========

/**
 * A generic grimoire entry base shape.
 * @typedef {Object} GrimoireBase
 * @property {string} slug - Unique identifier used in URLs and lookups.
 * @property {string} nombre - Display name (Spanish field name).
 * @property {number} [hp] - Optional hit points; used when adding to initiative (defaults to 10).
 */

/**
 * Monster entry stored in `grimoireMonsters`.
 * @typedef {GrimoireBase & {
 *   portrait_path?: string
 * }} GrimoireMonster
 */

/**
 * Spell entry stored in `grimoireSpells`.
 * @typedef {GrimoireBase} GrimoireSpell
 */

/**
 * Rule entry stored in `grimoireRules`.
 * @typedef {GrimoireBase} GrimoireRule
 */

/**
 * Character entity returned by /api/characters.
 * @typedef {Object} Character
 * @property {number} id
 * @property {string} name
 * @property {number} initiative
 * @property {number} [hp]
 * @property {number} [max_hp]
 * @property {string} [type] - e.g. 'player' | 'monster' | 'spell' | 'rule' etc.
 * @property {boolean} [isCurrent]
 * @property {string} [portrait_path]
 */

/**
 * Response shape for /api/characters.
 * @typedef {Object} CharactersResponse
 * @property {boolean} success
 * @property {Character[]} characters
 * @property {number} current_turn
 * @property {number} round_number
 */

// ========== EXPORT (compat) ==========
// Expose functions on window so inline HTML handlers (or other scripts) can call them.
// This is a compatibility pattern; prefer module exports in modern builds.

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

/**
 * Initializes the DM Control Center when the DOM is ready:
 * - Loads embedded grimoire datasets and renders lists (render is assumed by HTML templating).
 * - Loads game state (initiative, current turn, round).
 * - Sets up all DOM event listeners (delegation + inputs).
 * - Initializes Fabric.js whiteboard if Fabric is available.
 * - Initializes audio player and populates audio list.
 * - Polls game state every 3 seconds (UI refresh).
 *
 * @listens DOMContentLoaded
 * @returns {void}
 */
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

/**
 * Registers all UI event listeners.
 *
 * Patterns used:
 * 1) Global click delegation using [data-action] attributes.
 * 2) Tab buttons for right panel (grimoire/spells/rules).
 * 3) Center tabs (whiteboard/markdown viewer).
 * 4) Whiteboard tool buttons.
 * 5) Filter inputs for lists.
 * 6) Card click delegation (open modal detail).
 * 7) Special inputs (YouTube URL, add character on Enter, markdown file input).
 * 8) Whiteboard brush settings and audio volume.
 * 9) Modal close on outside click.
 * 10) Delegation inside initiative list for delete + HP updates.
 *
 * @returns {void}
 */
function setupEventListeners() {
  // 1) Generic actions via data-action
  document.addEventListener('click', (e) => {
    const actionEl = e.target.closest('[data-action]');
    if (!actionEl) return;

    const action = actionEl.getAttribute('data-action');

    switch (action) {
      // Initiative
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

  // 2) Right-side tabs (Grimoire/Spells/Rules)
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => openTab(btn.dataset.tab, btn));
  });

  // 3) Center tabs (Whiteboard/Markdown)
  document.querySelectorAll('.center-tab-btn[data-center-tab]').forEach(btn => {
    btn.addEventListener('click', () => toggleCenterView(btn.dataset.centerTab));
  });

  // 4) Whiteboard tools
  document.querySelectorAll('.tool-btn[data-tool]').forEach(btn => {
    btn.addEventListener('click', () => setTool(btn.dataset.tool));
  });

  // 5) Grimoire filters
  document.querySelectorAll('input[data-filter]').forEach(inp => {
    inp.addEventListener('keyup', () => filterContent(inp.dataset.filter));
  });

  // 6) Grimoire card click (delegation)
  document.addEventListener('click', (e) => {
    const card = e.target.closest('.tarjeta[data-ctype][data-slug]');
    if (!card) return;
    showContentDetail(card.dataset.ctype, card.dataset.slug);
  });

  // 7) Special inputs
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

  // Audio volume slider
  document.getElementById('masterVolume')?.addEventListener('input', (e) => updateMasterVolume(e.target.value));

  // Modal close when clicking outside the modal content
  window.addEventListener('click', (event) => {
    const modal = document.getElementById('monsterModal');
    if (event.target === modal) hideModal();
  });

  // Delegation: HP changes and delete button inside initiative list
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

// ========== TABS (GRIMOIRE / SPELLS / RULES) ==========

/**
 * Activates a right-panel tab and highlights its button.
 *
 * @param {string} tabId - DOM id of the tab content container.
 * @param {HTMLElement} [btnEl] - Button element that should be marked active.
 * @returns {void}
 */
function openTab(tabId, btnEl) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

  const tab = document.getElementById(tabId);
  if (tab) tab.classList.add('active');
  if (btnEl) btnEl.classList.add('active');
}

// ========== CENTER TABS (WHITEBOARD / MARKDOWN) ==========

/**
 * Toggles the center panel view between whiteboard and markdown viewer.
 *
 * When switching to whiteboard, it recalculates Fabric's offsets so drawing coordinates
 * match the visible canvas position.
 *
 * @param {'whiteboard'|'markdown'} mode - Target center view.
 * @returns {void}
 */
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

// ========== GRIMOIRE DATA LOADING ==========

/**
 * Loads grimoire datasets (monsters, spells, rules) from JSON embedded in the DOM.
 *
 * Expected DOM nodes:
 * - #grimorio-data contains JSON string for monsters.
 * - #spells-data contains JSON string for spells.
 * - #rules-data contains JSON string for rules.
 *
 * @returns {void}
 */
function loadGrimoireDataAndRender() {
  try {
    grimoireMonsters = JSON.parse(document.getElementById('grimorio-data').textContent);
    grimoireSpells = JSON.parse(document.getElementById('spells-data').textContent);
    grimoireRules = JSON.parse(document.getElementById('rules-data').textContent);
    console.log("📚 Grimoire data loaded:", grimoireMonsters.length, "monsters");
  } catch (e) {
    console.error("Error loading grimoire data:", e);
  }
}

// ========== FILTERS ==========

/**
 * Filters the visible cards in the selected list (monsters/spells/rules)
 * using the text value in the associated filter input.
 *
 * DOM assumptions:
 * - Cards have class `.tarjeta`
 * - Each card has `data-nombre` attribute used as searchable name
 *
 * @param {'monster'|'spell'|'rule'} type - Which list to filter.
 * @returns {void}
 */
function filterContent(type) {
  /** @type {HTMLInputElement|null|undefined} */
  let filterInput;
  /** @type {HTMLElement|null|undefined} */
  let listContainer;

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

/**
 * Shows the content modal.
 * @returns {void}
 */
function showModal() {
  document.getElementById('monsterModal').style.display = 'block';
}

/**
 * Hides the content modal.
 * @returns {void}
 */
function hideModal() {
  document.getElementById('monsterModal').style.display = 'none';
}

// ========== CONTENT DETAIL LOADING ==========

/**
 * Loads HTML detail for a grimoire entry (monster/spell/rule) and displays it in the modal.
 *
 * Endpoint contract:
 * GET /content/:type/:slug -> HTML string (fragment or page)
 *
 * It also extracts the first <h1> from the returned HTML to use as a title when projecting.
 *
 * @param {'monster'|'spell'|'rule'} type - Content type.
 * @param {string} slug - Content slug identifier.
 * @returns {void}
 */
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
    .catch(error => console.error("Error loading detail:", error));
}

/**
 * Adds the currently viewed modal content (monster/spell/rule) to initiative as a character entry.
 *
 * Data sources:
 * - Uses currentContentType/currentContentSlug to locate the item in grimoire arrays.
 * - Reads initiative value from #modalMonsterIni input (defaults to 10).
 *
 * Backend:
 * - POST /api/characters with JSON payload:
 *   { name, initiative, hp, max_hp, type, slug }
 *
 * @returns {void}
 */
function addMonsterToInitiative() {
  if (!currentContentType || !currentContentSlug) return;

  const initiative = parseInt(document.getElementById('modalMonsterIni').value, 10) || 10;

  /** @type {GrimoireBase|undefined} */
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
        updateStatus(`${name} added to initiative`);
      }
    });
}

/**
 * Projects the currently opened modal content as an "info card" on the player screen.
 *
 * Backend:
 * - POST /api/screen/show-card with JSON:
 *   { title, html }
 *
 * @returns {void}
 */
function projectCurrentCard() {
  if (!currentContentHtml) return;

  fetch('/api/screen/show-card', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: currentContentTitle || "Information",
      html: currentContentHtml
    })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Card projected");
    });
}

// ========== INITIATIVE MANAGEMENT ==========

/**
 * Creates a new initiative character from the UI inputs and persists it to the backend.
 *
 * Reads:
 * - #charName (string)
 * - #charInitiative (number)
 * - #charHP (number) -> also used as max_hp
 *
 * Backend:
 * - POST /api/characters with JSON: { name, initiative, hp, max_hp, type:'player' }
 *
 * @returns {void}
 */
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
        updateStatus(`${name} added`);
      }
    });
}

/**
 * Deletes a character from initiative by id.
 *
 * @param {number} id - Character ID.
 * @returns {void}
 */
function deleteCharacter(id) {
  fetch(`/api/characters/${id}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        updateStatus("Character deleted");
      }
    });
}

/**
 * Updates the HP of a character.
 *
 * Backend:
 * - PUT /api/characters/:id/hp with JSON { hp }
 *
 * @param {number} id - Character ID.
 * @param {number} hp - New HP value (integer).
 * @returns {void}
 */
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

/**
 * Advances the turn order to the next character.
 * Also projects the initiative view on the player screen.
 *
 * Backend:
 * - POST /api/game/next-turn
 *
 * @returns {void}
 */
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

/**
 * Moves turn order to the previous character.
 * Also projects the initiative view on the player screen.
 *
 * Backend:
 * - POST /api/game/prev-turn
 *
 * @returns {void}
 */
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

/**
 * Resets the entire initiative state (with a user confirmation).
 * Also clears the player screen after reset.
 *
 * Backend:
 * - POST /api/game/reset
 *
 * @returns {void}
 */
function clearInitiative() {
  if (!confirm("Reset initiative?")) return;

  fetch('/api/game/reset', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        loadGameState();
        clearScreen();
        updateStatus("Initiative reset");
      }
    });
}

// ========== GAME STATE LOADING & RENDERING ==========

/**
 * Loads the current game state from the backend and updates the UI:
 * - Initiative list
 * - Round number
 * - Current turn label
 * - Active monster portrait panel (if applicable)
 *
 * Backend:
 * - GET /api/characters -> CharactersResponse
 *
 * @returns {void}
 */
function loadGameState() {
  fetch('/api/characters')
    .then(r => r.json())
    .then(/** @param {CharactersResponse} data */ data => {
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

/**
 * Renders the initiative list UI.
 *
 * It marks:
 * - The active turn (index === currentTurn) with .active-turn
 * - Defeated characters (hp <= 0) with .defeated
 *
 * It also embeds:
 * - HP input with data-hp-id for delegation updates
 * - Delete button with data-del-id for delegation deletes
 *
 * @param {Character[]} characters - Initiative entries.
 * @param {number} currentTurn - Index of the current turn.
 * @param {number} roundNumber - Current round number (not used in this renderer, but available).
 * @returns {void}
 */
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

// ========== ACTIVE TURN PORTRAIT ==========

/**
 * Updates the "active turn" portrait panel for monsters.
 * This is a DM-side helper UI and does not project to the player screen.
 *
 * Rules:
 * - Only shows if char.type === 'monster' and char.portrait_path exists.
 *
 * @param {Character} char - The current character/turn.
 * @returns {void}
 */
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

// ========== MEDIA UPLOAD & PROJECTION ==========

/**
 * Opens a file picker and uploads the selected file to the backend.
 *
 * After successful upload:
 * - For images: sets `currentImage` to returned URL.
 * - For videos: sets `currentVideo` to returned URL.
 * - For audio: refreshes audio list.
 *
 * Backend:
 * - POST /api/media/upload?type=image|video|audio (multipart/form-data, key "file")
 * Response (expected):
 * - { success: boolean, url?: string }
 *
 * @param {'image'|'video'|'audio'} type - Media type to select and upload.
 * @returns {void}
 */
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
          updateStatus("Image uploaded");
        } else if (type === 'video') {
          currentVideo = data.url;
          updateStatus("Video uploaded");
        } else {
          loadAudioList();
          updateStatus("Audio uploaded");
        }
      });
  };

  input.click();
}

/**
 * Projects the currently selected image (`currentImage`) to the player screen.
 *
 * Backend:
 * - POST /api/screen/show-image with JSON { url }
 *
 * @returns {void}
 */
function showImage() {
  if (!currentImage) return;

  fetch('/api/screen/show-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: currentImage })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Image projected");
    });
}

/**
 * Projects the currently selected video (`currentVideo`) to the player screen.
 *
 * Backend:
 * - POST /api/screen/show-video with JSON { url }
 *
 * @returns {void}
 */
function playVideo() {
  if (!currentVideo) return;

  fetch('/api/screen/show-video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: currentVideo })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Video projected");
    });
}

/**
 * Clears the currently selected video reference on the master side.
 * Note: This does NOT send any command to the player screen.
 *
 * @returns {void}
 */
function stopVideo() {
  currentVideo = null;
}

/**
 * Extracts a YouTube video ID from common YouTube URL formats.
 *
 * Supported patterns include:
 * - youtu.be/<id>
 * - watch?v=<id>
 * - embed/<id>
 * - v/<id>
 *
 * @param {string} url - Full YouTube URL.
 * @returns {string|null} The extracted 11-character video ID, or null if not found.
 */
function extractYouTubeId(url) {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
}

/**
 * Updates `currentYouTubeId` whenever the YouTube URL input changes.
 * Reads value from #youtubeUrl.
 *
 * @returns {void}
 */
function updateYoutubePreview() {
  const url = document.getElementById('youtubeUrl').value;
  currentYouTubeId = extractYouTubeId(url);
}

/**
 * Projects a YouTube video to the player screen based on the URL in #youtubeUrl.
 *
 * Backend:
 * - POST /api/screen/show-youtube with JSON { video_id }
 *
 * @returns {void}
 */
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
      if (data.success) updateStatus("YouTube projected");
    });
}

/**
 * Sends a toggle playback command for YouTube to the player screen.
 * This assumes the player screen has an active YouTube player instance.
 *
 * Backend:
 * - POST /api/screen/youtube-control with JSON { action: 'toggle' }
 *
 * @returns {void}
 */
function toggleYoutubePlayback() {
  fetch('/api/screen/youtube-control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'toggle' })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("YouTube toggled");
    });
}

// ========== PLAYER SCREEN COMMANDS ==========

/**
 * Projects the initiative layer on the player screen.
 *
 * Backend:
 * - POST /api/screen/show-initiative
 *
 * @returns {void}
 */
function showInitiativeOnScreen() {
  fetch('/api/screen/show-initiative', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Initiative on screen");
    });
}

/**
 * Clears the player screen (hides all layers).
 *
 * Backend:
 * - POST /api/screen/clear
 *
 * @returns {void}
 */
function clearScreen() {
  fetch('/api/screen/clear', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Screen cleared");
    });
}

/**
 * Forces a blackout on the player screen.
 *
 * Backend:
 * - POST /api/screen/blackout
 *
 * @returns {void}
 */
function blackoutScreen() {
  fetch('/api/screen/blackout', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Blackout");
    });
}

// ========== WHITEBOARD (FABRIC.JS) ==========

/**
 * Initializes the Fabric.js whiteboard:
 * - Creates canvas sized to #canvasContainer
 * - Enables free drawing by default
 * - Configures brush width/color based on UI inputs
 * - Loads persisted board state from backend
 * - Registers autosave events (paths, modifications, additions)
 * - Enables shape tools via mouse handlers
 * - Draws (and optionally toggles) a grid overlay
 * - Re-sizes on window resize
 *
 * DOM requirements:
 * - #canvasContainer exists and has measurable size.
 * - <canvas id="masterCanvas"> exists.
 * - #drawingLineWidth and #drawingColor exist.
 *
 * @returns {void}
 */
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

  // Persist changes
  masterCanvas.on('path:created', saveWhiteboardState);
  masterCanvas.on('object:modified', saveWhiteboardState);
  masterCanvas.on('object:added', function (e) {
    if (e.target && e.target.gridLine) return; // do not persist grid primitives
    if (!isDrawingShape) saveWhiteboardState(); // avoid excessive saves while dragging shapes
  });

  setupShapeDrawing();
  drawGrid();

  window.addEventListener('resize', resizeCanvas);
}

/**
 * Resizes the Fabric canvas to match #canvasContainer and redraws the grid.
 *
 * @returns {void}
 */
function resizeCanvas() {
  if (!masterCanvas) return;
  const canvasContainer = document.getElementById('canvasContainer');
  masterCanvas.setWidth(canvasContainer.clientWidth);
  masterCanvas.setHeight(canvasContainer.clientHeight);
  masterCanvas.renderAll();
  drawGrid();
}

/**
 * Updates the free-drawing brush properties based on UI inputs and current tool.
 * - If tool is eraser, brush color is set to white (background color).
 * - Otherwise uses selected color.
 *
 * @returns {void}
 */
function updateBrushProperties() {
  if (!masterCanvas) return;
  const color = document.getElementById('drawingColor').value;
  const width = parseInt(document.getElementById('drawingLineWidth').value, 10);

  masterCanvas.freeDrawingBrush.color = currentTool === 'eraser' ? 'white' : color;
  masterCanvas.freeDrawingBrush.width = width;
}

/**
 * Sets the current whiteboard tool and updates UI button active state.
 *
 * Tools:
 * - 'brush'  : free drawing
 * - 'eraser' : free drawing with white stroke
 * - 'rect'   : rectangle shape drawing (mouse drag)
 * - 'circle' : circle shape drawing (mouse drag)
 * - 'line'   : line drawing (mouse drag)
 *
 * @param {'brush'|'eraser'|'rect'|'circle'|'line'} tool - Tool identifier.
 * @returns {void}
 */
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

/**
 * Installs Fabric mouse handlers to support drawing shapes (rect/circle/line).
 *
 * Workflow:
 * - mouse:down  -> create a new Fabric object with 0 size
 * - mouse:move  -> update size/endpoints based on cursor
 * - mouse:up    -> finalize object, save board state
 *
 * @returns {void}
 */
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
      activeShape = new fabric.Rect({
        left: shapeOrigX,
        top: shapeOrigY,
        width: 0,
        height: 0,
        fill: 'transparent',
        stroke: color,
        strokeWidth: width
      });
    } else if (currentTool === 'circle') {
      activeShape = new fabric.Circle({
        left: shapeOrigX,
        top: shapeOrigY,
        radius: 1,
        fill: 'transparent',
        stroke: color,
        strokeWidth: width
      });
    } else if (currentTool === 'line') {
      activeShape = new fabric.Line([shapeOrigX, shapeOrigY, shapeOrigX, shapeOrigY], {
        stroke: color,
        strokeWidth: width
      });
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
      // Uses distance formula; approximate radius based on cursor distance.
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

/**
 * Draws a grid overlay as non-interactive Fabric.Line objects.
 *
 * Implementation notes:
 * - Grid lines are tagged with `gridLine: true` so they can be removed and excluded from saves.
 * - Grid lines are sent to back to avoid blocking drawn content.
 *
 * @returns {void}
 */
function drawGrid() {
  if (!masterCanvas) return;

  // Remove existing grid lines
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
    const line = new fabric.Line([i, 0, i, height], {
      stroke: '#ddd',
      selectable: false,
      evented: false,
      gridLine: true
    });
    masterCanvas.add(line);
    masterCanvas.sendToBack(line);
  }

  for (let i = 0; i < height; i += gridSize) {
    const line = new fabric.Line([0, i, width, i], {
      stroke: '#ddd',
      selectable: false,
      evented: false,
      gridLine: true
    });
    masterCanvas.add(line);
    masterCanvas.sendToBack(line);
  }

  masterCanvas.renderAll();
}

/**
 * Toggles grid visibility and redraws.
 * Also notifies backend (optional) so the player screen can mirror the preference.
 *
 * Backend (best-effort):
 * - POST /api/screen/toggle-grid with JSON { show: boolean }
 *
 * @returns {void}
 */
function toggleGrid() {
  showGrid = !showGrid;
  drawGrid();

  fetch('/api/screen/toggle-grid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ show: showGrid })
  }).catch(() => {});
}

/**
 * Clears the whiteboard (with user confirmation), resets background, redraws grid,
 * and persists the empty state.
 *
 * @returns {void}
 */
function clearCanvas() {
  if (!confirm("Clear whiteboard?")) return;
  masterCanvas.clear();
  masterCanvas.backgroundColor = 'white';
  drawGrid();
  saveWhiteboardState();
}

/**
 * Saves the current whiteboard state to the backend.
 *
 * Important:
 * - Grid line objects are excluded from persistence (pure UI overlay).
 * - State is saved as a JSON string.
 *
 * Backend:
 * - POST /api/whiteboard/save with JSON { state: string }
 *
 * @returns {void}
 */
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

/**
 * Loads the whiteboard state from the backend and applies it to the Fabric canvas.
 *
 * Backend:
 * - GET /api/whiteboard/load -> { state: <fabric-json> }
 *
 * @returns {void}
 */
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

/**
 * Projects the whiteboard on the player screen by setting a screen command.
 *
 * Backend:
 * - POST /api/screen/command with JSON { type: 'whiteboard' }
 *
 * @returns {void}
 */
function projectWhiteboard() {
  fetch('/api/screen/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'whiteboard' })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Whiteboard projected");
    });
}

/**
 * Reserved for future use: stops projecting whiteboard.
 * Currently not implemented (no backend call).
 *
 * @returns {void}
 */
function stopProjectingWhiteboard() {
  // reserved
}

/**
 * Toggles fullscreen mode for the whiteboard wrapper and resizes the Fabric canvas accordingly.
 *
 * @returns {void}
 */
function toggleWhiteboardFullscreen() {
  const wrapper = document.getElementById('whiteboard-wrapper');
  wrapper.classList.toggle('wb-fullscreen');
  resizeCanvas();
}

// ========== AUDIO ==========

/**
 * Initializes the master audio player:
 * - Stores reference to the audio element.
 * - Loads the list of available audio tracks from the backend.
 *
 * DOM requirements:
 * - <audio id="master-audio-element">
 *
 * @returns {void}
 */
function initAudio() {
  masterAudioElement = document.getElementById('master-audio-element');
  loadAudioList();
}

/**
 * Loads the list of available audio files from the backend into a <select>.
 *
 * Backend:
 * - GET /api/audio/list -> string[] (filenames)
 *
 * DOM requirements:
 * - <select id="audioList">
 *
 * @returns {void}
 */
function loadAudioList() {
  fetch('/api/audio/list')
    .then(r => r.json())
    .then(files => {
      const select = document.getElementById('audioList');
      select.innerHTML = '';

      if (!files || files.length === 0) {
        select.innerHTML = '<option value="">No audio files</option>';
        return;
      }

      files.forEach(file => {
        const opt = document.createElement('option');
        opt.value = file;
        opt.textContent = file;
        select.appendChild(opt);
      });
    })
    .catch(err => console.error("Error loading audio list:", err));
}

/**
 * Opens the audio picker (reuses openFilePicker('audio')).
 *
 * @returns {void}
 */
function openAudioPicker() {
  openFilePicker('audio');
}

/**
 * Plays the selected audio file in the master UI (not projected to player screen).
 *
 * Reads:
 * - #audioList selected filename
 * - #masterVolume value (0..1)
 *
 * @returns {void}
 */
function playMasterAudio() {
  if (!masterAudioElement) return;

  const selected = document.getElementById('audioList').value;
  if (!selected) return;

  masterAudioElement.src = `/static/uploads/audio/${selected}`;
  masterAudioElement.volume = parseFloat(document.getElementById('masterVolume').value);
  masterAudioElement.play().catch(() => {});
}

/**
 * Pauses master audio playback.
 * @returns {void}
 */
function pauseMasterAudio() {
  if (masterAudioElement) masterAudioElement.pause();
}

/**
 * Stops master audio playback and resets time to 0.
 * @returns {void}
 */
function stopMasterAudio() {
  if (!masterAudioElement) return;
  masterAudioElement.pause();
  masterAudioElement.currentTime = 0;
}

/**
 * Updates the master audio volume.
 *
 * @param {number|string} value - Volume value (expected 0..1); coerced via parseFloat.
 * @returns {void}
 */
function updateMasterVolume(value) {
  if (masterAudioElement) masterAudioElement.volume = parseFloat(value);
}

// ========== MARKDOWN VIEWER ==========

/**
 * Loads a local Markdown file selected by the user, sends its text to the backend for rendering,
 * and injects the resulting HTML into the markdown viewer.
 *
 * Backend:
 * - POST /api/render-markdown-text with JSON { text }
 * Response:
 * - { html: string } (expected)
 *
 * DOM requirements:
 * - #mdFileName (file name label)
 * - #md-content-area (render target)
 *
 * @param {HTMLInputElement} input - <input type="file"> element with .files[0] available.
 * @returns {Promise<void>}
 */
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
      document.getElementById('md-content-area').innerHTML =
        '<p style="color:red">Error rendering the file.</p>';
    }
  };
  reader.readAsText(file);
}

/**
 * Projects the currently displayed Markdown HTML as an info card on the player screen.
 *
 * Title strategy:
 * - Uses first <h1> if present; otherwise uses #mdFileName or "Document".
 *
 * Backend:
 * - POST /api/screen/show-card with JSON { title, html }
 *
 * @returns {Promise<void>}
 */
async function projectCustomMarkdown() {
  const contentDiv = document.getElementById('md-content-area');
  if (!contentDiv) return;

  const h1 = contentDiv.querySelector('h1');
  const title = h1 ? h1.textContent : (document.getElementById('mdFileName').textContent || "Document");

  await fetchData('/api/screen/show-card', 'POST', { title, html: contentDiv.innerHTML });
  updateStatus('Document projected');
}

// ========== UTILITIES ==========

/**
 * Updates the status bar text and indicator color in the DM UI.
 *
 * DOM requirements:
 * - #statusText
 * - .status-indicator
 *
 * @param {string} message - Status message to display.
 * @param {boolean} [isError=false] - If true, indicator becomes red; otherwise teal.
 * @returns {void}
 */
function updateStatus(message, isError = false) {
  document.getElementById('statusText').textContent = message;
  const indicator = document.querySelector('.status-indicator');
  if (indicator) indicator.style.background = isError ? 'red' : '#00bfa5';
}

/**
 * Helper wrapper around fetch() that sends/receives JSON.
 *
 * - If `data` is provided, it sets Content-Type: application/json and JSON.stringifies it.
 * - Always returns response.json().
 *
 * @param {string} url - Request URL.
 * @param {string} [method='GET'] - HTTP method.
 * @param {Object|null} [data=null] - Request body object (JSON).
 * @returns {Promise<any>} Parsed JSON response.
 */
async function fetchData(url, method = 'GET', data = null) {
  /** @type {RequestInit} */
  const options = { method };
  if (data) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
  const response = await fetch(url, options);
  return await response.json();
}

/**
 * Escapes text for safe insertion into HTML.
 * Prevents HTML injection in text contexts.
 *
 * @param {unknown} str - Any value; coerced to string (null/undefined become '').
 * @returns {string} Escaped HTML string.
 */
function escapeHtml(str) {
  return String(str ?? '')
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
