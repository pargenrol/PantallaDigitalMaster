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

// ========== SYSTEM CONFIG ==========

/**
 * Active system configuration (loaded from #system-config JSON in the DOM).
 * @type {{ id: string, has_stress: boolean, initiative_label: string, hp_label: string, stress_label: string }}
 */
let systemConfig = { id: 'dnd5e', has_stress: false, initiative_label: 'Ini', hp_label: 'PV', stress_label: 'Estrés' };

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
window.updateStress = updateStress;
window.nextTurn = nextTurn;
window.prevTurn = prevTurn;
window.clearInitiative = clearInitiative;
window.showModal = showModal;
window.hideModal = hideModal;
window.showContentDetail = showContentDetail;
window.editContentInline = editContentInline;
window.cancelEditContent = cancelEditContent;
window.saveEditedContent = saveEditedContent;
window.deleteContentConfirm = deleteContentConfirm;
window.addMonsterToInitiative = addMonsterToInitiative;
window.filterContent = filterContent;
window.openTab = openTab;
window.showImage = showImage;
window.showWebpage = showWebpage;
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

  try {
    systemConfig = JSON.parse(document.getElementById('system-config').textContent);
  } catch (e) { /* use defaults */ }

  loadGrimoireDataAndRender();
  loadGameState();

  setupEventListeners();

  // initWhiteboard se llama desde master.html como script inline tras cargar fabric

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
      case 'send-webpage': showWebpage(); break;
      case 'pick-html': openFilePicker('html'); break;
      case 'clear-screen': clearScreen(); break;
      case 'blackout': blackoutScreen(); break;

      // Whiteboard
      case 'wb-clear':   clearCanvas(); break;
      case 'wb-project': projectWhiteboard(); break;
      case 'wb-fullscreen': toggleWhiteboardFullscreen(); break;
      case 'wb-undo': if (wbHIdx>0) { wbHIdx--; wbApplySnap(wbHistory[wbHIdx]); } break;
      case 'wb-redo': if (wbHIdx<wbHistory.length-1) { wbHIdx++; wbApplySnap(wbHistory[wbHIdx]); } break;

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
      case 'modal-portrait': openCropModal(); break;
      case 'modal-edit': editContentInline(); break;
      case 'modal-edit-cancel': cancelEditContent(); break;
      case 'modal-edit-save': saveEditedContent(); break;
      case 'modal-delete': deleteContentConfirm(); break;

      // Audio
      case 'audio-play': playMasterAudio(); break;
      case 'audio-pause': pauseMasterAudio(); break;
      case 'audio-stop': stopMasterAudio(); break;
      case 'audio-next': playNextTrack(); break;
      case 'audio-autoplay': toggleAutoplay(); break;
      case 'audio-loop': toggleLoop(); break;
      case 'audio-shuffle': toggleShuffle(); break;
      case 'audio-upload': openAudioPicker(); break;
      // Playlists
      case 'playlist-load': loadSelectedPlaylist(); break;
      case 'playlist-edit-mode': togglePlaylistEditMode(); break;
      case 'playlist-save': saveCurrentAsPlaylist(); break;
      case 'playlist-delete': deleteSelectedPlaylist(); break;

      default:
        break;
    }
  });

  // 2) Right-side tabs (Grimoire/Spells/Rules)
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      openTab(btn.dataset.tab, btn);
      if (btn.dataset.tab === 'tabEquipo') equipoCargarCatalogo();
    });
  });

  // 2b) Sub-pestañas "Jugadores" (PJs / PNJs)
  document.querySelectorAll('#playersSubtabRow [data-players-subtab]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#playersSubtabRow [data-players-subtab]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const sub = btn.dataset.playersSubtab;
      document.getElementById('playersSubtabPJs').style.display = sub === 'pjs' ? '' : 'none';
      document.getElementById('playersSubtabPNJs').style.display = sub === 'pnjs' ? '' : 'none';
      if (sub === 'pnjs') jugadoresPnjCargarRoster();
    });
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

      const stress = e.target.closest('[data-stress-id]');
      if (stress) {
        const id = parseInt(stress.dataset.stressId, 10);
        const val = parseInt(stress.value, 10);
        if (!Number.isNaN(id)) updateStress(id, Number.isNaN(val) ? 0 : val);
      }

      const ini = e.target.closest('[data-ini-id]');
      if (ini) {
        const id = parseInt(ini.dataset.iniId, 10);
        const val = parseInt(ini.value, 10);
        if (!Number.isNaN(id)) updateInitiative(id, Number.isNaN(val) ? 0 : val);
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

  const wp = document.getElementById('webpage-control-wrapper');

  if (mode === 'whiteboard') {
    wb.classList.add('visible');
    md.classList.remove('visible');
    if (wp) wp.classList.remove('visible');
    if (masterCanvas) { masterCanvas.calcOffset(); resizeCanvas(); }
  } else if (mode === 'markdown') {
    wb.classList.remove('visible');
    md.classList.add('visible');
    if (wp) wp.classList.remove('visible');
  } else if (mode === 'webpage') {
    wb.classList.remove('visible');
    md.classList.remove('visible');
    if (wp) wp.classList.add('visible');
  }

  btns.forEach(b => b.classList.remove('active'));
  const activeBtn = [...btns].find(b => b.dataset.centerTab === mode);
  if (activeBtn) activeBtn.classList.add('active');
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
// Filtros activos de clase/nivel para la pestaña de Conjuros (AD&D2e). '' = sin filtrar.
let activeSpellClase = '';
let activeSpellNivel = '';
let activeMonsterDg = '';
let activeRuleCategory = '';

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
    let visible = name.includes(filter) && cardMatchesCampaign(card);

    if (visible && type === 'spell') {
      if (activeSpellClase && card.getAttribute('data-clase') !== activeSpellClase) visible = false;
      if (activeSpellNivel) {
        const nivel = card.getAttribute('data-nivel') || '';
        if (activeSpellNivel === '?' ? nivel !== '' : nivel !== activeSpellNivel) visible = false;
      }
    }

    if (visible && type === 'rule' && activeRuleCategory) {
      if ((card.getAttribute('data-category') || '') !== activeRuleCategory) visible = false;
    }

    if (visible && type === 'monster' && activeMonsterDg) {
      const dgAttr = card.getAttribute('data-dg') || '';
      if (activeMonsterDg === '?') {
        if (dgAttr !== '') visible = false;
      } else if (activeMonsterDg === '11+') {
        if (dgAttr === '' || parseInt(dgAttr, 10) < 11) visible = false;
      } else {
        if (dgAttr !== activeMonsterDg) visible = false;
      }
    }

    card.style.display = visible ? 'block' : 'none';
  });
}

// Botones de filtro por clase/nivel de la pestaña Conjuros
document.querySelectorAll('#spellClaseRow [data-spell-clase]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeSpellClase = btn.dataset.spellClase;
    document.querySelectorAll('#spellClaseRow [data-spell-clase]').forEach(b => b.classList.toggle('active', b === btn));
    filterContent('spell');
  });
});
document.querySelectorAll('#spellNivelRow [data-spell-nivel]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeSpellNivel = btn.dataset.spellNivel;
    document.querySelectorAll('#spellNivelRow [data-spell-nivel]').forEach(b => b.classList.toggle('active', b === btn));
    filterContent('spell');
  });
});
// Botón de filtro por categoría de la pestaña Reglas
document.querySelectorAll('#ruleCategoryRow [data-rule-category]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeRuleCategory = btn.dataset.ruleCategory;
    document.querySelectorAll('#ruleCategoryRow [data-rule-category]').forEach(b => b.classList.toggle('active', b === btn));
    filterContent('rule');
  });
});
// Botón de filtro por Dados de Golpe de la pestaña Bestiario (AD&D2e)
document.querySelectorAll('#monsterDgRow [data-monster-dg]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeMonsterDg = btn.dataset.monsterDg;
    document.querySelectorAll('#monsterDgRow [data-monster-dg]').forEach(b => b.classList.toggle('active', b === btn));
    filterContent('monster');
  });
});

// ========== FILTRO DE CAMPAÑA ==========
// Se alimenta de la campaña "fijada" (📌) en la pestaña Campañas. Cuando hay
// una campaña de carpeta fijada, las tarjetas sin `data-campana` (contenido
// genérico) siguen visibles, y las que tienen `data-campana` solo se
// muestran si coincide con la campaña activa.

/** @type {string|null} */
window.activeCampaignName = window.activeCampaignName || null;

/**
 * Comprueba si una tarjeta debe verse con la campaña actualmente fijada.
 * @param {HTMLElement} card
 * @returns {boolean}
 */
function cardMatchesCampaign(card) {
  if (!window.activeCampaignName) return true;
  const camp = card.getAttribute('data-campana') || '';
  return !camp || camp === window.activeCampaignName;
}

/**
 * Reaplica el filtro de campaña a las listas de monstruos y jugadores.
 * Llamar cada vez que cambia la campaña fijada (pin/unpin).
 * @returns {void}
 */
function applyCampaignFilter() {
  filterContent('monster');
  document.querySelectorAll('#playersList .tarjeta').forEach(card => {
    card.style.display = cardMatchesCampaign(card) ? 'block' : 'none';
  });
}
window.applyCampaignFilter = applyCampaignFilter;

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

      // Si la ficha inyectada es el generador de PNJ Rápido, carga sus
      // categorías (select de PnjCategoria) y el panel de gestión (listado +
      // catálogo de equipo) tras insertar el HTML en el DOM.
      if (document.getElementById('pnjCategoriaSelect')) {
        pnjCargarCategorias();
        pnjCargarCategoriasListado();
        pnjCargarCatalogoEquipo({});
        pnjCargarRasgos();
        pnjCargarModelosIa();
        pnjCargarRoster();
      }

      // Si la ficha inyectada es "Clima", carga las entradas del primer
      // entorno del selector por defecto.
      if (document.getElementById('climaZonaSelect')) {
        climaCambiarZona();
      }
    })
    .catch(error => console.error("Error loading detail:", error));
}

// ========== GENERADORES EDITABLES (BD: GeneratorTable/GeneratorEntry) ==========

/**
 * Tira/elige al azar sobre las entradas en base de datos de un generador
 * (evita repetir entradas ya marcadas como usadas mientras queden libres).
 * Resalta la entrada elegida y marca su checkbox.
 * @param {string} slug - Slug del generador (coincide con el fichero .md de la regla).
 * @returns {void}
 */
function generatorDbRoll(slug) {
  fetch(`/api/generators/${slug}/roll`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    .then(r => r.json())
    .then(entry => {
      if (entry.error) { alert(entry.error); return; }
      const container = document.getElementById(`generator-entries-${slug}`);
      if (!container) return;
      container.querySelectorAll('.generator-entry.roll-highlight')
        .forEach(el => el.classList.remove('roll-highlight'));
      const row = container.querySelector(`.generator-entry[data-entry-id="${entry.id}"]`);
      if (row) {
        row.classList.add('roll-highlight', 'generator-entry--usado');
        row.querySelector('input[type="checkbox"]').checked = true;
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      const resultSpan = document.querySelector(`.content-detail--generator[data-generator-slug="${slug}"] .generator-roll__result`);
      if (resultSpan) resultSpan.textContent = entry.texto;
    })
    .catch(err => console.error('Error tirando generador:', err));
}

/**
 * Desmarca todas las entradas de un generador como "usado" (para reiniciar
 * antes de una sesión nueva) y refresca la vista.
 * @param {string} slug
 * @returns {void}
 */
function generatorResetUsados(slug) {
  fetch(`/api/generators/${slug}/reset`, { method: 'POST' })
    .then(() => showContentDetail('rule', slug))
    .catch(err => console.error('Error reiniciando generador:', err));
}

/**
 * Marca/desmarca una entrada como usada (checkbox manual, independiente
 * de la tirada aleatoria).
 * @param {number} entryId
 * @param {boolean} usado
 * @returns {void}
 */
function generatorToggleUsado(entryId, usado) {
  fetch(`/api/generators/entries/${entryId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usado }),
  })
    .then(r => r.json())
    .then(() => {
      const row = document.querySelector(`.generator-entry[data-entry-id="${entryId}"]`);
      if (row) row.classList.toggle('generator-entry--usado', usado);
    })
    .catch(err => console.error('Error marcando entrada:', err));
}

/**
 * Convierte el texto de una entrada en editable in-place; al perder el foco
 * o pulsar Enter, guarda el cambio vía API.
 * @param {number} entryId
 * @param {HTMLElement} span
 * @returns {void}
 */
function generatorEditEntry(entryId, span) {
  if (span.isContentEditable) return;
  span.contentEditable = "true";
  span.focus();

  const guardar = () => {
    span.contentEditable = "false";
    span.removeEventListener('blur', guardar);
    span.removeEventListener('keydown', onKey);
    const texto = span.textContent.trim();
    if (!texto) return;
    fetch(`/api/generators/entries/${entryId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto }),
    }).catch(err => console.error('Error guardando entrada:', err));
  };
  const onKey = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); span.blur(); }
  };
  span.addEventListener('blur', guardar);
  span.addEventListener('keydown', onKey);
}

/**
 * Elimina una entrada de un generador tras confirmación, y la quita del DOM.
 * @param {number} entryId
 * @returns {void}
 */
