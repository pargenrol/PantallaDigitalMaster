// master.js - CON VISOR DE ARCHIVOS MARKDOWN

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

// ========== EXPORTAR FUNCIONES ==========
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
// Añade esto junto a las otras exportaciones (aprox. línea 50)
window.playMasterAudio = playMasterAudio;
window.pauseMasterAudio = pauseMasterAudio;
window.stopMasterAudio = stopMasterAudio;
window.updateMasterVolume = updateMasterVolume;
window.openAudioPicker = openAudioPicker; // Para subir audios
// NUEVAS EXPORTACIONES
window.toggleCenterView = toggleCenterView;
window.loadLocalMarkdown = loadLocalMarkdown;
window.projectCustomMarkdown = projectCustomMarkdown;

// ========== INICIALIZACIÓN ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log("🎮 RPG Master Control iniciando...");
    try { loadGrimoireDataAndRender(); } catch (e) { console.error("Error cargando grimorio:", e); }
    loadGameState(); 
    setupEventListeners();
    if (typeof fabric !== 'undefined') { initWhiteboard(); }
    setInterval(loadGameState, 3000); 
});

function setupEventListeners() {
    document.getElementById('addCharacterBtn')?.addEventListener('click', () => addCharacter());
    document.getElementById('selectImageBtn')?.addEventListener('click', () => openFilePicker('image'));
    document.getElementById('selectVideoBtn')?.addEventListener('click', () => openFilePicker('video'));
    document.getElementById('blackoutBtn')?.addEventListener('click', blackoutScreen);
    
    const ytInput = document.getElementById('youtubeUrl');
    if (ytInput) ytInput.addEventListener('input', updateYoutubePreview);

    document.getElementById('drawingColor')?.addEventListener('change', updateBrushProperties);
    document.getElementById('drawingLineWidth')?.addEventListener('change', updateBrushProperties);

    const charNameInput = document.getElementById('charName');
    if (charNameInput) {
        charNameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); addCharacter(); }
        });
    }

    const closeBtn = document.querySelector('.close');
    if (closeBtn) closeBtn.onclick = hideModal;
    window.onclick = function(event) {
        const modal = document.getElementById('monsterModal');
        if (event.target == modal) hideModal();
    }
}

// ========== NUEVO: VISOR MARKDOWN Y TABS CENTRALES ==========

function toggleCenterView(mode) {
    const wb = document.getElementById('whiteboard-wrapper');
    const md = document.getElementById('markdown-viewer-wrapper');
    const btns = document.querySelectorAll('.center-tab-btn');

    if (mode === 'whiteboard') {
        wb.classList.add('visible');
        md.classList.remove('visible');
        btns[0].classList.add('active');
        btns[1].classList.remove('active');
        // Redimensionar canvas por si acaso
        if(masterCanvas) masterCanvas.calcOffset();
    } else {
        wb.classList.remove('visible');
        md.classList.add('visible');
        btns[0].classList.remove('active');
        btns[1].classList.add('active');
    }
}

