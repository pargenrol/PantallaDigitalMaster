let lastCommandTimestamp = "";
let playerCanvas = null;

// YouTube
let youtubePlayer = null;
let youtubeApiReady = false;

// Estado media
const mediaImage = () => document.getElementById('media-image');
const mediaVideo = () => document.getElementById('media-video');
const youtubeWrapper = () => document.getElementById('youtube-wrapper');

document.addEventListener("DOMContentLoaded", () => {
  initCanvas();
  loadYouTubeApi();

  // Polling de comandos
  setInterval(checkCommands, 1000);
});

window.addEventListener("resize", () => {
  if (!playerCanvas) return;
  playerCanvas.setWidth(window.innerWidth);
  playerCanvas.setHeight(window.innerHeight);
  playerCanvas.renderAll();
});

// ==============================
// CANVAS (WHITEBOARD PLAYER)
// ==============================
function initCanvas() {
  // Fabric necesita dimensiones reales
  const canvasEl = document.getElementById('playerCanvas');
  canvasEl.width = window.innerWidth;
  canvasEl.height = window.innerHeight;

  playerCanvas = new fabric.Canvas('playerCanvas', {
    width: window.innerWidth,
    height: window.innerHeight,
    selection: false,
    defaultCursor: 'default'
  });

  // Importante: el jugador no edita
  playerCanvas.selection = false;
  playerCanvas.skipTargetFind = true;
  playerCanvas.forEachObject(obj => obj.selectable = false);
}

// ==============================
// YOUTUBE IFRAME API
// ==============================
function loadYouTubeApi() {
  const tag = document.createElement('script');
  tag.src = "https://www.youtube.com/iframe_api";
  const firstScriptTag = document.getElementsByTagName('script')[0];
  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
}

// La API llama a esto globalmente
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
      onReady: (e) => {
        try { e.target.playVideo(); } catch (_) {}
      }
    }
  });
};

// ==============================
// POLLING COMANDOS
// ==============================
async function checkCommands() {
  try {
    const response = await fetch('/api/screen/command', { cache: 'no-store' });
    const command = await response.json();

    // Si no hay timestamp, igual procesamos tipo "initiative" por defecto
    if (command.timestamp && command.timestamp === lastCommandTimestamp) {
      // Mantener whiteboard actualizada si está activa
      if (command.type === 'whiteboard') {
        await updateWhiteboard();
      }
      return;
    }

    if (command.timestamp) lastCommandTimestamp = command.timestamp;

    await executeCommand(command);

    // Si el comando es whiteboard, sincroniza estado también
    if (command.type === 'whiteboard') {
      await updateWhiteboard();
    }
  } catch (e) {
    console.error("checkCommands error:", e);
  }
}

async function updateWhiteboard() {
  try {
    const r = await fetch('/api/whiteboard/load', { cache: 'no-store' });
    const data = await r.json();
    if (data.state && playerCanvas) {
      playerCanvas.loadFromJSON(data.state, () => {
        // Hacer no seleccionables
        playerCanvas.forEachObject(obj => { obj.selectable = false; obj.evented = false; });
        playerCanvas.renderAll();
      });
    }
  } catch (e) {
    console.error("updateWhiteboard error:", e);
  }
}

// ==============================
// EJECUCIÓN DE COMANDOS
// ==============================
async function executeCommand(cmd) {
  hideAll();

  // Compatibilidad: si el backend manda {type:'clear'} sin data/timestamp
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
      // clear screen por defecto
      // ya está todo oculto
      break;
  }
}

// ==============================
// CAPAS
// ==============================
function showInitiativeLayer() {
  document.getElementById('initiative-container').style.display = 'block';
}
function showMediaLayer() {
  document.getElementById('media-container').style.display = 'flex';
}
function showWhiteboardLayer() {
  document.getElementById('whiteboard-container').style.display = 'block';
}
function showInfoCardLayer() {
  document.getElementById('info-card-container').style.display = 'flex';
}