function generatorDeleteEntry(entryId) {
  if (!confirm('¿Eliminar esta entrada?')) return;
  fetch(`/api/generators/entries/${entryId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      const row = document.querySelector(`.generator-entry[data-entry-id="${entryId}"]`);
      if (row) row.remove();
    })
    .catch(err => console.error('Error eliminando entrada:', err));
}

/**
 * Añade una nueva entrada al generador a partir del input de texto libre,
 * y refresca la vista para mostrarla en la lista.
 * @param {string} slug
 * @param {HTMLInputElement} input
 * @returns {void}
 */
function generatorAddEntry(slug, input) {
  const texto = input.value.trim();
  if (!texto) return;
  fetch(`/api/generators/${slug}/entries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texto }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      input.value = '';
      showContentDetail('rule', slug);
    })
    .catch(err => console.error('Error añadiendo entrada:', err));
}

// ========== PNJ RÁPIDO POR CATEGORÍA (BD: PnjCategoria) ==========

/**
 * Sistema activo (adnd2e, darksun, etc.), leído del mismo bloque JSON que
 * usa el reproductor de audio. Las categorías de PNJ y el catálogo de
 * equipo son independientes por sistema para no mezclar contenido entre
 * ambientaciones.
 * @returns {string}
 */
function pnjSistemaActivo() {
  try {
    return JSON.parse(document.getElementById('system-config').textContent || '{}').id || 'adnd2e';
  } catch (e) {
    return 'adnd2e';
  }
}

/**
 * Rellena el <select> de categorías de PNJ desde la API. Se llama al abrir
 * la ficha del generador "PNJ Rápido".
 * @returns {void}
 */
function pnjCargarCategorias() {
  const select = document.getElementById('pnjCategoriaSelect');
  if (!select) return;
  fetch('/api/pnj-categorias?sistema=' + pnjSistemaActivo())
    .then(r => r.json())
    .then(cats => {
      if (!cats.length) {
        select.innerHTML = '<option value="">Sin categorías — crea una abajo</option>';
        return;
      }
      select.innerHTML = cats.map(c => `<option value="${c.id}">${c.nombre}</option>`).join('');
    })
    .catch(err => console.error('Error cargando categorías de PNJ:', err));
}

/** Último PNJ generado (nombre/categoria/dg/genero/stats/equipo, más rasgos
 * y descripcion una vez generados), para poder guardarlo en el roster sin
 * tener que re-parsear el DOM. */
let pnjUltimoResultado = null;

/**
 * Genera un PNJ: llama a /api/pnj-categorias/generar con la categoría
 * seleccionada (o al azar si se marcó la casilla) y los Dados de Golpe
 * indicados, y pinta las estadísticas + equipo resultantes.
 * @returns {void}
 */
function pnjGenerar() {
  const select = document.getElementById('pnjCategoriaSelect');
  const azar = document.getElementById('pnjCategoriaAzar').checked;
  const dg = parseInt(document.getElementById('pnjDgInput').value, 10) || 1;
  const genero = document.getElementById('pnjGeneroSelect').value;
  const resultado = document.getElementById('pnjGenResultado');

  const body = { dg, genero, sistema: pnjSistemaActivo() };
  if (!azar && select.value) body.categoria_id = parseInt(select.value, 10);

  fetch('/api/pnj-categorias/generar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { resultado.innerHTML = `<p class="generator-empty">${data.error}</p>`; return; }
      pnjUltimoResultado = data;
      pnjUltimoResultado.rasgos = [];
      pnjUltimoResultado.descripcion = '';
      document.getElementById('pnjDescripcionResultado').innerHTML = '';
      pnjPintarResultado(data);
    })
    .catch(err => console.error('Error generando PNJ:', err));
}

/**
 * Pinta el resultado de un PNJ generado (nombre, categoría, DG, stats,
 * equipo) en el panel de resultado. Separado de pnjGenerar para poder
 * repintar tras un simple re-roll de nombre sin regenerar todo lo demás.
 * @param {Object} data - Resultado de /api/pnj-categorias/generar.
 * @returns {void}
 */
function pnjPintarResultado(data) {
  const resultado = document.getElementById('pnjGenResultado');
  const statsHtml = Object.entries(data.stats)
    .map(([k, v]) => `<span class="stat"><span class="stat__k">${k.toUpperCase()}</span><span class="stat__v">${v}</span></span>`)
    .join('');
  const equipoHtml = data.equipo.length
    ? `<ul class="pnj-gen-resultado__equipo">${data.equipo.map(e => `<li>${e}</li>`).join('')}</ul>`
    : '<p class="generator-empty">Sin equipo definido para esta categoría.</p>';
  const generoLabel = { masculino: 'Masculino', femenino: 'Femenino', aleatorio: 'Género aleatorio' }[data.genero] || data.genero;
  resultado.dataset.categoria = data.categoria;
  resultado.dataset.dg = data.dg;
  resultado.innerHTML = `
    <div class="pnj-gen-resultado__nombre">
      <strong>${data.nombre}</strong>
      <button type="button" class="generator-entry__del" onclick="pnjRerollNombre()" title="Nuevo nombre">🎲</button>
    </div>
    <div>${data.categoria} — ${data.dg} DG — <span class="chip">${generoLabel}</span></div>
    <div class="pnj-gen-resultado__stats">${statsHtml || '<span class="generator-empty">Sin estadísticas configuradas</span>'}</div>
    ${equipoHtml}
    <button type="button" class="generator-roll__btn generator-roll__btn--ghost" style="margin-top:8px;" onclick="pnjAnadirAIniciativa()">⚔️ Añadir a Iniciativa</button>
  `;
}

/**
 * Añade el último PNJ generado (pnjUltimoResultado) al tracker de
 * iniciativa como combatiente de tipo "monster". Como el generador no
 * calcula puntos de golpe (solo las 6 características), se piden con un
 * prompt sugiriendo un valor aproximado a partir de los DG.
 * @returns {void}
 */
function pnjAnadirAIniciativa() {
  if (!pnjUltimoResultado) { alert('Genera un PNJ primero.'); return; }
  pnjPedirHpYAnadir(pnjUltimoResultado.nombre, pnjUltimoResultado.dg);
}

/**
 * Añade un PNJ guardado del roster al tracker de iniciativa. Recupera la
 * ficha completa (nombre/DG) antes de pedir los puntos de golpe.
 * @param {number} entryId
 * @returns {void}
 */
function pnjAnadirRosterAIniciativa(entryId) {
  fetch(`/api/pnj-roster/${entryId}`)
    .then(r => r.json())
    .then(e => {
      if (e.error) { alert(e.error); return; }
      pnjPedirHpYAnadir(e.nombre, e.dg);
    })
    .catch(err => console.error('Error cargando PNJ del roster:', err));
}

/**
 * Pide los puntos de golpe (con un valor sugerido a partir de los DG) y
 * añade el combatiente al tracker de iniciativa vía /api/characters.
 * @param {string} nombre
 * @param {number} dg
 * @returns {void}
 */
function pnjPedirHpYAnadir(nombre, dg) {
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
    .then(data => {
      if (!data.success) { alert('No se pudo añadir a iniciativa.'); return; }
    })
    .catch(err => console.error('Error añadiendo a iniciativa:', err));
}

/**
 * Vuelve a tirar solo el nombre del PNJ ya generado (mantiene stats/equipo
 * en pantalla), respetando el género seleccionado en el formulario.
 * @returns {void}
 */
function pnjRerollNombre() {
  const genero = document.getElementById('pnjGeneroSelect').value;
  fetch('/api/pnj-categorias/nombre', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ genero }),
  })
    .then(r => r.json())
    .then(data => {
      const nombreEl = document.querySelector('.pnj-gen-resultado__nombre strong');
      if (nombreEl) nombreEl.textContent = data.nombre;
      if (pnjUltimoResultado) pnjUltimoResultado.nombre = data.nombre;
    })
    .catch(err => console.error('Error regenerando nombre:', err));
}

// ========== DESCRIPCIÓN POR IA / PLANTILLA Y ROSTER (BD: PnjRosterEntry) ==========

/**
 * Rellena los checkboxes de rasgos de personalidad desde la API. Se llama
 * al abrir la ficha del generador "PNJ Rápido".
 * @returns {void}
 */
function pnjCargarRasgos() {
  const cont = document.getElementById('pnjRasgosCheckboxes');
  if (!cont) return;
  fetch('/api/pnj-categorias/rasgos')
    .then(r => r.json())
    .then(rasgos => {
      cont.innerHTML = rasgos.map(r => `
        <label class="pnj-rasgo-chip">
          <input type="checkbox" value="${r.id}"> ${r.label}
        </label>
      `).join('');
    })
    .catch(err => console.error('Error cargando rasgos:', err));
}

/**
 * Devuelve los ids de los rasgos marcados en el panel.
 * @returns {string[]}
 */
function pnjRasgosSeleccionados() {
  const cont = document.getElementById('pnjRasgosCheckboxes');
  if (!cont) return [];
  return Array.from(cont.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
}

/**
 * Rellena el selector de modelo de IA reutilizando /api/assistant/models
 * (mismo endpoint que usa el asistente RAG). Si no hay modelos disponibles
 * (Ollama caído y sin clave de Claude), deja el selector vacío — el
 * generador de descripción sigue funcionando en modo plantilla.
 * @returns {void}
 */
function pnjCargarModelosIa() {
  const select = document.getElementById('pnjModeloIaSelect');
  if (!select) return;
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

/**
 * Genera la descripción del último PNJ generado (con IA si está marcado el
 * checkbox, o por plantilla si no), a partir de los rasgos seleccionados.
 * Si la IA falla (sin clave/Ollama caído), el backend cae automáticamente
 * a la plantilla y lo indica en la respuesta.
 * @returns {void}
 */
function pnjGenerarDescripcion() {
  if (!pnjUltimoResultado) { alert('Genera un PNJ primero.'); return; }
  const usarIa = document.getElementById('pnjUsarIaCheck').checked;
  const modelo = document.getElementById('pnjModeloIaSelect').value;
  const rasgos = pnjRasgosSeleccionados();
  const resultado = document.getElementById('pnjDescripcionResultado');
  resultado.innerHTML = '<p class="generator-empty">Generando...</p>';

  fetch('/api/pnj-categorias/descripcion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre: pnjUltimoResultado.nombre,
      categoria: pnjUltimoResultado.categoria,
      dg: pnjUltimoResultado.dg,
      genero: pnjUltimoResultado.genero,
      rasgos, usar_ia: usarIa, model: modelo, sistema: pnjSistemaActivo(),
    }),
  })
    .then(r => r.json())
    .then(data => {
      pnjUltimoResultado.rasgos = rasgos;
      pnjUltimoResultado.descripcion = data.descripcion || '';
      const aviso = data.fuente === 'plantilla_fallback'
        ? '<p class="generator-empty">⚠️ IA no disponible — configura tu clave desde el asistente (💬). Se usó una descripción de plantilla.</p>'
        : '';
      resultado.innerHTML = `<p>${data.descripcion || ''}</p>${aviso}`;
    })
    .catch(err => console.error('Error generando descripción:', err));
}

/**
 * Guarda el último PNJ generado (con su descripción, si se generó) en el
 * roster, junto a las notas libres del formulario.
 * @returns {void}
 */
function pnjGuardarEnRoster() {
  if (!pnjUltimoResultado) { alert('Genera un PNJ primero.'); return; }
  const notasInput = document.getElementById('pnjNotasInput');
  fetch('/api/pnj-roster', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre: pnjUltimoResultado.nombre,
      categoria: pnjUltimoResultado.categoria,
      dg: pnjUltimoResultado.dg,
      genero: pnjUltimoResultado.genero,
      stats: pnjUltimoResultado.stats,
      equipo: pnjUltimoResultado.equipo,
      rasgos: pnjUltimoResultado.rasgos || [],
      descripcion: pnjUltimoResultado.descripcion || '',
      notas: notasInput.value.trim(),
      sistema: pnjSistemaActivo(),
    }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      notasInput.value = '';
      pnjCargarRoster();
    })
    .catch(err => console.error('Error guardando en el roster:', err));
}

/**
 * Lista los PNJs guardados en el roster del sistema activo.
 * @returns {void}
 */