function loadLocalMarkdown(input) {
    const file = input.files[0];
    if (!file) return;

    document.getElementById('mdFileName').textContent = file.name;

    const reader = new FileReader();
    reader.onload = async function(e) {
        const text = e.target.result;
        
        // Enviar al backend para renderizar a HTML
        const result = await fetchData('/api/render-markdown-text', 'POST', { text: text });
        
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
    
    // Intentar buscar un título H1, si no usar el nombre del archivo
    const h1 = contentDiv.querySelector('h1');
    let title = h1 ? h1.textContent : (document.getElementById('mdFileName').textContent || "Documento");

    await fetchData('/api/screen/show-card', 'POST', { title: title, html: contentDiv.innerHTML });
    updateStatus('Documento proyectado');
}


// ========== PIZARRA ==========
function initWhiteboard() {
    const container = document.getElementById('canvasContainer');
    if (!container || masterCanvas) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    const canvasElement = document.getElementById('masterCanvas');
    canvasElement.width = w;
    canvasElement.height = h;

    masterCanvas = new fabric.Canvas('masterCanvas', { width: w, height: h, backgroundColor: 'white', isDrawingMode: true });
    updateBrushProperties();

    masterCanvas.on('path:created', () => saveWhiteboardState());
    masterCanvas.on('mouse:down', function(o) {
        if (currentTool === 'brush' || currentTool === 'eraser') return;
        isDrawingShape = true;
        const pointer = masterCanvas.getPointer(o.e);
        shapeOrigX = pointer.x; shapeOrigY = pointer.y;
        const color = document.getElementById('drawingColor').value;
        const width = parseInt(document.getElementById('drawingLineWidth').value, 10);

        if (currentTool === 'rect') activeShape = new fabric.Rect({ left: shapeOrigX, top: shapeOrigY, width: 0, height: 0, fill: 'transparent', stroke: color, strokeWidth: width });
        else if (currentTool === 'circle') activeShape = new fabric.Circle({ left: shapeOrigX, top: shapeOrigY, radius: 1, fill: 'transparent', stroke: color, strokeWidth: width });
        else if (currentTool === 'line') activeShape = new fabric.Line([shapeOrigX, shapeOrigY, shapeOrigX, shapeOrigY], { stroke: color, strokeWidth: width });
        
        if (activeShape) masterCanvas.add(activeShape);
    });

    masterCanvas.on('mouse:move', function(o) {
        if (!isDrawingShape || !activeShape) return;
        const pointer = masterCanvas.getPointer(o.e);
        if (currentTool === 'rect') {
            activeShape.set({ width: Math.abs(shapeOrigX - pointer.x), height: Math.abs(shapeOrigY - pointer.y) });
            activeShape.set({ left: Math.min(shapeOrigX, pointer.x), top: Math.min(shapeOrigY, pointer.y) });
        } else if (currentTool === 'circle') {
            activeShape.set({ radius: Math.sqrt(Math.pow(shapeOrigX - pointer.x, 2) + Math.pow(shapeOrigY - pointer.y, 2)) / 2 });
        } else if (currentTool === 'line') {
            activeShape.set({ x2: pointer.x, y2: pointer.y });
        }
        masterCanvas.renderAll();
    });

    masterCanvas.on('mouse:up', function() {
        if (isDrawingShape) { isDrawingShape = false; activeShape.setCoords(); saveWhiteboardState(); activeShape = null; }
    });

    fetch('/api/whiteboard/load').then(r => r.json()).then(data => { if(data.state) masterCanvas.loadFromJSON(data.state, masterCanvas.renderAll.bind(masterCanvas)); });
    
    window.addEventListener('resize', () => {
        if(!document.getElementById('whiteboard-wrapper').classList.contains('wb-fullscreen') && masterCanvas){
             const c = document.getElementById('canvasContainer');
             masterCanvas.setWidth(c.clientWidth); masterCanvas.setHeight(c.clientHeight);
        }
    });
}


function setupGrid(canvas) {
    // Este evento se dispara cada vez que el canvas se refresca
    canvas.on('after:render', function() {
        if (!showGrid) return;

        const ctx = canvas.getContext();
        ctx.save(); // Guarda el estado actual del pincel
        
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)'; // Color blanco suave y transparente
        ctx.lineWidth = 1;

        // Dibujar líneas verticales
        for (let i = 0; i <= canvas.width; i += gridSize) {
            ctx.moveTo(i, 0);
            ctx.lineTo(i, canvas.height);
        }

        // Dibujar líneas horizontales
        for (let i = 0; i <= canvas.height; i += gridSize) {
            ctx.moveTo(0, i);
            ctx.lineTo(canvas.width, i);
        }

        ctx.stroke();
        ctx.restore(); // Restaura el pincel para no afectar a otros dibujos
    });
}
function toggleWhiteboardFullscreen() {
    const wrapper = document.getElementById('whiteboard-wrapper');
    const btn = document.getElementById('btnFullscreenWB');
    if (!wrapper) return;
    if (!wrapper.classList.contains('wb-fullscreen')) {
        wrapper.classList.add('wb-fullscreen');
        if(btn) btn.textContent = "🔽 Salir de Pantalla Completa";
        if (masterCanvas) { masterCanvas.setWidth(window.innerWidth); masterCanvas.setHeight(window.innerHeight - 80); }
    } else {
        wrapper.classList.remove('wb-fullscreen');
        if(btn) btn.textContent = "⛶ Pantalla Completa";
        const c = document.getElementById('canvasContainer');
        if (masterCanvas && c) { masterCanvas.setWidth(c.clientWidth); masterCanvas.setHeight(c.clientHeight); }
    }
}

