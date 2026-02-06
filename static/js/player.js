/**
 * Player Screen Controller (Initiative / Media / Whiteboard / Info Card)
 * ---------------------------------------------------------------------
 * This script drives a "player display" page for a TTRPG/DM tool:
 * - Polls the backend for screen commands (/api/screen/command).
 * - Switches between UI layers (initiative, media, whiteboard, info cards).
 * - Renders a read-only Fabric.js canvas for the whiteboard state.
 * - Plays images/videos and YouTube content (YouTube IFrame API).
 *
 * External dependencies:
 * - fabric.js (global `fabric`)
 * - YouTube IFrame API (global `YT`)
 *
 * Backend endpoints (expected):
 * - GET /api/screen/command         -> { type, data, timestamp }
 * - GET /api/whiteboard/load        -> { state: <fabric-json> }
 * - GET /api/characters             -> { round_number, characters: [...] }
 */

// ==============================
// GLOBAL STATE
// ==============================

/**
 * Tracks the last processed command timestamp.
 * Used to prevent re-executing the same command repeatedly.
 * @type {string}
 */
let lastCommandTimestamp = "";

/**
 * Fabric.js canvas instance used for the whiteboard view.
 * The player canvas is configured as read-only.
 * @type {fabric.Canvas|null}
 */
let playerCanvas = null;

// ==============================
// YOUTUBE STATE
// ==============================

/**
 * YouTube IFrame API player instance.
 * Created once the API is ready.
 * @type {YT.Player|null}
 */
let youtubePlayer = null;

/**
 * Whether the YouTube IFrame API has been loaded and initialized.
 * @type {boolean}
 */
let youtubeApiReady = false;

// ==============================
// DOM HELPERS (MEDIA NODES)
// ==============================

/**
 * Returns the <img> element used to show images in the media layer.
 * @returns {HTMLImageElement|null}
 */
const mediaImage = () => document.getElementById('media-image');

/**
 * Returns the <video> element used to show videos in the media layer.
 * @returns {HTMLVideoElement|null}
 */
const mediaVideo = () => document.getElementById('media-video');

/**
 * Returns the wrapper element that contains the YouTube iframe container.
 * @returns {HTMLElement|null}
 */
const youtubeWrapper = () => document.getElementById('youtube-wrapper');

// ==============================
// APP BOOTSTRAP
// ==============================

document.addEventListener("DOMContentLoaded", () => {
  // Initializes the read-only Fabric canvas used for whiteboard playback.
  initCanvas();

  // Injects the YouTube IFrame API script so we can create YT.Player.
  loadYouTubeApi();

  // Polls the backend every second to fetch and execute display commands.
  setInterval(checkCommands, 1000);
});

window.addEventListener("resize", () => {
  // Keeps the Fabric canvas full-screen and responsive.
  if (!playerCanvas) return;
  playerCanvas.setWidth(window.innerWidth);
  playerCanvas.setHeight(window.innerHeight);
  playerCanvas.renderAll();
});

// ==============================
// CANVAS (WHITEBOARD PLAYER)
// ==============================

/**
 * Initializes the Fabric.js canvas for the player screen.
 *
 * The canvas is set to:
 * - Full-window size
 * - No selection / no target finding (read-only experience)
 * - Objects marked as non-selectable
 *
 * Requirements:
 * - A <canvas id="playerCanvas"> element exists in the DOM.
 * - `fabric` is available globally (fabric.js loaded).
 *
 * @returns {void}
 */
function initCanvas() {
  // Fabric requires explicit real dimensions on the <canvas> element.
  const canvasEl = document.getElementById('playerCanvas');
  canvasEl.width = window.innerWidth;
  canvasEl.height = window.innerHeight;

  playerCanvas = new fabric.Canvas('playerCanvas', {
    width: window.innerWidth,
    height: window.innerHeight,
    selection: false,
    defaultCursor: 'default'
  });

  // Player should never edit the whiteboard.
  playerCanvas.selection = false;
  playerCanvas.skipTargetFind = true;
  playerCanvas.forEachObject(obj => (obj.selectable = false));
}

// ==============================
// YOUTUBE IFRAME API
// ==============================