function pnjCargarRoster() {
  const listado = document.getElementById('pnjRosterListado');
  if (!listado) return;
  fetch('/api/pnj-roster?sistema=' + pnjSistemaActivo())
    .then(r => r.json())
    .then(entradas => {
      if (!entradas.length) {
        listado.innerHTML = '<p class="generator-empty">Sin PNJs guardados todavía.</p>';
        return;
      }
      listado.innerHTML = entradas.map(e => `
        <div class="pnj-cat-listado__item">
          <strong>${e.nombre}</strong>
          <span class="chip">${e.categoria} — ${e.dg} DG</span>
          <button type="button" onclick="pnjAnadirRosterAIniciativa(${e.id})" title="Añadir a Iniciativa">⚔️</button>
          <button type="button" onclick="pnjBorrarRosterEntry(${e.id})" title="Eliminar">✕</button>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error cargando el roster:', err));
}

/**
 * Elimina un PNJ del roster tras confirmación.
 * @param {number} entryId
 * @returns {void}
 */
function pnjBorrarRosterEntry(entryId) {
  if (!confirm('¿Eliminar este PNJ del roster?')) return;
  fetch(`/api/pnj-roster/${entryId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      pnjCargarRoster();
      if (document.getElementById('jugadoresPnjList')) jugadoresPnjCargarRoster();
    })
    .catch(err => console.error('Error borrando PNJ del roster:', err));
}

// ========== SUB-PESTAÑA "Jugadores → PNJs" (mismo roster, vista tipo ficha) ==========

/**
 * Carga el roster de PNJs guardados en la sub-pestaña "PNJs" de Jugadores,
 * con tarjetas al estilo de las de PJ (nombre, categoría, descripción,
 * botones de iniciativa y borrado).
 * @returns {void}
 */
function jugadoresPnjCargarRoster() {
  const list = document.getElementById('jugadoresPnjList');
  if (!list) return;
  fetch('/api/pnj-roster?sistema=' + pnjSistemaActivo())
    .then(r => r.json())
    .then(entradas => {
      if (!entradas.length) {
        list.innerHTML = '<div style="text-align:center;color:var(--muted,#aaa);font-size:12px;padding:20px 0;">Sin PNJs guardados. Créalos desde Reglas → PNJ Rápido.</div>';
        return;
      }
      list.innerHTML = entradas.map(e => `
        <div class="tarjeta player-card" data-id="${e.id}">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="width:32px;height:32px;border-radius:50%;background:var(--line,#333);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">👤</div>
            <div style="flex:1;min-width:0;">
              <strong style="display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${e.nombre}</strong>
              <small style="color:var(--muted,#aaa);">${e.categoria} · ${e.dg} DG</small>
            </div>
          </div>
          ${e.descripcion ? `<p style="font-size:11px;color:var(--muted,#aaa);margin:6px 0 0;">${e.descripcion}</p>` : ''}
          ${e.notas ? `<p style="font-size:11px;color:var(--muted,#aaa);margin:2px 0 0;"><em>${e.notas}</em></p>` : ''}
          <div style="display:flex;gap:4px;margin-top:6px;">
            <button class="btn-sm" style="font-size:10px;padding:2px 6px;flex:1;" onclick="pnjAnadirRosterAIniciativa(${e.id})" title="Añadir a iniciativa">⚔️ Iniciativa</button>
            <button class="btn-sm" style="font-size:10px;padding:2px 6px;color:#e74c3c;" onclick="pnjBorrarRosterEntry(${e.id})" title="Eliminar">🗑</button>
          </div>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error cargando PNJs de Jugadores:', err));
}

/**
 * Actualiza el precio de un objeto del catálogo de equipo al cambiarlo
 * inline en el listado.
 * @param {number} itemId
 * @param {string} precio
 * @returns {void}
 */
function pnjActualizarPrecioEquipo(itemId, precio) {
  fetch(`/api/equipo/${itemId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ precio: precio === '' ? null : parseFloat(precio) }),
  }).catch(err => console.error('Error actualizando precio:', err));
}

// ========== PESTAÑA "🎒 EQUIPO" (catálogo completo, sin categoría) ==========

/** Último listado de equipo cargado, para abrir el detalle sin necesitar
 * un endpoint GET /api/equipo/<id> que hoy no existe. */
let equipoItemsCache = [];

/**
 * Carga el catálogo de equipo del sistema activo en la pestaña "Equipo",
 * con nombre clicable (detalle/edición), precio editable y borrado.
 * @returns {void}
 */
function equipoCargarCatalogo() {
  const listado = document.getElementById('equipoCatalogoListado');
  if (!listado) return;
  fetch('/api/equipo?sistema=' + pnjSistemaActivo())
    .then(r => r.json())
    .then(items => {
      equipoItemsCache = items;
      if (!items.length) {
        listado.innerHTML = '<p class="generator-empty">Catálogo vacío — añade el primer objeto abajo.</p>';
        return;
      }
      listado.innerHTML = items.map(item => `
        <div class="pnj-cat-equipo-listado__item" data-equipo-id="${item.id}">
          <span style="flex:1 1 auto;cursor:pointer;text-decoration:underline dotted;" onclick="equipoAbrirDetalle(${item.id})" title="Ver/editar descripción">${item.nombre}${item.descripcion ? ` <small class="generator-empty">— ${item.descripcion}</small>` : ''}</span>
          Precio <input type="number" class="search-box pnj-equipo-precio" value="${item.precio ?? ''}"
            onchange="pnjActualizarPrecioEquipo(${item.id}, this.value)">
          <button type="button" class="generator-entry__del" onclick="equipoBorrarItem(${item.id})" title="Eliminar">✕</button>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error cargando catálogo de equipo:', err));
}

/** Id del objeto de equipo actualmente abierto en el modal de detalle. */
let equipoDetalleId = null;

/**
 * Abre el modal de detalle de un objeto del catálogo (nombre + descripción
 * editable), usando la caché ya cargada en pantalla.
 * @param {number} itemId
 * @returns {void}
 */
function equipoAbrirDetalle(itemId) {
  const item = equipoItemsCache.find(i => i.id === itemId);
  if (!item) return;
  equipoDetalleId = itemId;
  document.getElementById('equipoModalNombre').textContent = item.nombre;
  document.getElementById('equipoModalDescripcion').value = item.descripcion || '';
  document.getElementById('equipoModal').style.display = 'flex';
}

/**
 * Guarda la descripción editada del objeto de equipo abierto en el modal.
 * @returns {void}
 */
function equipoGuardarDetalle() {
  if (!equipoDetalleId) return;
  const descripcion = document.getElementById('equipoModalDescripcion').value;
  fetch(`/api/equipo/${equipoDetalleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ descripcion }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      document.getElementById('equipoModal').style.display = 'none';
      equipoCargarCatalogo();
    })
    .catch(err => console.error('Error guardando descripción de equipo:', err));
}

document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('equipoModal');
  if (!modal) return;
  document.getElementById('equipoModalCancel').addEventListener('click', () => { modal.style.display = 'none'; });
  document.getElementById('equipoModalSave').addEventListener('click', equipoGuardarDetalle);
  modal.addEventListener('click', e => { if (e.target === modal) modal.style.display = 'none'; });
});

/**
 * Crea un objeto nuevo en el catálogo desde la pestaña "Equipo" y refresca
 * el listado.
 * @returns {void}
 */
function equipoCrearItem() {
  const nombreInput = document.getElementById('equipoNuevoNombre');
  const descInput = document.getElementById('equipoNuevoDescripcion');
  const precioInput = document.getElementById('equipoNuevoPrecio');
  const nombre = nombreInput.value.trim();
  if (!nombre) return;
  fetch('/api/equipo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre,
      descripcion: descInput.value.trim(),
      precio: precioInput.value === '' ? null : parseFloat(precioInput.value),
      sistema: pnjSistemaActivo(),
    }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      nombreInput.value = '';
      descInput.value = '';
      precioInput.value = '';
      equipoCargarCatalogo();
    })
    .catch(err => console.error('Error creando objeto de catálogo:', err));
}

/**
 * Elimina un objeto del catálogo tras confirmación (también desasigna
 * automáticamente el objeto de cualquier categoría de PNJ que lo tuviera).
 * @param {number} itemId
 * @returns {void}
 */
function equipoBorrarItem(itemId) {
  if (!confirm('¿Eliminar este objeto del catálogo? Se quitará también de cualquier categoría que lo tenga asignado.')) return;
  fetch(`/api/equipo/${itemId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      equipoCargarCatalogo();
    })
    .catch(err => console.error('Error borrando objeto de catálogo:', err));
}

/**
 * Crea una nueva categoría de PNJ a partir del formulario "+ Nueva
 * categoría": parsea las líneas "atributo:base:bonus_dg:tope" a JSON y las
 * manda junto al equipo básico a la API. Recarga el <select> al terminar.
 * @returns {void}
 */
function pnjCrearCategoria() {
  const nombre = document.getElementById('pnjNuevaCatNombre').value.trim();
  const statsRaw = document.getElementById('pnjNuevaCatStats').value.trim();
  const equipo = document.getElementById('pnjNuevaCatEquipo').value.trim();
  if (!nombre) { alert('Ponle un nombre a la categoría.'); return; }

  const statsConfig = {};
  statsRaw.split('\n').forEach(linea => {
    const partes = linea.split(':').map(p => p.trim());
    if (partes.length < 2 || !partes[0]) return;
    const [attr, base, bonusDg, tope] = partes;
    statsConfig[attr.toLowerCase()] = {
      base: parseFloat(base) || 0,
      bonus_dg: parseFloat(bonusDg) || 0,
      ...(tope !== undefined && tope !== '' ? { tope: parseFloat(tope) } : {}),
    };
  });

  fetch('/api/pnj-categorias', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, stats_config: statsConfig, equipo_basico: equipo }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      document.getElementById('pnjNuevaCatNombre').value = '';
      document.getElementById('pnjNuevaCatStats').value = '';
      document.getElementById('pnjNuevaCatEquipo').value = '';
      pnjCargarCategorias();
    })
    .catch(err => console.error('Error creando categoría de PNJ:', err));
}

// ========== GESTIÓN VISUAL DE CATEGORÍAS DE PNJ (6 stats + equipo) ==========

const PNJ_ATTRS = ['fue', 'des', 'con', 'int', 'sab', 'car'];

/** Ids de equipo asignados a la categoría que se está editando ahora mismo
 * (para poder calcular qué desasignar al guardar si se destildan). */
let pnjEquipoAsignadoOriginal = new Set();

/**
 * Carga el listado de categorías existentes con botones editar/borrar, y
 * también refresca el <select> del generador. Se llama al abrir la ficha
 * de PNJ Rápido.
 * @returns {void}
 */
function pnjCargarCategoriasListado() {
  const listado = document.getElementById('pnjCategoriasListado');
  if (!listado) return;
  fetch('/api/pnj-categorias?sistema=' + pnjSistemaActivo())
    .then(r => r.json())
    .then(cats => {
      if (!cats.length) {
        listado.innerHTML = '<p class="generator-empty">Sin categorías todavía.</p>';
        return;
      }
      listado.innerHTML = cats.map(c => `
        <div class="pnj-cat-listado__item">
          <strong>${c.nombre}</strong>
          <button type="button" onclick="pnjEditarCategoria(${c.id})" title="Editar">✏️</button>
          <button type="button" onclick="pnjBorrarCategoria(${c.id})" title="Eliminar">✕</button>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error listando categorías de PNJ:', err));
}

/**
 * Resetea el formulario de categoría a estado "nueva" (sin id, stats por
 * defecto, catálogo de equipo sin nada marcado).
 * @returns {void}
 */
function pnjLimpiarFormulario() {
  document.getElementById('pnjCatEditId').value = '';
  document.getElementById('pnjCatNombre').value = '';
  document.querySelectorAll('#pnjCatStatsBody tr').forEach(row => {
    row.querySelector('.pnj-cat-attr-incluir').checked = true;
    row.querySelector('.pnj-cat-attr-base').value = 10;
    row.querySelector('.pnj-cat-attr-bonus').value = 0;
    row.querySelector('.pnj-cat-attr-tope').value = 18;
  });
  pnjEquipoAsignadoOriginal = new Set();
  pnjCargarCatalogoEquipo({});
}

/**
 * Carga los datos de una categoría existente (stats + equipo asignado) en
 * el formulario, para editarla.
 * @param {number} categoriaId
 * @returns {void}
 */
function pnjEditarCategoria(categoriaId) {
  Promise.all([
    fetch('/api/pnj-categorias?sistema=' + pnjSistemaActivo()).then(r => r.json()),
    fetch(`/api/equipo/categoria/${categoriaId}`).then(r => r.json()),
  ]).then(([cats, asignaciones]) => {
    const cat = cats.find(c => c.id === categoriaId);
    if (!cat) return;

    document.getElementById('pnjCatEditId').value = cat.id;
    document.getElementById('pnjCatNombre').value = cat.nombre;

    document.querySelectorAll('#pnjCatStatsBody tr').forEach(row => {
      const attr = row.dataset.attr;
      const cfg = cat.stats_config[attr];
      row.querySelector('.pnj-cat-attr-incluir').checked = !!cfg;
      row.querySelector('.pnj-cat-attr-base').value = cfg ? cfg.base : 10;
      row.querySelector('.pnj-cat-attr-bonus').value = cfg ? (cfg.bonus_dg || 0) : 0;
      row.querySelector('.pnj-cat-attr-tope').value = cfg && cfg.tope !== undefined ? cfg.tope : 18;
    });

    const nivelesPorId = {};
    asignaciones.forEach(a => { nivelesPorId[a.equipo_id] = a.nivel_minimo; });
    pnjEquipoAsignadoOriginal = new Set(asignaciones.map(a => a.equipo_id));
    pnjCargarCatalogoEquipo(nivelesPorId);
  }).catch(err => console.error('Error cargando categoría para editar:', err));
}

/**
 * Elimina una categoría de PNJ tras confirmación, y refresca los listados.
 * @param {number} categoriaId
 * @returns {void}
 */
function pnjBorrarCategoria(categoriaId) {
  if (!confirm('¿Eliminar esta categoría de PNJ?')) return;
  fetch(`/api/pnj-categorias/${categoriaId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      pnjCargarCategoriasListado();
      pnjCargarCategorias();
      pnjLimpiarFormulario();
    })
    .catch(err => console.error('Error borrando categoría:', err));
}

/**
 * Renderiza el catálogo completo de equipo como checkboxes + input de nivel
 * mínimo, marcando los que ya están en `nivelesPorId` (equipo_id -> nivel).
 * @param {Object<number, number>} nivelesPorId
 * @returns {void}
 */
function pnjCargarCatalogoEquipo(nivelesPorId) {
  const listado = document.getElementById('pnjCatEquipoListado');
  if (!listado) return;
  fetch('/api/equipo?sistema=' + pnjSistemaActivo())
    .then(r => r.json())
    .then(items => {
      if (!items.length) {
        listado.innerHTML = '<p class="generator-empty">Catálogo vacío — añade el primer objeto abajo.</p>';
        return;
      }
      listado.innerHTML = items.map(item => {
        const marcado = nivelesPorId[item.id] !== undefined;
        const nivel = marcado ? nivelesPorId[item.id] : 1;
        return `
          <div class="pnj-cat-equipo-listado__item" data-equipo-id="${item.id}">
            <label>
              <input type="checkbox" class="pnj-equipo-check" ${marcado ? 'checked' : ''}>
              ${item.nombre}
            </label>
            DG mín. <input type="number" class="search-box pnj-equipo-nivel" value="${nivel}" min="1">
            Precio <input type="number" class="search-box pnj-equipo-precio" value="${item.precio ?? ''}"
              onchange="pnjActualizarPrecioEquipo(${item.id}, this.value)">
          </div>
        `;
      }).join('');
    })
    .catch(err => console.error('Error cargando catálogo de equipo:', err));
}

/**
 * Añade un objeto nuevo al catálogo reutilizable de equipo (sin asignarlo
 * todavía a ninguna categoría) y refresca el listado de checkboxes.
 * @returns {void}
 */
function pnjCrearItemCatalogo() {
  const input = document.getElementById('pnjNuevoItemNombre');
  const precioInput = document.getElementById('pnjNuevoItemPrecio');
  const nombre = input.value.trim();
  if (!nombre) return;
  const precio = precioInput.value === '' ? null : parseFloat(precioInput.value);
  fetch('/api/equipo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, precio, sistema: pnjSistemaActivo() }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      input.value = '';
      precioInput.value = '';
      // Recarga preservando lo que ya estaba marcado en pantalla
      const nivelesActuales = {};
      document.querySelectorAll('.pnj-cat-equipo-listado__item').forEach(el => {
        const check = el.querySelector('.pnj-equipo-check');
        if (check.checked) {
          nivelesActuales[el.dataset.equipoId] = el.querySelector('.pnj-equipo-nivel').value;
        }
      });
      pnjCargarCatalogoEquipo(nivelesActuales);
    })
    .catch(err => console.error('Error creando objeto de catálogo:', err));
}

/**
 * Guarda la categoría (crea si pnjCatEditId está vacío, actualiza si no) con
 * las 6 estadísticas del formulario, y sincroniza las asignaciones de
 * equipo (asigna las marcadas, desasigna las que estaban y ya no lo están).
 * @returns {void}
 */
function pnjGuardarCategoria() {
  const idEdit = document.getElementById('pnjCatEditId').value;
  const nombre = document.getElementById('pnjCatNombre').value.trim();
  if (!nombre) { alert('Ponle un nombre a la categoría.'); return; }

  const statsConfig = {};
  document.querySelectorAll('#pnjCatStatsBody tr').forEach(row => {
    if (!row.querySelector('.pnj-cat-attr-incluir').checked) return;
    const attr = row.dataset.attr;
    statsConfig[attr] = {
      base: parseFloat(row.querySelector('.pnj-cat-attr-base').value) || 0,
      bonus_dg: parseFloat(row.querySelector('.pnj-cat-attr-bonus').value) || 0,
      tope: parseFloat(row.querySelector('.pnj-cat-attr-tope').value),
    };
  });

  const guardarPromise = idEdit
    ? fetch(`/api/pnj-categorias/${idEdit}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, stats_config: statsConfig }),
      }).then(r => r.json())
    : fetch('/api/pnj-categorias', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, stats_config: statsConfig, sistema: pnjSistemaActivo() }),
      }).then(r => r.json());

  guardarPromise.then(cat => {
    if (cat.error) { alert(cat.error); return; }

    // Sincronizar equipo: marcados -> asignar, desmarcados-que-estaban -> desasignar
    const marcadosAhora = new Set();
    const peticiones = [];
    document.querySelectorAll('.pnj-cat-equipo-listado__item').forEach(el => {
      const equipoId = parseInt(el.dataset.equipoId, 10);
      const check = el.querySelector('.pnj-equipo-check');
      if (check.checked) {
        marcadosAhora.add(equipoId);
        const nivel = parseInt(el.querySelector('.pnj-equipo-nivel').value, 10) || 1;
        peticiones.push(fetch(`/api/equipo/categoria/${cat.id}/asignar`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ equipo_id: equipoId, nivel_minimo: nivel }),
        }));
      }
    });
    pnjEquipoAsignadoOriginal.forEach(equipoId => {
      if (!marcadosAhora.has(equipoId)) {
        peticiones.push(fetch(`/api/equipo/categoria/${cat.id}/desasignar/${equipoId}`, { method: 'DELETE' }));
      }
    });

    Promise.all(peticiones).then(() => {
      pnjCargarCategoriasListado();
      pnjCargarCategorias();
      pnjLimpiarFormulario();
    });
  }).catch(err => console.error('Error guardando categoría:', err));
}