function setTool(toolName) {
    if(!masterCanvas) return;
    currentTool = toolName;
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
    const ids = {'brush':'toolBrush', 'line':'toolLine', 'rect':'toolRect', 'circle':'toolCircle', 'eraser':'toolEraser'};
    if(ids[toolName]) document.getElementById(ids[toolName])?.classList.add('active');
    
    if (toolName === 'brush' || toolName === 'eraser') {
        masterCanvas.isDrawingMode = true;
        updateBrushProperties();
    } else {
        masterCanvas.isDrawingMode = false;
        masterCanvas.selection = true; 
    }
}

function updateBrushProperties() {
    if (!masterCanvas) return;
    const color = document.getElementById('drawingColor') ? document.getElementById('drawingColor').value : '#000';
    const width = document.getElementById('drawingLineWidth') ? parseInt(document.getElementById('drawingLineWidth').value, 10) : 3;
    masterCanvas.freeDrawingBrush.color = (currentTool === 'eraser') ? '#ffffff' : color;
    masterCanvas.freeDrawingBrush.width = (currentTool === 'eraser') ? width * 5 : width;
}
function toggleGrid() {
    showGrid = !showGrid;
    if (masterCanvas) {
        masterCanvas.renderAll(); // Fuerza el redibujado para que se vea el cambio
    }
    
    // Sincronizar con el jugador usando la función de comunicación existente
    fetchData('/api/screen/toggle-grid', 'POST', { show: showGrid });
}

// No olvides añadirla a las exportaciones para que sea accesible desde el HTML
window.toggleGrid = toggleGrid;
function clearCanvas() { if(masterCanvas && confirm('¿Borrar todo?')) { masterCanvas.clear(); masterCanvas.backgroundColor='white'; saveWhiteboardState(); }}
async function saveWhiteboardState() { if(masterCanvas) await fetchData('/api/whiteboard/save', 'POST', { state: JSON.stringify(masterCanvas.toJSON()) }); }
async function projectWhiteboard() { await saveWhiteboardState(); await saveScreenCommand('whiteboard'); updateStatus("Mostrando Pizarra"); }
async function stopProjectingWhiteboard() { await saveScreenCommand('initiative'); updateStatus("Regresando"); }

// ========== UTILS ==========
function updateStatus(msg, err=false) {
    const el = document.getElementById('statusText'); const ind = document.querySelector('.status-indicator');
    if (el) el.textContent = msg;
    if (ind) ind.style.backgroundColor = err ? 'red' : '#00bfa5';
}
async function fetchData(url, method='GET', data=null) {
    const opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (data) opts.body = JSON.stringify(data);
    try { const r = await fetch(url, opts); return await r.json(); } catch (e) { console.error(e); return null; }
}
async function saveScreenCommand(type, data={}) { return fetchData('/api/screen/command', 'POST', { type, data }); }

// ========== LÓGICA DE JUEGO & RETRATO ==========
async function loadGameState() {
    const result = await fetchData('/api/characters');
    if (result) renderInitiativeList(result.characters, result.current_turn, result.round_number);
}