/**
 * Dynamically injects the YouTube IFrame API script into the page.
 * Once loaded, YouTube will call `window.onYouTubeIframeAPIReady()`.
 *
 * @returns {void}
 */
function loadYouTubeApi() {
  const tag = document.createElement('script');
  tag.src = "https://www.youtube.com/iframe_api";
  const firstScriptTag = document.getElementsByTagName('script')[0];
  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
}

/**
 * Global callback invoked by the YouTube IFrame API when it finishes loading.
 * Creates a YT.Player instance in the element with id="youtube-player".
 *
 * Notes:
 * - `YT` is provided by the IFrame API.
 * - Player is configured for autoplay and minimal chrome.
 *
 * @returns {void}
 */
window.onYouTubeIframeAPIReady = function () {
  youtubeApiReady = true;

  youtubePlayer = new YT.Player('youtube-player', {
    height: '100%',
    width: '100%',
    videoId: '',
    playerVars: {
      autoplay: 1,
      controls: 0,
      rel: 0,
      modestbranding: 1,
      playsinline: 1
    },
    events: {
      /**
       * Attempt playback as soon as the player is ready.
       * Some browsers may block autoplay; errors are swallowed.
       * @param {{ target: YT.Player }} e
       */
      onReady: (e) => {
        try { e.target.playVideo(); } catch (_) {}
      }
    }
  });
};

// ==============================
// COMMAND POLLING
// ==============================

/**
 * Polls the backend for the latest screen command and executes it.
 *
 * Endpoint contract (expected):
 * GET /api/screen/command -> JSON:
 * {
 *   "type": string,
 *   "timestamp": string,
 *   "data": object
 * }
 *
 * Behavior:
 * - If the timestamp matches the last executed timestamp, it skips re-executing.
 * - Special case: if the command is "whiteboard", it will still refresh the
 *   whiteboard state periodically to keep it in sync.
 *
 * @returns {Promise<void>}
 */
async function checkCommands() {
  try {
    const response = await fetch('/api/screen/command', { cache: 'no-store' });
    const command = await response.json();

    // If timestamp matches, skip executing the same command.
    // But if we're in whiteboard mode, keep syncing board state.
    if (command.timestamp && command.timestamp === lastCommandTimestamp) {
      if (command.type === 'whiteboard') {
        await updateWhiteboard();
      }
      return;
    }

    if (command.timestamp) lastCommandTimestamp = command.timestamp;

    await executeCommand(command);

    // If command is whiteboard, also sync the state.
    if (command.type === 'whiteboard') {
      await updateWhiteboard();
    }
  } catch (e) {
    console.error("checkCommands error:", e);
  }
}

/**
 * Fetches the latest whiteboard state from the backend and loads it into Fabric.
 *
 * Endpoint contract (expected):
 * GET /api/whiteboard/load -> JSON:
 * {
 *   "state": object|string  // Fabric JSON (stringified or object depending on backend)
 * }
 *
 * Behavior:
 * - Calls `playerCanvas.loadFromJSON` to render the board.
 * - Ensures all objects are non-interactive (selectable=false, evented=false).
 *
 * @returns {Promise<void>}
 */
async function updateWhiteboard() {
  try {
    const r = await fetch('/api/whiteboard/load', { cache: 'no-store' });
    const data = await r.json();
    if (data.state && playerCanvas) {
      playerCanvas.loadFromJSON(data.state, () => {
        playerCanvas.forEachObject(obj => {
          obj.selectable = false;
          obj.evented = false;
        });
        playerCanvas.renderAll();
      });
    }
  } catch (e) {
    console.error("updateWhiteboard error:", e);
  }
}

// ==============================
// COMMAND EXECUTION
// ==============================

/**
 * Screen command object returned by the backend.
 *
 * @typedef {Object} ScreenCommand
 * @property {string} [type] - Command type (initiative, image, video, youtube, youtube_control, whiteboard, info_card, blackout, clear).
 * @property {string} [timestamp] - Monotonic or unique timestamp used for deduplication.
 * @property {Object} [data] - Payload for the command (shape depends on type).
 */