// ========== CLIMA (selector de entorno sobre varias GeneratorTable) ==========

/**
 * Construye el HTML de la lista de entradas de clima para el entorno
 * seleccionado (igual estructura visual que el resto de generadores, pero
 * pintada por JS porque la tabla real depende de la selección del cliente).
 * @param {Array<Object>} entries
 * @returns {string}
 */
function _climaRenderEntradas(entries) {
  if (!entries.length) return '<p class="generator-empty">Sin entradas todavía. Añade la primera abajo.</p>';
  return entries.map((e, i) => `
    <div class="generator-entry ${e.usado ? 'generator-entry--usado' : ''}" data-entry-id="${e.id}">
      <label class="generator-entry__check">
        <input type="checkbox" onchange="climaToggleUsado(${e.id}, this.checked)" ${e.usado ? 'checked' : ''}>
      </label>
      <span class="generator-entry__num">${i + 1}</span>
      <span class="generator-entry__texto" onclick="climaEditarEntrada(${e.id}, this)">${e.texto}</span>
      <button type="button" class="generator-entry__del" onclick="climaBorrarEntrada(${e.id})" title="Eliminar">✕</button>
    </div>
  `).join('');
}

/**
 * Carga y pinta las entradas del entorno actualmente seleccionado en
 * #climaZonaSelect. Se llama al abrir la ficha y cada vez que se cambia
 * de entorno.
 * @returns {void}
 */
function climaCambiarZona() {
  const slug = document.getElementById('climaZonaSelect').value;
  const lista = document.getElementById('climaEntriesList');
  const resultado = document.getElementById('climaResultado');
  if (resultado) resultado.textContent = '';
  fetch(`/api/generators/${slug}/entries`)
    .then(r => r.json())
    .then(entries => { lista.innerHTML = _climaRenderEntradas(entries); })
    .catch(err => console.error('Error cargando entradas de clima:', err));
}

/** @returns {string} slug real de la GeneratorTable del entorno seleccionado ahora mismo. */
function _climaSlugActual() {
  return document.getElementById('climaZonaSelect').value;
}

/**
 * Tira/elige al azar sobre el entorno actualmente seleccionado.
 * @returns {void}
 */
function climaTirar() {
  const slug = _climaSlugActual();
  fetch(`/api/generators/${slug}/roll`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    .then(r => r.json())
    .then(entry => {
      if (entry.error) { alert(entry.error); return; }
      document.querySelectorAll('#climaEntriesList .generator-entry.roll-highlight')
        .forEach(el => el.classList.remove('roll-highlight'));
      const row = document.querySelector(`#climaEntriesList .generator-entry[data-entry-id="${entry.id}"]`);
      if (row) {
        row.classList.add('roll-highlight', 'generator-entry--usado');
        row.querySelector('input[type="checkbox"]').checked = true;
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      document.getElementById('climaResultado').textContent = entry.texto;
    })
    .catch(err => console.error('Error tirando clima:', err));
}

/**
 * Desmarca todas las entradas "usadas" del entorno seleccionado y refresca
 * la lista.
 * @returns {void}
 */
function climaReiniciarUsadas() {
  fetch(`/api/generators/${_climaSlugActual()}/reset`, { method: 'POST' })
    .then(() => climaCambiarZona())
    .catch(err => console.error('Error reiniciando clima:', err));
}

/**
 * Marca/desmarca una entrada de clima como usada.
 * @param {number} entryId
 * @param {boolean} usado
 * @returns {void}
 */
function climaToggleUsado(entryId, usado) {
  fetch(`/api/generators/entries/${entryId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ usado }),
  })
    .then(() => {
      const row = document.querySelector(`#climaEntriesList .generator-entry[data-entry-id="${entryId}"]`);
      if (row) row.classList.toggle('generator-entry--usado', usado);
    })
    .catch(err => console.error('Error marcando entrada de clima:', err));
}

/**
 * Edita el texto de una entrada de clima in-place (igual mecánica que el
 * resto de generadores).
 * @param {number} entryId
 * @param {HTMLElement} span
 * @returns {void}
 */
function climaEditarEntrada(entryId, span) {
  if (span.isContentEditable) return;
  span.contentEditable = "true";
  span.focus();
  const guardar = () => {
    span.contentEditable = "false";
    span.removeEventListener('blur', guardar);
    span.removeEventListener('keydown', onKey);
    const texto = span.textContent.trim();
    if (!texto) return;
    fetch(`/api/generators/entries/${entryId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto }),
    }).catch(err => console.error('Error guardando entrada de clima:', err));
  };
  const onKey = (e) => { if (e.key === 'Enter') { e.preventDefault(); span.blur(); } };
  span.addEventListener('blur', guardar);
  span.addEventListener('keydown', onKey);
}

/**
 * Elimina una entrada de clima tras confirmación.
 * @param {number} entryId
 * @returns {void}
 */
function climaBorrarEntrada(entryId) {
  if (!confirm('¿Eliminar esta entrada?')) return;
  fetch(`/api/generators/entries/${entryId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      const row = document.querySelector(`#climaEntriesList .generator-entry[data-entry-id="${entryId}"]`);
      if (row) row.remove();
    })
    .catch(err => console.error('Error borrando entrada de clima:', err));
}

/**
 * Añade una entrada nueva al entorno actualmente seleccionado y refresca
 * la lista.
 * @returns {void}
 */
function climaAnadirEntrada() {
  const input = document.getElementById('climaNuevaEntrada');
  const texto = input.value.trim();
  if (!texto) return;
  fetch(`/api/generators/${_climaSlugActual()}/entries`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      input.value = '';
      climaCambiarZona();
    })
    .catch(err => console.error('Error añadiendo entrada de clima:', err));
}

// ========== EDITAR / BORRAR FICHA ==========

/**
 * Sustituye el contenido del modal por un textarea con el markdown crudo
 * (frontmatter + cuerpo) de la ficha actual, para editarlo a mano.
 * @returns {void}
 */
function editContentInline() {
  if (!currentContentType || !currentContentSlug) return;

  fetch(`/api/content/${currentContentType}/${currentContentSlug}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      const container = document.getElementById('monsterDetailContent');
      container.dataset.prevHtml = container.innerHTML;
      container.innerHTML =
        '<textarea id="contentEditArea" spellcheck="false" ' +
        'style="width:100%;min-height:420px;font-family:monospace;font-size:12px;' +
        'background:var(--panel,#1a1a1a);color:var(--text,#eee);border:1px solid var(--line,#444);' +
        'border-radius:4px;padding:10px;box-sizing:border-box;"></textarea>' +
        '<div style="display:flex;gap:8px;margin-top:8px;justify-content:flex-end;">' +
        '<button class="btn-portrait" data-action="modal-edit-cancel">Cancelar</button>' +
        '<button class="primary" data-action="modal-edit-save">💾 Guardar</button>' +
        '</div>';
      document.getElementById('contentEditArea').value = data.content;
    })
    .catch(err => alert('Error al cargar la ficha para editar: ' + err));
}

/** Descarta la edición en curso y restaura la vista de detalle previa. @returns {void} */
function cancelEditContent() {
  const container = document.getElementById('monsterDetailContent');
  if (container.dataset.prevHtml !== undefined) {
    container.innerHTML = container.dataset.prevHtml;
    delete container.dataset.prevHtml;
  }
}

/** Guarda el markdown editado (PUT) y refresca el detalle y la tarjeta de la lista. @returns {void} */
function saveEditedContent() {
  const area = document.getElementById('contentEditArea');
  if (!area) return;
  const content = area.value;

  fetch(`/api/content/${currentContentType}/${currentContentSlug}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      const container = document.getElementById('monsterDetailContent');
      delete container.dataset.prevHtml;
      showContentDetail(currentContentType, currentContentSlug);

      const nombre = data.metadata && (data.metadata.nombre || data.metadata.title);
      if (nombre) {
        const card = document.querySelector(
          `.tarjeta[data-ctype="${currentContentType}"][data-slug="${currentContentSlug}"]`
        );
        if (card) {
          card.setAttribute('data-nombre', nombre);
          const strong = card.querySelector('strong');
          if (strong) strong.textContent = nombre;
        }
      }
    })
    .catch(err => alert('Error al guardar: ' + err));
}

/** Pide confirmación y borra la ficha actual por completo (fichero + índice RAG). @returns {void} */
function deleteContentConfirm() {
  if (!currentContentType || !currentContentSlug) return;
  const label = currentContentTitle || currentContentSlug;
  if (!confirm(`¿Borrar "${label}" definitivamente? Esta acción no se puede deshacer.`)) return;

  fetch(`/api/content/${currentContentType}/${currentContentSlug}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      const card = document.querySelector(
        `.tarjeta[data-ctype="${currentContentType}"][data-slug="${currentContentSlug}"]`
      );
      if (card) card.remove();
      hideModal();
    })
    .catch(err => alert('Error al borrar: ' + err));
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
  const stressEl = document.getElementById('charStress');
  const stress = stressEl ? (parseInt(stressEl.value, 10) || 0) : 0;

  if (!name) return;

  fetch('/api/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, initiative, hp, max_hp: hp, stress, max_stress: stress, type: 'player' })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        document.getElementById('charName').value = '';
        document.getElementById('charInitiative').value = '';
        document.getElementById('charHP').value = '';
        if (stressEl) stressEl.value = '';
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
 * Updates the stress of a character (Mothership).
 *
 * @param {number} id - Character ID.
 * @param {number} stress - New stress value.
 * @returns {void}
 */
function updateStress(id, stress) {
  fetch(`/api/characters/${id}/stress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stress })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) loadGameState();
    });
}