function renderInitiativeList(characters, currentTurnIndex, roundNumber) {
    const list = document.getElementById('initiativeList');
    if (!list) return;
    
    list.innerHTML = '';
    const roundEl = document.getElementById('roundNumber');
    if(roundEl) roundEl.textContent = roundNumber;
    
    let currentTurnName = 'N/A';
    const portraitContainer = document.getElementById('active-turn-container');
    const portraitImg = document.getElementById('active-turn-img');
    const portraitName = document.getElementById('active-turn-name');

    // Ocultar retrato por defecto
    if(portraitContainer) portraitContainer.style.display = 'none';

    characters.forEach((char, index) => {
        const isCurrent = (index === currentTurnIndex);
        if (isCurrent) {
            currentTurnName = char.name;
            // ACTUALIZAR RETRATO
            if (char.portrait_path && portraitContainer && portraitImg) {
                portraitImg.src = char.portrait_path;
                portraitName.textContent = char.name;
                portraitContainer.style.display = 'block';
            }
        }
        
        const item = document.createElement('div');
        item.className = 'initiative-item' + (isCurrent ? ' active-turn' : '') + (char.hp <= 0 ? ' defeated' : '');
        item.innerHTML = `
            <div class="char-info"><span class="char-name">${char.name}</span> <span class="char-ini">(${char.initiative})</span></div>
            <div class="char-controls">
                <span class="hp-status">${char.hp}${char.max_hp ? '/'+char.max_hp : ''}</span>
                <input type="number" value="${char.hp||''}" class="hp-input" style="width:40px" onchange="updateHP(${char.id}, this.value)">
                <button class="delete-btn" onclick="deleteCharacter(${char.id})">❌</button>
            </div>`;
        list.appendChild(item);
    });
    
    const nameEl = document.getElementById('currentTurnName');
    if(nameEl) nameEl.textContent = currentTurnName;
}

// ========== ACCIONES JUEGO ==========
async function addCharacter(name, ini, hp, max_hp, type, slug) { 
    const n = name || document.getElementById('charName').value;
    if (!n) return;
    await fetchData('/api/characters', 'POST', { 
        name: n, 
        initiative: ini || parseInt(document.getElementById('charInitiative').value), 
        hp: hp !== undefined ? hp : document.getElementById('charHP').value, 
        max_hp: max_hp||hp, type: type||'player', slug: slug 
    });
    if (!name) { document.getElementById('charName').value = ''; document.getElementById('charInitiative').value = ''; document.getElementById('charHP').value = ''; }
    loadGameState();
}
async function deleteCharacter(id) { if (confirm("¿Borrar?")) { await fetchData(`/api/characters/${id}`, 'DELETE'); loadGameState(); }}
async function updateHP(id, val) { await fetchData(`/api/characters/${id}/hp`, 'PUT', { hp: parseInt(val) }); loadGameState(); }
async function nextTurn() { await fetchData('/api/game/next-turn', 'POST'); loadGameState(); }
async function prevTurn() { await fetchData('/api/game/prev-turn', 'POST'); loadGameState(); }
async function clearInitiative() { if (confirm("¿Reset?")) { await fetchData('/api/game/reset', 'POST'); loadGameState(); clearScreen(); }}

// ========== CONTENIDO ==========
function loadGrimoireDataAndRender() {
    try {
        const m = document.getElementById('grimorio-data'); if(m) grimoireMonsters = JSON.parse(m.textContent);
        const s = document.getElementById('spells-data'); if(s) grimoireSpells = JSON.parse(s.textContent);
        const r = document.getElementById('rules-data'); if(r) grimoireRules = JSON.parse(r.textContent);
    } catch (e) {}
}

function filterContent(type) {
    const ids = {'monster':['grimoireFilter','grimoireList'], 'spell':['spellFilter','spellList'], 'rule':['ruleFilter','ruleList']};
    const [inId, listId] = ids[type] || [];
    if (!inId) return;
    const txt = document.getElementById(inId).value.toLowerCase();
    document.getElementById(listId).querySelectorAll('.tarjeta').forEach(t => {
        t.style.display = t.getAttribute('data-nombre').toLowerCase().includes(txt) ? "block" : "none";
    });
}

// MODAL
function showModal() { document.getElementById('monsterModal').style.display = 'block'; }
function hideModal() { document.getElementById('monsterModal').style.display = 'none'; }
let currentContentData = null, currentContentType = null;