/**
 * Executes a screen command by:
 * - Hiding all layers
 * - Switching to the appropriate layer
 * - Loading the relevant content (initiative list, media, whiteboard, etc.)
 *
 * Supported command types:
 * - initiative: shows initiative layer and loads characters
 * - image: shows media layer and displays an image URL
 * - video: shows media layer and plays a video URL
 * - youtube: shows media layer and plays a YouTube video by ID
 * - youtube_control: toggles play/pause for the current YouTube video
 * - whiteboard: shows whiteboard layer (state sync handled elsewhere)
 * - info_card: shows info card layer and renders title + html
 * - blackout: clears everything and forces a black screen
 * - clear (default): hides everything
 *
 * @param {ScreenCommand} cmd - Command returned by the backend.
 * @returns {Promise<void>}
 */
async function executeCommand(cmd) {
  hideAll();

  // Compatibility: backend might send {type:'clear'} without data/timestamp.
  const type = cmd?.type || 'initiative';

  switch (type) {
    case 'initiative':
      showInitiativeLayer();
      await loadInitiative();
      break;

    case 'image':
      showMediaLayer();
      showImage(cmd?.data?.url || '');
      break;

    case 'video':
      showMediaLayer();
      await showVideo(cmd?.data?.url || '');
      break;

    case 'youtube':
      showMediaLayer();
      await showYouTube(cmd?.data?.video_id || '', cmd?.data);
      break;

    case 'youtube_control':
      showMediaLayer();
      toggleYouTubePlayer();
      break;

    case 'whiteboard':
      showWhiteboardLayer();
      break;

    case 'info_card':
      showInfoCardLayer();
      showInfoCard(cmd?.data);
      break;

    case 'blackout':
      blackout();
      break;

    case 'clear':
    default:
      // Default is clear screen: everything already hidden by hideAll().
      break;
  }
}

// ==============================
// LAYERS (VISIBILITY CONTROL)
// ==============================

/**
 * Shows the initiative layer container.
 * @returns {void}
 */
function showInitiativeLayer() {
  document.getElementById('initiative-container').style.display = 'block';
}

/**
 * Shows the media layer container.
 * @returns {void}
 */
function showMediaLayer() {
  document.getElementById('media-container').style.display = 'flex';
}

/**
 * Shows the whiteboard layer container.
 * @returns {void}
 */
function showWhiteboardLayer() {
  document.getElementById('whiteboard-container').style.display = 'block';
}

/**
 * Shows the info card layer container.
 * @returns {void}
 */
function showInfoCardLayer() {
  document.getElementById('info-card-container').style.display = 'flex';
}

/**
 * Hides all layer containers and resets media playback state.
 *
 * This is the "base reset" invoked before executing most commands.
 * It ensures:
 * - All layers are hidden
 * - HTML5 video is paused, src cleared, and hidden
 * - Image src cleared and hidden
 * - YouTube wrapper hidden and YouTube paused (if available)
 * - Body background set to black
 *
 * @returns {void}
 */
function hideAll() {
  // Hide layers
  document
    .querySelectorAll('#initiative-container, #media-container, #whiteboard-container, #info-card-container')
    .forEach(div => (div.style.display = 'none'));

  // Reset HTML5 video
  const v = mediaVideo();
  if (v) {
    v.pause();
    v.removeAttribute('src');
    v.load();
    v.style.display = 'none';
  }

  // Reset image
  const img = mediaImage();
  if (img) {
    img.removeAttribute('src');
    img.style.display = 'none';
  }

  // Hide YouTube wrapper
  const yt = youtubeWrapper();
  if (yt) yt.style.display = 'none';

  // Pause YouTube player if it exists
  if (youtubePlayer && youtubePlayer.pauseVideo) {
    try { youtubePlayer.pauseVideo(); } catch (_) {}
  }

  // Base background
  document.body.style.backgroundColor = '#000';
}

/**
 * Forces a full blackout:
 * - Hides all layers and resets media
 * - Sets body background to pure black
 *
 * @returns {void}
 */
function blackout() {
  hideAll();
  document.body.style.backgroundColor = 'black';
}

// ==============================
// MEDIA: IMAGE
// ==============================