/**
 * Updates the initiative value of a character (reorders the roster).
 *
 * @param {number} id - Character ID.
 * @param {number} initiative - New initiative value.
 * @returns {void}
 */
function updateInitiative(id, initiative) {
  fetch(`/api/characters/${id}/initiative`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initiative })
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
        _activeTurnSheetCharId = null;
        renderActiveTurnSheet(null);
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

    const stressHtml = systemConfig.has_stress ? `
      <div style="display:flex;flex-direction:column;align-items:center">
        <input type="number" class="stress-input" value="${char.stress ?? 0}" data-stress-id="${char.id}" title="${systemConfig.stress_label}">
        <span class="stat-label">EST</span>
      </div>
    ` : '';

    item.innerHTML = `
      <div style="flex:1;min-width:0">
        <strong>${escapeHtml(char.name)}</strong>
        <div class="char-meta">${escapeHtml(char.type || '')}</div>
      </div>
      <div style="display:flex;align-items:center;gap:5px">
        <div style="display:flex;flex-direction:column;align-items:center">
          <input type="number" class="ini-input" value="${char.initiative}" data-ini-id="${char.id}" title="${systemConfig.initiative_label || 'Iniciativa'}" style="width:34px;">
          <span class="stat-label">${systemConfig.initiative_label || 'Ini'}</span>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center">
          <input type="number" class="hp-input" value="${char.hp ?? 0}" data-hp-id="${char.id}" title="${systemConfig.hp_label}">
          <span class="stat-label">${systemConfig.hp_label}</span>
        </div>
        ${stressHtml}
        <button class="danger" onclick="deleteCharacter(${char.id})">×</button>
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

  if (char.portrait_path) {
    container.style.display = 'block';
    img.src = char.portrait_path;
    name.textContent = char.name;
  } else {
    container.style.display = 'none';
  }

  loadActiveTurnSheet(char.id);
}

let _activeTurnSheetCharId = null;

/**
 * Fetches and renders a stats/attacks summary for the character whose turn
 * is active, so the DM doesn't have to open the grimoire modal mid-combat.
 * Cached by character id to avoid refetching on every 3s poll.
 * @param {number} charId
 * @returns {void}
 */
function loadActiveTurnSheet(charId) {
  if (charId === _activeTurnSheetCharId) return;
  _activeTurnSheetCharId = charId;

  fetch(`/api/characters/${charId}/sheet`)
    .then(r => r.json())
    .then(data => renderActiveTurnSheet(data.success ? data.sheet : null))
    .catch(() => renderActiveTurnSheet(null));
}

/**
 * Renders the stat chips + body (attacks/description) for the active-turn
 * character. Supports both the 5e/Dark Sun field schema (hp/ac/challenge/xp)
 * and the AD&D2e schema (ca/thac0/dg/movimiento/px), plus plain player
 * sheets (hp_max/ca/atributos/ataques).
 * @param {{metadata: object, html: string}|null} sheet
 * @returns {void}
 */
function renderActiveTurnSheet(sheet) {
  const el = document.getElementById('active-turn-sheet');
  if (!el) return;

  if (!sheet || !sheet.metadata) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }

  const m = sheet.metadata;
  const chips = [];
  const addChip = (label, val) => {
    if (val !== undefined && val !== null && val !== '') {
      chips.push(`<div class="stat"><span class="stat__k">${escapeHtml(label)}</span><span class="stat__v">${escapeHtml(String(val))}</span></div>`);
    }
  };

  addChip(systemConfig.hp_label || 'PV', m.hp ?? m.hp_max);
  addChip('CA', m.ac ?? m.ca);
  addChip('Desafío', m.challenge ?? m.desafio);
  addChip('THAC0', m.thac0);
  addChip('Dados de Golpe', m.dg);
  addChip('PX', m.xp ?? m.px);
  addChip('Movimiento', m.movimiento ?? m.speed);
  addChip('Clase', m.clase);
  addChip('Nivel', m.nivel);

  let bodyHtml = '';
  if (sheet.html) {
    bodyHtml = sheet.html;
  } else if (m.ataques) {
    bodyHtml = '<h3>Ataques</h3><p>' + escapeHtml(m.ataques).replace(/\n/g, '<br>') + '</p>';
  }

  if (chips.length === 0 && !bodyHtml) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }

  el.innerHTML =
    `<div class="active-turn-sheet__stats">${chips.join('')}</div>` +
    `<div class="active-turn-sheet__body">${bodyHtml}</div>`;
  el.style.display = 'block';
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
  if (type === 'html') input.accept = '.html,.htm';

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
        } else if (type === 'html') {
          document.getElementById('webpageUrl').value = data.url;
          updateStatus(`HTML subido: ${data.filename}`);
        } else {
          loadAudioList();
          updateStatus("Audio uploaded");
          // Abrir modal de etiquetado para el archivo recién subido
          setTimeout(() => openTagModal(data.filename, { categories: [], systems: [] }), 400);
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
    body: JSON.stringify({ action: 'youtube_toggle' })
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
/**
 * Projects a webpage (URL or uploaded HTML) on the player screen.
 * Reads the URL from #webpageUrl input.
 *
 * Backend:
 * - POST /api/screen/show-webpage with JSON { url }
 *
 * @returns {void}
 */
function showWebpage() {
  const url = document.getElementById('webpageUrl').value.trim();
  if (!url) return;

  fetch('/api/screen/show-webpage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) updateStatus("Página proyectada");
    });
}

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

// ── Whiteboard state ──────────────────────────────────────────────────────────
let wbHistory = []; let wbHIdx = -1; let wbSuppressH = false;
let wbRoomCounter = 1;
let wbConnectSource = null;
let wbGridMode = null;
let wbMapImageObj = null;
let wbImgLocked = true;
let wbSaveTimer = null;

const WB_BGS = {
  dark:      { canvas:'#111111', grid:'rgba(200,180,100,0.15)' },
  parchment: { canvas:'#f0ead0', grid:'rgba(80,60,20,0.22)' },
  light:     { canvas:'#f8f8f4', grid:'rgba(80,60,20,0.18)' },
  dungeon:   { canvas:'#1a1208', grid:'rgba(200,180,100,0.12)' },
};

function initWhiteboard() {
  const wrap = document.getElementById('canvasContainer');
  const canvasEl = document.getElementById('masterCanvas');
  // Usar dimensiones reales o fallback si el layout aún no está calculado
  const initW = wrap.clientWidth  || 400;
  const initH = wrap.clientHeight || 300;
  canvasEl.width  = initW;
  canvasEl.height = initH;

  masterCanvas = new fabric.Canvas('masterCanvas', {
    isDrawingMode: true,
    backgroundColor: WB_BGS.parchment.canvas,
    stopContextMenu: true,
    fireRightClick: false,
  });
  masterCanvas.freeDrawingBrush.color = document.getElementById('drawingColor').value;
  masterCanvas.freeDrawingBrush.width = parseInt(document.getElementById('drawingLineWidth').value, 10);

  // ── Background ──────────────────────────────────────────────────
  function wbApplyBg(key) {
    const bg = WB_BGS[key] || WB_BGS.parchment;
    wrap.style.background = bg.canvas;
    masterCanvas.backgroundColor = bg.canvas;
    masterCanvas.renderAll();
    const sqStroke  = document.getElementById('wb-sq-stroke');
    const hexStroke = document.getElementById('wb-hex-stroke');
    if (sqStroke)  sqStroke.setAttribute('stroke',  bg.grid);
    if (hexStroke) hexStroke.setAttribute('stroke', bg.grid);
    if (currentTool === 'eraser' && masterCanvas.freeDrawingBrush) {
      masterCanvas.freeDrawingBrush.color = bg.canvas;
    }
  }
  wbApplyBg('parchment');
  document.getElementById('wb-bg-select').addEventListener('change', e => { wbApplyBg(e.target.value); wbSave(); });

  // ── Grid (SVG overlay) ──────────────────────────────────────────
  const wbGridSVG  = document.getElementById('wb-grid-svg');
  const wbGridRect = document.getElementById('wb-grid-rect');
  const btnGridSq  = document.getElementById('btn-wb-grid-sq');
  const btnGridHex = document.getElementById('btn-wb-grid-hex');
  if (btnGridSq) btnGridSq.addEventListener('click', () => {
    if (wbGridMode === 'sq') { wbGridMode=null; wbGridSVG.style.display='none'; btnGridSq.style.borderColor=''; }
    else { wbGridMode='sq'; wbGridRect.setAttribute('fill','url(#wb-pat-sq)'); wbGridSVG.style.display=''; btnGridSq.style.borderColor='var(--accent)'; if (btnGridHex) btnGridHex.style.borderColor=''; }
  });
  if (btnGridHex) btnGridHex.addEventListener('click', () => {
    if (wbGridMode === 'hex') { wbGridMode=null; wbGridSVG.style.display='none'; btnGridHex.style.borderColor=''; }
    else { wbGridMode='hex'; wbGridRect.setAttribute('fill','url(#wb-pat-hex)'); wbGridSVG.style.display=''; btnGridHex.style.borderColor='var(--accent)'; if (btnGridSq) btnGridSq.style.borderColor=''; }
  });

  // ── Color palette ────────────────────────────────────────────────
  document.querySelectorAll('.wb-pc').forEach(btn => {
    btn.addEventListener('click', () => {
      const c = btn.dataset.color;
      document.getElementById('drawingColor').value = c;
      if (masterCanvas.freeDrawingBrush && currentTool !== 'eraser') masterCanvas.freeDrawingBrush.color = c;
      document.querySelectorAll('.wb-pc').forEach(b => b.classList.remove('sel'));
      btn.classList.add('sel');
    });
  });
  document.getElementById('drawingColor').addEventListener('input', e => {
    if (masterCanvas.freeDrawingBrush && currentTool !== 'eraser') masterCanvas.freeDrawingBrush.color = e.target.value;
    document.querySelectorAll('.wb-pc').forEach(b => b.classList.remove('sel'));
  });
  document.getElementById('drawingLineWidth').addEventListener('input', e => {
    if (!masterCanvas.freeDrawingBrush) return;
    masterCanvas.freeDrawingBrush.width = currentTool === 'eraser'
      ? parseInt(e.target.value) * 3
      : parseInt(e.target.value);
  });

  // ── Image background ─────────────────────────────────────────────
  document.getElementById('wb-btn-img-upload').addEventListener('click', () => document.getElementById('wb-img-file-input').click());
  document.getElementById('wb-img-file-input').addEventListener('change', e => {
    const file = e.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      if (wbMapImageObj) { masterCanvas.remove(wbMapImageObj); wbMapImageObj = null; }
      fabric.Image.fromURL(ev.target.result, img => {
        const scale = Math.min(masterCanvas.width / img.width, masterCanvas.height / img.height);
        img.set({ left: masterCanvas.width/2, top: masterCanvas.height/2, originX:'center', originY:'center',
          scaleX:scale, scaleY:scale, opacity: parseInt(document.getElementById('wb-img-opacity').value)/100,
          selectable:false, evented:false, lockMovementX:true, lockMovementY:true, customType:'map-bg' });
        wbMapImageObj = img;
        masterCanvas.add(img);
        masterCanvas.sendToBack(img);
        document.getElementById('wb-btn-img-remove').style.display = '';
        wbSnapshot(); wbSave();
      });
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  });
  document.getElementById('wb-img-opacity').addEventListener('input', e => {
    const op = parseInt(e.target.value)/100;
    masterCanvas.getObjects().filter(o => o.customType==='map-bg').forEach(o => o.set('opacity', op));
    masterCanvas.renderAll();
  });
  document.getElementById('wb-btn-img-lock').addEventListener('click', () => {
    wbImgLocked = !wbImgLocked;
    masterCanvas.getObjects().filter(o => o.customType==='map-bg').forEach(o => {
      o.selectable = !wbImgLocked; o.evented = !wbImgLocked;
      o.lockMovementX = wbImgLocked; o.lockMovementY = wbImgLocked;
    });
    document.getElementById('wb-btn-img-lock').textContent = wbImgLocked ? '🔒' : '🔓';
    masterCanvas.renderAll();
  });
  document.getElementById('wb-btn-img-remove').addEventListener('click', () => {
    masterCanvas.getObjects().filter(o => o.customType==='map-bg').forEach(o => masterCanvas.remove(o));
    wbMapImageObj = null;
    document.getElementById('wb-btn-img-remove').style.display = 'none';
    document.getElementById('wb-btn-img-lock').textContent = '🔒';
    wbImgLocked = true;
    masterCanvas.renderAll();
    wbSnapshot(); wbSave();
  });

  // ── Canvas events ─────────────────────────────────────────────────
  masterCanvas.on('path:created',    () => { wbSnapshot(); wbSave(); });
  masterCanvas.on('object:modified', () => { wbSnapshot(); wbSave(); });

  setupShapeDrawing();
  loadWhiteboardState();
  window.addEventListener('resize', resizeCanvas);
  // Garantizar dimensiones correctas tras el primer render del navegador
  requestAnimationFrame(() => requestAnimationFrame(resizeCanvas));
}

function resizeCanvas() {
  if (!masterCanvas) return;
  const wrap = document.getElementById('canvasContainer');
  const w = wrap.clientWidth  || 400;
  const h = wrap.clientHeight || 300;
  masterCanvas.setWidth(w);
  masterCanvas.setHeight(h);
  masterCanvas.renderAll();
}

function wbSnap(v) { return document.getElementById('snapGrid')?.checked ? Math.round(v/40)*40 : v; }

function wbSnapshot() {
  if (wbSuppressH) return;
  const s = JSON.stringify(masterCanvas.toJSON(['customType','roomId']));
  wbHistory.splice(wbHIdx+1); wbHistory.push(s);
  if (wbHistory.length > 60) wbHistory.shift(); else wbHIdx++;
}

function wbApplySnap(json) {
  wbSuppressH = true;
  masterCanvas.loadFromJSON(json, () => { masterCanvas.renderAll(); wbSuppressH = false; });
}

function setTool(tool) {
  if (!masterCanvas) return;
  currentTool = tool;

  document.querySelectorAll('.tool-btn[data-tool]').forEach(b => b.classList.remove('active'));
  document.querySelector(`.tool-btn[data-tool="${tool}"]`)?.classList.add('active');

  const tokenCtrl   = document.getElementById('wb-token-ctrl');
  const connectHint = document.getElementById('wb-connect-hint');
  if (tokenCtrl)   tokenCtrl.style.display   = tool === 'token'    ? 'flex' : 'none';
  if (connectHint) connectHint.style.display  = tool === 'conectar' ? 'flex' : 'none';

  masterCanvas.isDrawingMode = (tool === 'brush' || tool === 'eraser');
  masterCanvas.selection     = (tool === 'select');

  masterCanvas.getObjects().forEach(o => {
    if (tool === 'select') {
      o.selectable = true; o.evented = true;
    } else if (tool === 'conectar') {
      o.selectable = false; o.evented = (o.customType === 'sala');
    } else {
      o.selectable = false; o.evented = false;
    }
  });

  const bgKey = document.getElementById('wb-bg-select')?.value || 'parchment';
  const bgColor = (WB_BGS[bgKey] || WB_BGS.parchment).canvas;

  if (tool === 'eraser') {
    masterCanvas.freeDrawingBrush = new fabric.PencilBrush(masterCanvas);
    masterCanvas.freeDrawingBrush.color = bgColor;
    masterCanvas.freeDrawingBrush.width = parseInt(document.getElementById('drawingLineWidth').value)*3;
  } else if (tool === 'brush') {
    masterCanvas.freeDrawingBrush = new fabric.PencilBrush(masterCanvas);
    masterCanvas.freeDrawingBrush.color = document.getElementById('drawingColor').value;
    masterCanvas.freeDrawingBrush.width = parseInt(document.getElementById('drawingLineWidth').value);
  }

  if (tool !== 'conectar') {
    if (wbConnectSource) { wbConnectSource.set('opacity',1); masterCanvas.renderAll(); }
    wbConnectSource = null;
    const msg = document.getElementById('wb-connect-msg');
    if (msg) msg.textContent = 'Clic en sala A…';
  }
}

// ── Shape drawing ─────────────────────────────────────────────────────────────
function setupShapeDrawing() {
  masterCanvas.on('mouse:down', opt => {
    const tool = currentTool;
    if (tool === 'brush' || tool === 'eraser' || tool === 'select') return;
    const p = masterCanvas.getPointer(opt.e);

    if (tool === 'sala') {
      isDrawingShape = true;
      shapeOrigX = wbSnap(p.x); shapeOrigY = wbSnap(p.y);
      activeShape = new fabric.Rect({ left:shapeOrigX, top:shapeOrigY, width:1, height:1,
        fill:'rgba(46,38,32,0.3)', stroke:'#e0c870', strokeWidth:1, strokeDashArray:[4,3],
        selectable:false, evented:false });
      masterCanvas.add(activeShape);
    } else if (tool === 'conectar') {
      const hit = wbHitSala(p);
      if (!hit) return;
      if (!wbConnectSource) {
        wbConnectSource = hit; hit.set('opacity',0.55); masterCanvas.renderAll();
        const msg = document.getElementById('wb-connect-msg');
        if (msg) msg.textContent = 'Clic en sala B…';
      } else if (hit !== wbConnectSource) {
        wbConnectSource.set('opacity',1);
        wbBuildCorridor(wbConnectSource, hit);
        wbConnectSource = null;
        const msg = document.getElementById('wb-connect-msg');
        if (msg) msg.textContent = 'Clic en sala A…';
      }
    } else if (tool === 'text') {
      const size = parseInt(document.getElementById('drawingLineWidth').value)*4+10;
      const txt = new fabric.IText('Texto', { left:p.x, top:p.y, fontFamily:'Cinzel,Georgia,serif',
        fontSize:size, fill:document.getElementById('drawingColor').value, selectable:true, editable:true });
      masterCanvas.add(txt); masterCanvas.setActiveObject(txt);
      txt.enterEditing(); txt.selectAll();
      wbSnapshot(); wbSave();
    } else if (tool === 'token') {
      const num   = document.getElementById('wb-token-num')?.value || '1';
      const color = document.getElementById('wb-token-color')?.value || '#2266cc';
      const circ  = new fabric.Circle({ radius:18, fill:color, stroke:'#fff', strokeWidth:1.5, originX:'center', originY:'center' });
      const lbl   = new fabric.Text(String(num), { fontSize:15, fontFamily:'Cinzel,Georgia,serif', fontWeight:'bold', fill:'#fff', originX:'center', originY:'center', selectable:false, evented:false });
      const grp   = new fabric.Group([circ,lbl], { left:p.x, top:p.y, originX:'center', originY:'center', selectable:true });
      masterCanvas.add(grp);
      const numEl = document.getElementById('wb-token-num');
      if (numEl) numEl.value = parseInt(num)+1;
      wbSnapshot(); wbSave();
    } else {
      // line / rect / circle
      isDrawingShape = true;
      shapeOrigX = p.x; shapeOrigY = p.y;
      const color = document.getElementById('drawingColor').value;
      const lw    = parseInt(document.getElementById('drawingLineWidth').value);
      if (tool === 'line')   activeShape = new fabric.Line([p.x,p.y,p.x,p.y], {stroke:color,strokeWidth:lw,selectable:false,evented:false});
      if (tool === 'rect')   activeShape = new fabric.Rect({left:p.x,top:p.y,width:0,height:0,stroke:color,strokeWidth:lw,fill:'transparent',selectable:false,evented:false});
      if (tool === 'circle') activeShape = new fabric.Ellipse({left:p.x,top:p.y,rx:0,ry:0,stroke:color,strokeWidth:lw,fill:'transparent',selectable:false,evented:false});
      if (activeShape) masterCanvas.add(activeShape);
    }
  });

  masterCanvas.on('mouse:move', opt => {
    if (!isDrawingShape || !activeShape) return;
    const p = masterCanvas.getPointer(opt.e);
    const tool = currentTool;
    if (tool === 'sala') {
      const ex=wbSnap(p.x), ey=wbSnap(p.y);
      activeShape.set({ left:Math.min(ex,shapeOrigX), top:Math.min(ey,shapeOrigY), width:Math.abs(ex-shapeOrigX), height:Math.abs(ey-shapeOrigY) });
    } else if (tool === 'line')   activeShape.set({x2:p.x,y2:p.y});
    else if (tool === 'rect')     activeShape.set({width:Math.abs(p.x-shapeOrigX),height:Math.abs(p.y-shapeOrigY),left:Math.min(p.x,shapeOrigX),top:Math.min(p.y,shapeOrigY)});
    else if (tool === 'circle')   activeShape.set({rx:Math.abs(p.x-shapeOrigX)/2,ry:Math.abs(p.y-shapeOrigY)/2,left:Math.min(p.x,shapeOrigX),top:Math.min(p.y,shapeOrigY)});
    masterCanvas.renderAll();
  });

  masterCanvas.on('mouse:up', opt => {
    if (!isDrawingShape) return;
    isDrawingShape = false;
    if (currentTool === 'sala' && activeShape) {
      masterCanvas.remove(activeShape); activeShape = null;
      const p = masterCanvas.getPointer(opt.e);
      const ex=wbSnap(p.x), ey=wbSnap(p.y);
      const left=Math.min(ex,shapeOrigX), top=Math.min(ey,shapeOrigY);
      const width=Math.max(Math.abs(ex-shapeOrigX),80), height=Math.max(Math.abs(ey-shapeOrigY),80);
      wbPlaceRoom(left,top,width,height);
    } else if (activeShape) {
      activeShape.setCoords();
      activeShape = null;
      wbSnapshot(); wbSave();
    }
  });

  // Delete selected with keyboard
  document.addEventListener('keydown', e => {
    if ((e.key==='Delete'||e.key==='Backspace') && !e.target.closest('input,textarea,[contenteditable]')) {
      const obj = masterCanvas?.getActiveObject();
      if (obj) { masterCanvas.remove(obj); wbSnapshot(); wbSave(); }
    }
  });
}

function wbHitSala(pointer) {
  return masterCanvas.getObjects().filter(o => o.customType==='sala').reverse().find(o => {
    const br = o.getBoundingRect(true,true);
    return pointer.x>=br.left && pointer.x<=br.left+br.width && pointer.y>=br.top && pointer.y<=br.top+br.height;
  });
}

function wbPlaceRoom(left, top, width, height) {
  const fill = document.getElementById('drawingColor').value || '#2e2620';
  const num  = wbRoomCounter++;
  const outer = new fabric.Rect({ left, top, width, height, fill, stroke:'#a09070', strokeWidth:2 });
  const inner = new fabric.Rect({ left:left+4, top:top+4, width:width-8, height:height-8, fill:'transparent', stroke:'#a09070', strokeWidth:0.6, strokeDashArray:[4,3] });
  const label = new fabric.Text(String(num), { left:left+8, top:top+6, fontSize:14, fontFamily:'Cinzel,Georgia,serif', fill:'#e0c870', fontWeight:'bold' });
  const group = new fabric.Group([outer,inner,label], { selectable:false, evented:false, customType:'sala', roomId:num });
  masterCanvas.add(group);
  masterCanvas.bringToFront(group);
  masterCanvas.renderAll();
  wbSnapshot(); wbSave();
}

function wbBuildCorridor(rA, rB) {
  const W = 40; const fill = '#2e2620'; const stk = '#7a6a4a';
  const a = (br => ({cx:br.left+br.width/2,cy:br.top+br.height/2}))(rA.getBoundingRect(true,true));
  const b = (br => ({cx:br.left+br.width/2,cy:br.top+br.height/2}))(rB.getBoundingRect(true,true));
  const dx=Math.abs(b.cx-a.cx), dy=Math.abs(b.cy-a.cy);
  const rects = [];
  if (dx < W) {
    rects.push(new fabric.Rect({left:a.cx-W/2,top:Math.min(a.cy,b.cy),width:W,height:Math.abs(b.cy-a.cy),fill,stroke:stk,strokeWidth:1,selectable:false,evented:false,customType:'pasillo'}));
  } else if (dy < W) {
    rects.push(new fabric.Rect({left:Math.min(a.cx,b.cx),top:a.cy-W/2,width:Math.abs(b.cx-a.cx),height:W,fill,stroke:stk,strokeWidth:1,selectable:false,evented:false,customType:'pasillo'}));
  } else {
    rects.push(new fabric.Rect({left:Math.min(a.cx,b.cx),top:a.cy-W/2,width:Math.abs(b.cx-a.cx)+W/2,height:W,fill,stroke:stk,strokeWidth:1,selectable:false,evented:false,customType:'pasillo'}));
    rects.push(new fabric.Rect({left:b.cx-W/2,top:Math.min(a.cy,b.cy),width:W,height:Math.abs(b.cy-a.cy)+W/2,fill,stroke:stk,strokeWidth:1,selectable:false,evented:false,customType:'pasillo'}));
  }
  rects.forEach(r => { masterCanvas.add(r); masterCanvas.sendToBack(r); });
  masterCanvas.getObjects().filter(o=>o.customType==='sala').forEach(o=>masterCanvas.bringToFront(o));
  masterCanvas.renderAll();
  wbSnapshot(); wbSave();
}

function clearCanvas() {
  if (!confirm("¿Borrar toda la pizarra?")) return;
  masterCanvas.clear();
  const bgKey = document.getElementById('wb-bg-select')?.value || 'parchment';
  masterCanvas.backgroundColor = (WB_BGS[bgKey]||WB_BGS.parchment).canvas;
  wbMapImageObj=null; wbImgLocked=true; wbRoomCounter=1; wbConnectSource=null;
  document.getElementById('wb-btn-img-remove').style.display='none';
  document.getElementById('wb-btn-img-lock').textContent='🔒';
  wbHistory.splice(0); wbHIdx=-1;
  wbSnapshot(); wbSave();
}

function wbSave() {
  clearTimeout(wbSaveTimer);
  wbSaveTimer = setTimeout(() => {
    const state = JSON.stringify(masterCanvas.toJSON(['customType','roomId']));
    const meta  = { bg: document.getElementById('wb-bg-select')?.value || 'parchment', grid: wbGridMode };
    fetch('/api/whiteboard/save', { method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({state,meta}) }).catch(()=>{});
  }, 700);
}

function saveWhiteboardState() { wbSave(); }

function loadWhiteboardState() {
  fetch('/api/whiteboard/load')
    .then(r => r.json())
    .then(data => {
      if (!data || !data.state) { wbSnapshot(); return; }
      wbSuppressH = true;
      masterCanvas.loadFromJSON(data.state, () => {
        masterCanvas.renderAll(); wbSuppressH = false;
        wbSnapshot();
        setTool(currentTool);
        const has = masterCanvas.getObjects().some(o => o.customType==='map-bg');
        document.getElementById('wb-btn-img-remove').style.display = has ? '' : 'none';
      });
      if (data.meta?.bg) {
        document.getElementById('wb-bg-select').value = data.meta.bg;
        // wbApplyBg is scoped inside initWhiteboard — apply inline
        const bg = WB_BGS[data.meta.bg] || WB_BGS.parchment;
        masterCanvas.backgroundColor = bg.canvas;
        masterCanvas.renderAll();
      }
    })
    .catch(() => { wbSnapshot(); });
}

function projectWhiteboard() {
  fetch('/api/screen/command', { method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({type:'whiteboard'}) })
    .then(r => r.json())
    .then(data => { if (data.success) updateStatus("Pizarra proyectada"); });
}

function stopProjectingWhiteboard() {}
function toggleWhiteboardFullscreen() {
  window.open('/view/whiteboard', '_blank');
}
function toggleGrid() {}  // legacy — ahora via SVG overlay

// ========== AUDIO ==========

// ── Audio state ──────────────────────────────────────────────────────────────
let audioAllTracks = [];        // [{filename, categories, systems}]
let audioActiveCategory = '';   // '' = todas
let audioActiveSystem = '';     // '' = todos
let audioSelectedTrack = '';    // filename actualmente seleccionado
let audioLoop = false;          // repetir pista actual
let audioShuffle = false;       // orden aleatorio
let audioAutoplay = false;      // autoplay al cambiar categoría
let audioPlaylistMode = false;  // playlist activa (sobreescribe filtros)
let audioPlaylistTracks = [];   // [filename, ...] de la playlist activa
let audioPlaylistEditing = false; // modo edición: añadir/quitar pistas
let audioPlaylistSelection = new Set(); // pistas seleccionadas en modo edición

function fmtTime(s) {
  if (!isFinite(s)) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function initAudio() {
  masterAudioElement = document.getElementById('master-audio-element');
  loadAudioList();

  // Timeline events
  const timeline = document.getElementById('audioTimeline');
  masterAudioElement.addEventListener('timeupdate', () => {
    if (!masterAudioElement.duration) return;
    const pct = (masterAudioElement.currentTime / masterAudioElement.duration) * 100;
    timeline.value = pct;
    document.getElementById('audioCurrentTime').textContent = fmtTime(masterAudioElement.currentTime);
  });
  masterAudioElement.addEventListener('loadedmetadata', () => {
    document.getElementById('audioDuration').textContent = fmtTime(masterAudioElement.duration);
    timeline.value = 0;
    document.getElementById('audioCurrentTime').textContent = '0:00';
  });
  masterAudioElement.addEventListener('ended', () => {
    timeline.value = 0;
    document.getElementById('audioCurrentTime').textContent = '0:00';
    if (audioLoop) {
      masterAudioElement.play().catch(() => {});
    } else {
      playNextTrack();
    }
  });
  timeline.addEventListener('input', () => {
    if (!masterAudioElement.duration) return;
    masterAudioElement.currentTime = (timeline.value / 100) * masterAudioElement.duration;
  });

  // Auto-set sistema activo al del sistema de juego actual
  const systemConfig = JSON.parse(document.getElementById('system-config').textContent || '{}');
  if (systemConfig.id) {
    audioActiveSystem = systemConfig.id;
    document.querySelectorAll('.audio-sys-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.sys === audioActiveSystem);
    });
  }

  // Filtros por categoría — autoplay al cambiar
  document.getElementById('audioCategoryFilters').addEventListener('click', e => {
    const btn = e.target.closest('.audio-filter-btn');
    if (!btn) return;
    audioActiveCategory = btn.dataset.cat;
    document.querySelectorAll('.audio-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderAudioList();
    autoplayOnFilterChange();
  });

  // Filtros por sistema
  document.getElementById('audioSystemFilters').addEventListener('click', e => {
    const btn = e.target.closest('.audio-sys-btn');
    if (!btn) return;
    audioActiveSystem = btn.dataset.sys;
    document.querySelectorAll('.audio-sys-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderAudioList();
  });

  // Cargar playlists guardadas
  loadPlaylists();

  // Modal de etiquetado
  document.getElementById('audioTagCancel').addEventListener('click', closeTagModal);
  document.getElementById('audioTagSave').addEventListener('click', saveAudioTagsFromModal);
  document.getElementById('audioTagModal').addEventListener('click', e => {
    if (e.target === document.getElementById('audioTagModal')) closeTagModal();
  });
  document.querySelectorAll('#audioTagModal .tag-chip').forEach(chip => {
    chip.addEventListener('click', () => chip.classList.toggle('active'));
  });
}

function loadAudioList() {
  fetch('/api/audio/list')
    .then(r => r.json())
    .then(tracks => {
      audioAllTracks = tracks || [];
      renderAudioList();
    })
    .catch(err => console.error("Error loading audio list:", err));
}

function renderAudioList() {
  const container = document.getElementById('audioTrackList');
  if (!container) return;

  const filtered = getFilteredTracks();

  if (!filtered.length) {
    container.innerHTML = '<div class="audio-track-item" style="color:var(--muted);cursor:default;">Sin pistas para estos filtros</div>';
    return;
  }

  // En modo edición mostrar TODAS las pistas (no solo las filtradas)
  const displayTracks = audioPlaylistEditing && !audioPlaylistMode
    ? audioAllTracks
    : filtered;

  const modeLabel = audioPlaylistMode
    ? `<div style="font-size:10px;color:var(--accent,#5a8a5a);padding:2px 6px;">📋 Playlist activa · <span style="cursor:pointer;text-decoration:underline" id="exitPlaylistBtn">Salir</span></div>`
    : '';

  container.innerHTML = modeLabel + displayTracks.map(t => {
    const tagSummary = [...t.categories, ...t.systems].join(', ');
    const sel = t.filename === audioSelectedTrack ? ' selected' : '';
    const inPl = audioPlaylistSelection.has(t.filename) ? ' in-playlist' : '';

    let extraBtn = '';
    if (audioPlaylistEditing) {
      const icon = audioPlaylistSelection.has(t.filename) ? '✓' : '+';
      extraBtn = `<button class="audio-add-btn" data-add-file="${t.filename}" title="Añadir/quitar de playlist">${icon}</button>`;
    } else {
      extraBtn = `<button class="audio-tag-btn" data-tag-file="${t.filename}" title="Etiquetar">🏷</button>`;
    }

    return `<div class="audio-track-item${sel}${inPl}" data-filename="${t.filename}">
      <span class="audio-track-name" title="${t.filename}">${t.filename}</span>
      <span class="audio-track-tags">${tagSummary}</span>
      ${extraBtn}
    </div>`;
  }).join('');

  container.querySelectorAll('.audio-track-item').forEach(row => {
    row.addEventListener('click', e => {
      if (e.target.closest('.audio-tag-btn') || e.target.closest('.audio-add-btn')) return;
      if (audioPlaylistEditing) {
        toggleTrackInPlaylistSelection(row.dataset.filename);
      } else {
        selectAudioTrack(row.dataset.filename);
      }
    });
  });

  container.querySelectorAll('.audio-tag-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const track = audioAllTracks.find(t => t.filename === btn.dataset.tagFile);
      openTagModal(btn.dataset.tagFile, track);
    });
  });

  container.querySelectorAll('.audio-add-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      toggleTrackInPlaylistSelection(btn.dataset.addFile);
    });
  });

  document.getElementById('exitPlaylistBtn')?.addEventListener('click', exitPlaylistMode);
}

function getFilteredTracks() {
  if (audioPlaylistMode && audioPlaylistTracks.length) {
    return audioPlaylistTracks
      .map(fn => audioAllTracks.find(t => t.filename === fn))
      .filter(Boolean);
  }
  return audioAllTracks.filter(t => {
    const catOk = !audioActiveCategory || t.categories.includes(audioActiveCategory);
    // systems vacío = compatible con todos los sistemas
    const sysOk = !audioActiveSystem || !t.systems.length || t.systems.includes(audioActiveSystem);
    return catOk && sysOk;
  });
}

function selectAudioTrack(filename) {
  audioSelectedTrack = filename;
  renderAudioList();
  const nowPlaying = document.getElementById('audioNowPlaying');
  if (nowPlaying) nowPlaying.textContent = filename ? `▶ ${filename}` : '';
}

function playNextTrack() {
  const filtered = getFilteredTracks();
  if (!filtered.length) return;
  let next;
  if (audioShuffle) {
    next = filtered[Math.floor(Math.random() * filtered.length)].filename;
  } else {
    const idx = filtered.findIndex(t => t.filename === audioSelectedTrack);
    next = filtered[(idx + 1) % filtered.length].filename;
  }
  selectAudioTrack(next);
  playMasterAudio();
}

function autoplayOnFilterChange() {
  if (!audioAutoplay) return;
  const filtered = getFilteredTracks();
  if (!filtered.length) return;
  const pick = audioShuffle
    ? filtered[Math.floor(Math.random() * filtered.length)].filename
    : filtered[0].filename;
  selectAudioTrack(pick);
  playMasterAudio();
}

function toggleAutoplay() {
  audioAutoplay = !audioAutoplay;
  document.getElementById('btnAutoplay').classList.toggle('on', audioAutoplay);
}

function toggleLoop() {
  audioLoop = !audioLoop;
  document.getElementById('btnLoop').classList.toggle('on', audioLoop);
  if (masterAudioElement) masterAudioElement.loop = false; // lo gestionamos nosotros via ended
}

function toggleShuffle() {
  audioShuffle = !audioShuffle;
  document.getElementById('btnShuffle').classList.toggle('on', audioShuffle);
}

function openAudioPicker() {
  openFilePicker('audio');
}

function playMasterAudio() {
  if (!masterAudioElement || !audioSelectedTrack) return;
  masterAudioElement.src = `/static/uploads/audio/${audioSelectedTrack}`;
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

// ── Playlists ─────────────────────────────────────────────────────────────────

function loadPlaylists() {
  fetch('/api/playlists')
    .then(r => r.json())
    .then(data => {
      const sel = document.getElementById('playlistSelect');
      const current = sel.value;
      sel.innerHTML = '<option value="">— Mis playlists —</option>';
      Object.keys(data).sort().forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = `${name} (${data[name].length} pistas)`;
        sel.appendChild(opt);
      });
      if (current) sel.value = current;
    })
    .catch(() => {});
}

function loadSelectedPlaylist() {
  const name = document.getElementById('playlistSelect').value;
  if (!name) return;
  fetch('/api/playlists')
    .then(r => r.json())
    .then(data => {
      if (!data[name]) return;
      audioPlaylistTracks = data[name];
      audioPlaylistMode = true;
      audioPlaylistEditing = false;
      audioPlaylistSelection = new Set(audioPlaylistTracks);
      renderAudioList();
      updatePlaylistModeUI();
      updateStatus(`Playlist "${name}" cargada`);
    });
}

function deleteSelectedPlaylist() {
  const name = document.getElementById('playlistSelect').value;
  if (!name) return;
  if (!confirm(`¿Borrar playlist "${name}"?`)) return;
  fetch(`/api/playlists/${encodeURIComponent(name)}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(() => {
      if (audioPlaylistMode) exitPlaylistMode();
      loadPlaylists();
    });
}