function hideAll() {
  // Ocultar capas
  document.querySelectorAll('#initiative-container, #media-container, #whiteboard-container, #info-card-container')
    .forEach(div => div.style.display = 'none');

  // Reset media
  const v = mediaVideo();
  if (v) {
    v.pause();
    v.removeAttribute('src');
    v.load();
    v.style.display = 'none';
  }

  const img = mediaImage();
  if (img) {
    img.removeAttribute('src');
    img.style.display = 'none';
  }

  const yt = youtubeWrapper();
  if (yt) yt.style.display = 'none';

  // Pausar YouTube si existe
  if (youtubePlayer && youtubePlayer.pauseVideo) {
    try { youtubePlayer.pauseVideo(); } catch (_) {}
  }

  // Fondo base
  document.body.style.backgroundColor = '#000';
}

function blackout() {
  hideAll();
  document.body.style.backgroundColor = 'black';
}

// ==============================
// MEDIA: Imagen
// ==============================
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
// MEDIA: Vídeo
// ==============================
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

  // Si ya está puesto, solo play
  if (v.dataset.currentSrc === fullUrl) {
    if (v.paused) {
      try { await v.play(); } catch (_) {}
    }
    return;
  }

  v.pause();
  v.src = fullUrl;
  v.dataset.currentSrc = fullUrl;
  v.load();

  // Intentar autoplay con sonido (si el navegador lo permite)
  v.muted = false;
  v.volume = 1.0;

  try {
    await v.play();
  } catch (err) {
    // Safari/Chrome: si bloquea autoplay con audio, reintenta muted
    v.muted = true;
    try { await v.play(); } catch (_) {}
  }
}

// ==============================
// MEDIA: YouTube
// ==============================
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

  // Esperar API lista si llega antes
  if (!youtubeApiReady) {
    // Espera corta por polling
    await waitForYoutubeReady(2500);
  }

  if (youtubePlayer && youtubePlayer.loadVideoById) {
    youtubePlayer.loadVideoById(videoId);

    // Muted configurable por backend
    const muted = (data && typeof data.muted === 'boolean') ? data.muted : true;
    try {
      if (muted && youtubePlayer.mute) youtubePlayer.mute();
      if (!muted && youtubePlayer.unMute) youtubePlayer.unMute();
    } catch (_) {}
  }
}

function toggleYouTubePlayer() {
  if (!youtubePlayer || !youtubePlayer.getPlayerState) return;
  try {
    const s = youtubePlayer.getPlayerState();
    if (s === 1) youtubePlayer.pauseVideo();
    else youtubePlayer.playVideo();
  } catch (_) {}
}

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
function showInfoCard(data) {
  const container = document.getElementById('infoCardContent');
  if (!container) return;

  const title = data?.title || "Información";
  const html = data?.html || "";

  container.innerHTML = `<h1>${escapeHtml(title)}</h1>` + html;
}

// ==============================
// INICIATIVA
// ==============================
async function loadInitiative() {
  try {
    const r = await fetch('/api/characters', { cache: 'no-store' });
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

      const card = document.createElement('div');
      card.className = `turn-card ${isCurrent ? 'active' : ''}`;

      const hpPercent = char.max_hp ? (char.hp / char.max_hp) * 100 : 100;
      const hpHtml = char.max_hp
        ? `<div class="hp-bar"><div class="hp-fill" style="width:${Math.max(0, hpPercent)}%;"></div></div>`
        : '';

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

      if (isCurrent) {
        foundActive = true;
        activeName.textContent = char.name || '';

        // Retrato
        if (char.portrait_path) {
          const path = String(char.portrait_path);
          const lower = path.toLowerCase();
          const isVideo = lower.endsWith('.mp4') || lower.endsWith('.webm');

          if (isVideo) {
            portraitImg.style.display = 'none';
            portraitVid.style.display = 'block';

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
            portraitVid.style.display = 'none';
            portraitVid.pause();
            portraitVid.dataset.currentPath = "";

            portraitImg.style.display = 'block';
            portraitImg.src = absoluteUrl(path);
          }
        } else {
          hidePortrait(portraitImg, portraitVid);
        }

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
// UTIL
// ==============================
function absoluteUrl(url) {
  if (!url) return "";
  try {
    return new URL(url, window.location.origin).href;
  } catch (_) {
    return url;
  }
}

function escapeHtml(str) {
  return String(str ?? '')
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(str) {
  return escapeHtml(str).replaceAll('"', "&quot;");
}