/**
 * Displays an image in the media layer.
 *
 * Implementation details:
 * - Hides video and YouTube elements
 * - Sets the image src to an absolute URL
 *
 * @param {string} url - Image URL (absolute or relative).
 * @returns {void}
 */
function showImage(url) {
  const img = mediaImage();
  const v = mediaVideo();
  const yt = youtubeWrapper();

  if (v) v.style.display = 'none';
  if (yt) yt.style.display = 'none';

  if (img) {
    img.style.display = 'block';
    img.src = absoluteUrl(url);
  }
}

// ==============================
// MEDIA: VIDEO (HTML5)
// ==============================

/**
 * Displays and plays a video in the media layer using an HTML5 <video>.
 *
 * Behavior:
 * - Hides image and YouTube
 * - Converts URL to absolute (so relative paths work reliably)
 * - If the same video is already set, it only resumes playback
 * - Attempts autoplay with audio, then retries muted if blocked
 *
 * @param {string} url - Video URL (absolute or relative).
 * @returns {Promise<void>}
 */
async function showVideo(url) {
  const img = mediaImage();
  const v = mediaVideo();
  const yt = youtubeWrapper();

  if (img) img.style.display = 'none';
  if (yt) yt.style.display = 'none';

  if (!v) return;

  v.style.display = 'block';

  const fullUrl = absoluteUrl(url);
  if (!fullUrl) return;

  // If already loaded, just play
  if (v.dataset.currentSrc === fullUrl) {
    if (v.paused) {
      try { await v.play(); } catch (_) {}
    }
    return;
  }

  // Load and play new source
  v.pause();
  v.src = fullUrl;
  v.dataset.currentSrc = fullUrl;
  v.load();

  // Attempt autoplay with sound (may be blocked by browser policy)
  v.muted = false;
  v.volume = 1.0;

  try {
    await v.play();
  } catch (err) {
    // If blocked, retry muted autoplay
    v.muted = true;
    try { await v.play(); } catch (_) {}
  }
}

// ==============================
// MEDIA: YOUTUBE
// ==============================

/**
 * YouTube payload (command.data) expected for type "youtube".
 *
 * @typedef {Object} YouTubeCommandData
 * @property {string} [video_id] - The YouTube video ID to play.
 * @property {boolean} [muted] - Whether playback should be muted (defaults to true).
 */

/**
 * Displays and plays a YouTube video in the media layer.
 *
 * Behavior:
 * - Hides image and HTML5 video
 * - Shows YouTube wrapper
 * - Waits briefly for YouTube API readiness if needed
 * - Loads the requested video by ID into the existing player
 * - Applies muted/unmuted based on backend data (defaults to muted)
 *
 * @param {string} videoId - YouTube video ID (e.g., "dQw4w9WgXcQ").
 * @param {YouTubeCommandData} [data={}] - Optional settings from backend (e.g., muted).
 * @returns {Promise<void>}
 */
async function showYouTube(videoId, data = {}) {
  const img = mediaImage();
  const v = mediaVideo();
  const yt = youtubeWrapper();

  if (img) img.style.display = 'none';
  if (v) {
    v.style.display = 'none';
    v.pause();
  }

  if (yt) yt.style.display = 'block';

  if (!videoId) return;

  // If command arrives before API is ready, wait a bit.
  if (!youtubeApiReady) {
    await waitForYoutubeReady(2500);
  }

  if (youtubePlayer && youtubePlayer.loadVideoById) {
    youtubePlayer.loadVideoById(videoId);

    // Backend-configurable mute setting (defaults to true)
    const muted = (data && typeof data.muted === 'boolean') ? data.muted : true;
    try {
      if (muted && youtubePlayer.mute) youtubePlayer.mute();
      if (!muted && youtubePlayer.unMute) youtubePlayer.unMute();
    } catch (_) {}
  }
}

/**
 * Toggles YouTube playback between play and pause.
 *
 * Uses YT.PlayerState semantics:
 * - 1 means "playing"
 * Any other state triggers play attempt.
 *
 * @returns {void}
 */
function toggleYouTubePlayer() {
  if (!youtubePlayer || !youtubePlayer.getPlayerState) return;
  try {
    const s = youtubePlayer.getPlayerState();
    if (s === 1) youtubePlayer.pauseVideo();
    else youtubePlayer.playVideo();
  } catch (_) {}
}