function togglePlaylistEditMode() {
  audioPlaylistEditing = !audioPlaylistEditing;
  if (audioPlaylistEditing && audioPlaylistMode) {
    // editar la playlist activa
    audioPlaylistSelection = new Set(audioPlaylistTracks);
  } else if (audioPlaylistEditing) {
    // empezar selección nueva desde los tracks filtrados
    audioPlaylistSelection = new Set();
  }
  document.getElementById('btnPlaylistEdit').classList.toggle('on', audioPlaylistEditing);
  renderAudioList();
}

function saveCurrentAsPlaylist() {
  const tracks = audioPlaylistEditing
    ? [...audioPlaylistSelection]
    : getFilteredTracks().map(t => t.filename);

  if (!tracks.length) { updateStatus('No hay pistas para guardar'); return; }

  const name = prompt('Nombre de la playlist:', document.getElementById('playlistSelect').value || '');
  if (!name) return;

  fetch('/api/playlists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, tracks }),
  })
    .then(r => r.json())
    .then(() => {
      loadPlaylists().then?.(() => {});
      loadPlaylists();
      // Activar la playlist recién guardada
      audioPlaylistTracks = tracks;
      audioPlaylistMode = true;
      audioPlaylistEditing = false;
      document.getElementById('btnPlaylistEdit').classList.remove('on');
      document.getElementById('playlistSelect').value = name;
      renderAudioList();
      updatePlaylistModeUI();
      updateStatus(`Playlist "${name}" guardada`);
    });
}