async function showContentDetail(type, slug) {
    currentContentType = type;
    const c = document.getElementById('monsterDetailContent');
    if(c) c.innerHTML = '<div class="loading">Cargando...</div>'; 
    showModal();
    const r = await fetch(`/content/${type}/${slug}`);
    if(c) c.innerHTML = await r.text();
    
    if (type === 'monster') currentContentData = grimoireMonsters.find(m => m.slug === slug);
    else if (type === 'spell') currentContentData = grimoireSpells.find(m => m.slug === slug);
    else if (type === 'rule') currentContentData = grimoireRules.find(m => m.slug === slug);

    const btn = document.getElementById('btnAddToInitiative');
    if (btn) btn.style.display = (type === 'monster') ? 'inline-block' : 'none';
}

async function addMonsterToInitiative() {
    if (!currentContentData || currentContentType !== 'monster') return;
    const ini = document.getElementById('modalMonsterIni') ? document.getElementById('modalMonsterIni').value : 0;
    await addCharacter(currentContentData.nombre, ini, currentContentData.hp, currentContentData.hp, 'monster', currentContentData.slug);
    hideModal();
}

async function projectCurrentCard() {
    const c = document.getElementById('monsterDetailContent');
    if (!c) return;
    const title = c.querySelector('h1, h2')?.innerText || "Información";
    await fetchData('/api/screen/show-card', 'POST', { title: title, html: c.innerHTML });
    updateStatus('Proyectado');
}

// ========== MULTIMEDIA ==========
function openFilePicker(t) { 
    const i = document.createElement('input'); i.type = 'file'; i.accept = t==='image'?'image/*':'video/*'; 
    i.onchange = e => uploadMedia(e.target.files[0], t); i.click(); 
}
async function uploadMedia(f, t) { 
    if(!f) return; 
    const fd = new FormData(); fd.append('file', f); 
    const r = await(await fetch('/api/media/upload', {method:'POST', body:fd})).json(); 
    if(r.success) { 
        if(t==='image') { currentImage = r.url; updateStatus('Imagen lista'); }
        else { currentVideo = r.url; updateStatus('Video listo'); }
    }
}
function updateYoutubePreview() { 
    const v = document.getElementById('youtubeUrl').value.match(/(?:v=|youtu\.be\/)([^&]+)/); 
    if(v) currentYouTubeId = v[1]; 
}
async function playYouTube() { if(currentYouTubeId) fetchData('/api/screen/show-youtube', 'POST', { video_id: currentYouTubeId }); }
async function toggleYoutubePlayback() { fetchData('/api/screen/youtube-control', 'POST', { action: 'toggle' }); }
async function showImage() { if(currentImage) fetchData('/api/screen/show-image', 'POST', { url: currentImage }); }
async function playVideo() { if(currentVideo) fetchData('/api/screen/show-video', 'POST', { url: currentVideo }); }
async function stopVideo() { clearScreen(); }
async function showInitiativeOnScreen() { fetchData('/api/screen/show-initiative', 'POST'); }
async function clearScreen() { fetchData('/api/screen/clear', 'POST'); loadGameState(); }
async function blackoutScreen() { fetchData('/api/screen/blackout', 'POST'); }
// Variable para el elemento de audio
const masterAudio = document.getElementById('master-audio-element');
// ========== SISTEMA DE AUDIO DEL MÁSTER ==========

// Función para obtener el elemento de audio de forma segura
function getMasterAudio() {
    return document.getElementById('master-audio-element');
}

// Cargar lista de audios al iniciar
// En master.js

async function loadAudioList() {
    try {
        console.log("Cargando lista de audios...");
        const response = await fetch('/api/audio/list');
        const files = await response.json();
        const select = document.getElementById('audioList');
        
        if (!select) return;

        // Guardamos la selección actual si existe
        const currentSelection = select.value;

        select.innerHTML = '<option value="">Seleccionar pista...</option>';
        
        files.forEach(file => {
            const opt = document.createElement('option');
            // IMPORTANTE: Aquí construimos la ruta completa
            opt.value = `/static/uploads/audio/${file}`;
            opt.textContent = file;
            select.appendChild(opt);
        });

        // Restaurar selección si es posible
        if(currentSelection) select.value = currentSelection;
        
    } catch (e) {
        console.error("Error cargando audios:", e);
    }
}