/**
 * Waits until the YouTube API is ready and a player instance exists, or times out.
 *
 * This is used when a "youtube" command arrives before the iframe API callback ran.
 *
 * @param {number} [timeoutMs=2000] - Maximum time to wait in milliseconds.
 * @returns {Promise<boolean>} Resolves to true if ready, false if timed out.
 */
function waitForYoutubeReady(timeoutMs = 2000) {
  const start = Date.now();
  return new Promise((resolve) => {
    const t = setInterval(() => {
      if (youtubeApiReady && youtubePlayer) {
        clearInterval(t);
        resolve(true);
        return;
      }
      if (Date.now() - start >= timeoutMs) {
        clearInterval(t);
        resolve(false);
      }
    }, 50);
  });
}

// ==============================
// INFO CARD
// ==============================

/**
 * Info card payload expected for type "info_card".
 *
 * @typedef {Object} InfoCardData
 * @property {string} [title] - Title to show in the info card header.
 * @property {string} [html] - Additional HTML content to inject after the title.
 */

/**
 * Renders an info card into the "infoCardContent" container.
 *
 * Security note:
 * - The title is escaped via escapeHtml().
 * - The `html` field is inserted as raw HTML; it should be sanitized server-side
 *   if it can contain untrusted content.
 *
 * @param {InfoCardData|undefined|null} data - Info card data from backend.
 * @returns {void}
 */
function showInfoCard(data) {
  const container = document.getElementById('infoCardContent');
  if (!container) return;

  const title = data?.title || "Información";
  const html = data?.html || "";

  container.innerHTML = `<h1>${escapeHtml(title)}</h1>` + html;
}

// ==============================
// INITIATIVE
// ==============================

/**
 * Character data returned by /api/characters.
 *
 * @typedef {Object} Character
 * @property {string} [name] - Character display name.
 * @property {number} [initiative] - Initiative value used for ordering/label.
 * @property {number} [hp] - Current hit points.
 * @property {number} [max_hp] - Max hit points; if missing, HP bar is omitted.
 * @property {boolean} [isCurrent] - Whether this character is the active turn.
 * @property {string} [portrait_path] - Image/video path for portrait (relative or absolute).
 */

/**
 * Initiative response payload.
 *
 * @typedef {Object} InitiativeResponse
 * @property {number} [round_number] - Current round number.
 * @property {Character[]} [characters] - List of characters in initiative order.
 */

/**
 * Fetches initiative/character state from the backend and renders it to the player screen.
 *
 * Endpoint contract:
 * GET /api/characters -> InitiativeResponse
 *
 * UI responsibilities:
 * - Updates round number (#roundDisplay)
 * - Builds initiative list cards (#initiativeListDisplay)
 * - Highlights active character (isCurrent)
 * - Displays active portrait (image or looped muted video)
 * - Scrolls the active card into view
 *
 * @returns {Promise<void>}
 */