function exitPlaylistMode() {
  audioPlaylistMode = false;
  audioPlaylistEditing = false;
  audioPlaylistTracks = [];
  audioPlaylistSelection = new Set();
  document.getElementById('btnPlaylistEdit').classList.remove('on');
  document.getElementById('playlistSelect').value = '';
  renderAudioList();
  updatePlaylistModeUI();
}

function updatePlaylistModeUI() {
  const bar = document.querySelector('.audio-playlist-bar');
  if (bar) bar.style.borderTop = audioPlaylistMode
    ? '1px solid var(--accent, #5a8a5a)'
    : '1px solid transparent';
}

function toggleTrackInPlaylistSelection(filename) {
  if (audioPlaylistSelection.has(filename)) {
    audioPlaylistSelection.delete(filename);
  } else {
    audioPlaylistSelection.add(filename);
  }
  renderAudioList();
}

// ── Tag modal ─────────────────────────────────────────────────────────────────
let _tagModalFilename = '';

function openTagModal(filename, track) {
  _tagModalFilename = filename;
  document.getElementById('audioTagFilename').textContent = filename;

  const cats = track ? track.categories : [];
  const syss = track ? track.systems : [];

  document.querySelectorAll('#audioTagCategories .tag-chip').forEach(chip => {
    chip.classList.toggle('active', cats.includes(chip.dataset.val));
  });
  document.querySelectorAll('#audioTagSystems .tag-chip').forEach(chip => {
    chip.classList.toggle('active', syss.includes(chip.dataset.val));
  });

  document.getElementById('audioTagModal').style.display = 'flex';
}