function playMasterAudio() {
    const audio = document.getElementById('master-audio-element');
    const select = document.getElementById('audioList');
    
    // 1. COMPROBACIONES BÁSICAS
    if (!select || !select.value) {
        alert("⚠️ Selecciona una pista primero.");
        return;
    }
    if (!audio) {
        alert("⚠️ Error crítico: No encuentro la etiqueta <audio> en el HTML.");
        return;
    }

    console.log("▶ Intentando reproducir:", select.value);

    // 2. CARGA DEL ARCHIVO
    // Construimos la ruta absoluta para comparar con seguridad
    const targetSrc = new URL(select.value, window.location.origin).href;
    
    if (audio.src !== targetSrc) {
        console.log("   Cargando nueva fuente...");
        audio.src = select.value;
        audio.load(); // Obligatorio al cambiar de fuente
    }

    // 3. ASEGURAR VOLUMEN
    const volSlider = document.getElementById('masterVolume');
    if (volSlider) {
        audio.volume = volSlider.value;
        console.log("   Volumen establecido a:", volSlider.value);
    }

    // 4. REPRODUCIR CON DIAGNÓSTICO
    const playPromise = audio.play();

    if (playPromise !== undefined) {
        playPromise.then(() => {
            console.log("✅ ¡El navegador dice que está sonando!");
            // Si ves este mensaje en consola pero no oyes nada, revisa tus altavoces o el volumen del PC
        })
        .catch(error => {
            console.error("❌ ERROR AL REPRODUCIR:", error);
            
            if (error.name === 'NotAllowedError') {
                alert("🛑 BLOQUEO DE BRAVE DETECTADO.\n\nEl navegador ha impedido el audio automático.\nSOLUCIÓN: Haz clic en el icono del candado (🔒) o ajustes a la izquierda de la dirección web y permite 'Sonido' o 'Autoplay'.");
            } else if (error.name === 'NotSupportedError') {
                alert("🛑 ERROR DE FORMATO.\nEl archivo parece estar dañado o no es un MP3 válido.\nIntenta subir otro archivo simple (ej: 'test.mp3').");
            } else {
                alert("🛑 ERROR DESCONOCIDO:\n" + error.message + "\n\nAbre la consola (F12) para ver más detalles.");
            }
        });
    }
}

function pauseMasterAudio() {
    const audio = getMasterAudio();
    if (audio) audio.pause();
}

function stopMasterAudio() {
    const audio = getMasterAudio();
    if (audio) {
        audio.pause();
        audio.currentTime = 0;
    }
}

function updateMasterVolume(val) {
    const audio = getMasterAudio();
    if (audio) audio.volume = val;
}

function openAudioPicker() { 
    const i = document.createElement('input'); 
    i.type = 'file'; 
    i.accept = 'audio/*'; 
    i.onchange = e => uploadAudio(e.target.files[0]); 
    i.click(); 
}

async function uploadAudio(file) { 
    if(!file) return; 
    const fd = new FormData(); 
    fd.append('file', file); 
    
    updateStatus('Subiendo audio...');
    try {
        const r = await (await fetch('/api/media/upload?type=audio', { method:'POST', body:fd })).json(); 
        if(r.success) { 
            updateStatus('Audio subido con éxito');
            await loadAudioList(); // Esperamos a que recargue la lista
        }
    } catch (e) {
        updateStatus('Error al subir audio', true);
    }
}

// ========== UNIFICACIÓN DE INICIALIZACIÓN ==========
// Borra cualquier otro document.addEventListener('DOMContentLoaded'...) que tengas al final
document.addEventListener('DOMContentLoaded', function() {
    console.log("🎮 RPG Master Control unificado iniciando...");
    
    // Cargar datos del grimorio
    try { loadGrimoireDataAndRender(); } catch (e) { console.error("Error en grimorio:", e); }
    
    // Iniciar estado del juego
    loadGameState(); 
    
    // Configurar botones
    setupEventListeners();
    
    // Iniciar Pizarra
    if (typeof fabric !== 'undefined') { initWhiteboard(); }
    
    // Iniciar Audio
    loadAudioList();
    
    // Polling de estado
    setInterval(loadGameState, 3000); 
});