async function loadInitiative() {
  try {
    const r = await fetch('/api/characters', { cache: 'no-store' });
    /** @type {InitiativeResponse} */
    const data = await r.json();

    const list = document.getElementById('initiativeListDisplay');

    if (data.round_number != null) {
      document.getElementById('roundDisplay').textContent = data.round_number;
    }

    list.innerHTML = '';

    const portraitImg = document.getElementById('active-portrait-large');
    const portraitVid = document.getElementById('active-portrait-video');
    const activeName = document.getElementById('active-name-large');

    if (!data.characters || data.characters.length === 0) {
      activeName.textContent = "Esperando combate.";
      hidePortrait(portraitImg, portraitVid);
      return;
    }

    let foundActive = false;

    data.characters.forEach(char => {
      const isCurrent = !!char.isCurrent;

      // Build a card per character turn
      const card = document.createElement('div');
      card.className = `turn-card ${isCurrent ? 'active' : ''}`;

      // HP bar (only if max_hp exists)
      const hpPercent = char.max_hp ? (char.hp / char.max_hp) * 100 : 100;
      const hpHtml = char.max_hp
        ? `<div class="hp-bar"><div class="hp-fill" style="width:${Math.max(0, hpPercent)}%;"></div></div>`
        : '';

      // Mini avatar: either image thumbnail or a video indicator
      let miniAvatar = '';
      if (char.portrait_path) {
        const p = String(char.portrait_path).toLowerCase();
        const isVideo = p.endsWith('.mp4') || p.endsWith('.webm');
        if (isVideo) {
          miniAvatar = `<div class="mini-avatar mini-avatar-video">🎬</div>`;
        } else {
          miniAvatar = `<img class="mini-avatar" src="${escapeAttr(char.portrait_path)}" alt="">`;
        }
      }

      card.innerHTML = `
        <div class="char-info-group">
          <div class="ini-badge">${char.initiative}</div>
          ${miniAvatar}
          <h2>${escapeHtml(char.name || '')}</h2>
        </div>
        ${hpHtml}
      `;

      list.appendChild(card);

      // Active turn details (large portrait + name)
      if (isCurrent) {
        foundActive = true;
        activeName.textContent = char.name || '';

        if (char.portrait_path) {
          const path = String(char.portrait_path);
          const lower = path.toLowerCase();
          const isVideo = lower.endsWith('.mp4') || lower.endsWith('.webm');

          if (isVideo) {
            portraitImg.style.display = 'none';
            portraitVid.style.display = 'block';

            // Only reload if it changed
            if (portraitVid.dataset.currentPath !== path) {
              portraitVid.src = absoluteUrl(path);
              portraitVid.dataset.currentPath = path;
              portraitVid.load();

              portraitVid.muted = true;
              portraitVid.loop = true;

              const pp = portraitVid.play();
              if (pp !== undefined) {
                pp.catch(() => {});
              }
            }
          } else {
            // Switch to image portrait
            portraitVid.style.display = 'none';
            portraitVid.pause();
            portraitVid.dataset.currentPath = "";

            portraitImg.style.display = 'block';
            portraitImg.src = absoluteUrl(path);
          }
        } else {
          hidePortrait(portraitImg, portraitVid);
        }

        // Ensure active card is visible
        setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
      }
    });

    if (!foundActive) {
      activeName.textContent = "--";
      hidePortrait(portraitImg, portraitVid);
    }
  } catch (e) {
    console.error("loadInitiative error:", e);
  }
}

/**
 * Hides and resets the active portrait UI (image + video elements).
 *
 * @param {HTMLImageElement|null} img - Large portrait image element.
 * @param {HTMLVideoElement|null} vid - Large portrait video element.
 * @returns {void}
 */
function hidePortrait(img, vid) {
  if (img) img.style.display = 'none';
  if (vid) {
    vid.style.display = 'none';
    vid.pause();
    vid.removeAttribute('src');
    vid.load();
    vid.dataset.currentPath = "";
  }
}

// ==============================
// UTILITIES
// ==============================

/**
 * Converts a relative URL into an absolute URL using the current origin.
 *
 * Why:
 * - Allows backend to send relative paths like "/static/media/foo.png"
 * - Ensures media elements can resolve consistently regardless of current route
 *
 * @param {string} url - Input URL (relative or absolute).
 * @returns {string} Absolute URL string, or empty string if input is falsy.
 */
function absoluteUrl(url) {
  if (!url) return "";
  try {
    return new URL(url, window.location.origin).href;
  } catch (_) {
    // If URL construction fails, return raw input as fallback.
    return url;
  }
}

/**
 * Escapes a string for safe insertion into HTML text context.
 *
 * Use cases:
 * - Prevents HTML injection when rendering user/backend-provided strings.
 *
 * @param {unknown} str - Any value; will be coerced to string (null/undefined become '').
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

/**
 * Escapes a string for safe insertion into an HTML attribute.
 *
 * Note:
 * - This reuses escapeHtml() and ensures quotes are escaped.
 * - Still assumes you're using it in a quoted attribute context.
 *
 * @param {unknown} str - Any value; will be coerced to string.
 * @returns {string} Escaped attribute-safe string.
 */
function escapeAttr(str) {
  return escapeHtml(str).replaceAll('"', "&quot;");
}