function closeTagModal() {
  document.getElementById('audioTagModal').style.display = 'none';
  _tagModalFilename = '';
}

function saveAudioTagsFromModal() {
  const categories = [...document.querySelectorAll('#audioTagCategories .tag-chip.active')].map(c => c.dataset.val);
  const systems = [...document.querySelectorAll('#audioTagSystems .tag-chip.active')].map(c => c.dataset.val);

  fetch('/api/audio/tag', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: _tagModalFilename, categories, systems }),
  })
    .then(r => r.json())
    .then(() => {
      closeTagModal();
      loadAudioList();
    })
    .catch(err => console.error("Error saving tags:", err));
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
    const result = await fetchData('/api/screen/render-markdown-text', 'POST', { text });

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

// ========== CROP PORTRAIT ==========

const cropState = {
  img: null,       // HTMLImageElement de la imagen pegada
  startX: 0, startY: 0,
  endX: 0, endY: 0,
  dragging: false,
  hasCrop: false,
  videoFile: null, // File de vídeo seleccionado (si es un vídeo en vez de una imagen)
};

// Objetivo del recorte: por defecto el monstruo mostrado en el detalle genérico.
// openCropModalFor() lo redirige a otro tipo de contenido (p.ej. jugador) sin
// tocar el resto de la lógica de pegar/recortar/guardar, que es compartida.
let cropTarget = { type: 'monster', slug: null, label: null, onSaved: null };

function openCropModal() {
  if (currentContentType !== 'monster') return;
  cropTarget = { type: 'monster', slug: currentContentSlug, label: currentContentTitle || currentContentSlug, onSaved: null };
  document.getElementById('cropMonsterName').textContent = cropTarget.label;
  resetCropState();
  document.getElementById('cropModal').style.display = 'block';
  // Auto-focus the hint so Ctrl+V works immediately
  setTimeout(() => document.getElementById('cropPasteHint').focus(), 50);
}

// Abre el mismo modal de recorte para otro tipo de contenido (p.ej. 'player').
// onSaved(portraitUrl) se llama tras guardar con éxito, en vez del refresco
// automático de showContentDetail que solo tiene sentido para monstruos.
function openCropModalFor(type, slug, label, onSaved) {
  cropTarget = { type, slug, label, onSaved: onSaved || null };
  document.getElementById('cropMonsterName').textContent = label || slug;
  resetCropState();
  document.getElementById('cropModal').style.display = 'block';
  setTimeout(() => document.getElementById('cropPasteHint').focus(), 50);
}

function closeCropModal() {
  document.getElementById('cropModal').style.display = 'none';
  resetCropState();
}

function resetCropState() {
  cropState.img = null;
  cropState.hasCrop = false;
  cropState.dragging = false;
  cropState.videoFile = null;
  document.getElementById('cropPasteHint').style.display = '';
  document.getElementById('cropWorkArea').style.display = 'none';
  document.getElementById('cropPreviewWrap').style.display = 'none';
  document.getElementById('cropRect').style.display = 'none';
  document.getElementById('cropBtnSave').disabled = true;
  const canvas = document.getElementById('cropCanvas');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.style.display = '';
  document.getElementById('cropHintText').style.display = '';
  const video = document.getElementById('cropVideoPreview');
  video.pause();
  video.removeAttribute('src');
  video.load();
  video.style.display = 'none';
}

/**
 * Carga un vídeo seleccionado/arrastrado/pegado en el modal de retrato.
 * A diferencia de las imágenes, no se puede recortar: se guarda tal cual.
 *
 * @param {File} file - Archivo de vídeo (mp4/webm/mov).
 * @returns {void}
 */
function loadVideoIntoCrop(file) {
  cropState.img = null;
  cropState.hasCrop = false;
  cropState.videoFile = file;

  const canvas = document.getElementById('cropCanvas');
  canvas.style.display = 'none';
  document.getElementById('cropRect').style.display = 'none';
  document.getElementById('cropPreviewWrap').style.display = 'none';
  document.getElementById('cropHintText').style.display = 'none';

  const video = document.getElementById('cropVideoPreview');
  video.src = URL.createObjectURL(file);
  video.style.display = 'block';

  document.getElementById('cropPasteHint').style.display = 'none';
  document.getElementById('cropWorkArea').style.display = '';
  document.getElementById('cropBtnSave').disabled = false;
}

function loadImageIntoCrop(blob) {
  const url = URL.createObjectURL(blob);
  const img = new Image();
  img.onload = () => {
    cropState.img = img;
    cropState.hasCrop = false;
    const canvas = document.getElementById('cropCanvas');
    // Limit display width to 700px, scale proportionally
    const maxW = Math.min(700, window.innerWidth - 80);
    const scale = Math.min(1, maxW / img.naturalWidth);
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    document.getElementById('cropPasteHint').style.display = 'none';
    document.getElementById('cropWorkArea').style.display = '';
    // Enable save immediately — without selection saves the full image
    document.getElementById('cropBtnSave').disabled = false;
    URL.revokeObjectURL(url);
  };
  img.onerror = () => {
    updateStatus('Error al cargar la imagen', true);
    URL.revokeObjectURL(url);
  };
  img.src = url;
}

function getCropCanvasCoords(e) {
  const canvas = document.getElementById('cropCanvas');
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
    px: clientX - rect.left,  // pixel position for the overlay div
    py: clientY - rect.top,
  };
}

function updateCropRect(x1, y1, x2, y2) {
  const rect = document.getElementById('cropRect');
  const left = Math.min(x1, x2);
  const top = Math.min(y1, y2);
  const w = Math.abs(x2 - x1);
  const h = Math.abs(y2 - y1);
  rect.style.left = left + 'px';
  rect.style.top = top + 'px';
  rect.style.width = w + 'px';
  rect.style.height = h + 'px';
  rect.style.display = (w > 2 && h > 2) ? '' : 'none';
}

function renderCropPreview() {
  const canvas = document.getElementById('cropCanvas');
  const x1 = Math.min(cropState.startX, cropState.endX);
  const y1 = Math.min(cropState.startY, cropState.endY);
  const w = Math.abs(cropState.endX - cropState.startX);
  const h = Math.abs(cropState.endY - cropState.startY);
  if (w < 4 || h < 4) return;

  // Map canvas coords back to natural image coords
  const scaleX = cropState.img.naturalWidth / canvas.width;
  const scaleY = cropState.img.naturalHeight / canvas.height;
  const sx = x1 * scaleX, sy = y1 * scaleY;
  const sw = w * scaleX, sh = h * scaleY;

  const preview = document.getElementById('cropPreview');
  const maxH = 180;
  const ratio = sw / sh;
  preview.height = maxH;
  preview.width = Math.round(maxH * ratio);
  const pctx = preview.getContext('2d');
  pctx.drawImage(cropState.img, sx, sy, sw, sh, 0, 0, preview.width, preview.height);

  document.getElementById('cropPreviewWrap').style.display = '';
  cropState.hasCrop = true;
  document.getElementById('cropBtnSave').disabled = false;
}

function getCroppedJpegBase64() {
  const canvas = document.getElementById('cropCanvas');
  const img = cropState.img;

  // If no crop selection, use the full image
  if (!cropState.hasCrop) {
    const out = document.createElement('canvas');
    out.width = img.naturalWidth;
    out.height = img.naturalHeight;
    out.getContext('2d').drawImage(img, 0, 0);
    return out.toDataURL('image/jpeg', 0.92);
  }

  const x1 = Math.min(cropState.startX, cropState.endX);
  const y1 = Math.min(cropState.startY, cropState.endY);
  const w = Math.abs(cropState.endX - cropState.startX);
  const h = Math.abs(cropState.endY - cropState.startY);

  const scaleX = img.naturalWidth / canvas.width;
  const scaleY = img.naturalHeight / canvas.height;
  const sx = x1 * scaleX, sy = y1 * scaleY;
  const sw = w * scaleX, sh = h * scaleY;

  const out = document.createElement('canvas');
  out.width = Math.round(sw);
  out.height = Math.round(sh);
  out.getContext('2d').drawImage(img, sx, sy, sw, sh, 0, 0, out.width, out.height);
  return out.toDataURL('image/jpeg', 0.92);
}

function initCropModal() {
  const hint = document.getElementById('cropPasteHint');
  const container = document.getElementById('cropContainer');
  const btnSave = document.getElementById('cropBtnSave');
  const btnReset = document.getElementById('cropBtnReset');

  // Click hint to focus (Ctrl+V / Cmd+V)
  hint.addEventListener('click', () => hint.focus());

  // Global paste listener (active when modal is open)
  document.addEventListener('paste', (e) => {
    if (document.getElementById('cropModal').style.display === 'none') return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith('video/')) {
        loadVideoIntoCrop(item.getAsFile());
        e.preventDefault();
        break;
      }
      if (item.type.startsWith('image/')) {
        loadImageIntoCrop(item.getAsFile());
        e.preventDefault();
        break;
      }
    }
  });

  // Drag & drop onto the hint area
  hint.addEventListener('dragover', (e) => {
    e.preventDefault();
    hint.style.borderColor = '#c9a84c';
  });
  hint.addEventListener('dragleave', () => {
    hint.style.borderColor = '';
  });
  hint.addEventListener('drop', (e) => {
    e.preventDefault();
    hint.style.borderColor = '';
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (file.type.startsWith('video/')) loadVideoIntoCrop(file);
    else if (file.type.startsWith('image/')) loadImageIntoCrop(file);
  });

  // File input fallback
  document.getElementById('cropFileInput').addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type.startsWith('video/')) loadVideoIntoCrop(file);
      else loadImageIntoCrop(file);
    }
    e.target.value = '';
  });

  // Crop drag on canvas container
  container.addEventListener('mousedown', (e) => {
    if (!cropState.img) return;
    const coords = getCropCanvasCoords(e);
    cropState.startX = coords.x; cropState.startY = coords.y;
    cropState.endX = coords.x; cropState.endY = coords.y;
    cropState.dragging = true;
    cropState.hasCrop = false;
    document.getElementById('cropBtnSave').disabled = true;
    document.getElementById('cropPreviewWrap').style.display = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!cropState.dragging) return;
    const canvas = document.getElementById('cropCanvas');
    const rect = canvas.getBoundingClientRect();
    // Use pixel coords for the overlay div
    const px = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const py = Math.max(0, Math.min(e.clientY - rect.top, rect.height));
    // Canvas coords for actual crop math
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    cropState.endX = px * scaleX;
    cropState.endY = py * scaleY;

    const sx = Math.min(cropState.startX / scaleX, px);
    const sy = Math.min(cropState.startY / scaleY, py);
    const ex = Math.max(cropState.startX / scaleX, px);
    const ey = Math.max(cropState.startY / scaleY, py);
    updateCropRect(sx, sy, ex, ey);
  });

  document.addEventListener('mouseup', () => {
    if (!cropState.dragging) return;
    cropState.dragging = false;
    renderCropPreview();
  });

  // Reset / cambiar imagen
  btnReset.addEventListener('click', resetCropState);

  // Close button
  document.getElementById('cropModalClose').addEventListener('click', closeCropModal);
  document.getElementById('cropModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('cropModal')) closeCropModal();
  });

  // Save
  btnSave.addEventListener('click', async () => {
    if (!cropState.img && !cropState.videoFile) return;
    btnSave.disabled = true;
    btnSave.textContent = 'Guardando…';
    try {
      let res;
      const endpoint = cropTarget.type === 'player'
        ? `/api/players/${cropTarget.slug}/portrait`
        : `/api/monsters/${cropTarget.slug}/portrait`;
      if (cropState.videoFile) {
        const fd = new FormData();
        fd.append('video', cropState.videoFile);
        res = await fetch(endpoint, {
          method: 'POST',
          body: fd,
        });
      } else {
        const dataUrl = getCroppedJpegBase64();
        res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: dataUrl }),
        });
      }
      const json = await res.json();
      if (json.ok) {
        closeCropModal();
        if (cropTarget.type === 'player' && cropTarget.onSaved) {
          cropTarget.onSaved(json.portrait_path);
        } else {
          // Reload the monster detail to show the new portrait
          showContentDetail('monster', currentContentSlug);
        }
        updateStatus('Imagen guardada correctamente');
      } else {
        updateStatus('Error al guardar la imagen: ' + (json.error || ''), true);
      }
    } catch (err) {
      updateStatus('Error al guardar la imagen', true);
    } finally {
      btnSave.disabled = false;
      btnSave.textContent = 'Guardar';
    }
  });
}

document.addEventListener('DOMContentLoaded', initCropModal);
