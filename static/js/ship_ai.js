/**
 * MADRE — IA de nave para Mothership RPG
 * Grabación continua con MediaRecorder → Whisper local en servidor
 * para wake word "madre" (o el nombre configurado).
 */
(function () {
  "use strict";

  const fab = document.getElementById("shipai-fab");
  if (!fab) return;

  const panel      = document.getElementById("shipai-panel");
  const closeBtn   = document.getElementById("shipai-close");
  const tabLive    = document.getElementById("shipai-tab-live");
  const tabCfg     = document.getElementById("shipai-tab-cfg");
  const secLive    = document.getElementById("shipai-sec-live");
  const secCfg     = document.getElementById("shipai-sec-cfg");
  const wakeOuter  = document.getElementById("shipai-wake");
  const wakeText   = document.getElementById("shipai-wake-text");
  const interimEl  = document.getElementById("shipai-interim");
  const logEl      = document.getElementById("shipai-log");
  const btnListen  = document.getElementById("shipai-btn-listen");
  const btnMute    = document.getElementById("shipai-btn-mute");
  const nameEl     = document.getElementById("shipai-name");

  const cfgName        = document.getElementById("shipai-cfg-name");
  const cfgPersonality = document.getElementById("shipai-cfg-personality");
  const cfgContext     = document.getElementById("shipai-cfg-context");
  const cfgRedlines    = document.getElementById("shipai-cfg-redlines");
  const cfgVoice       = document.getElementById("shipai-cfg-voice");
  const cfgModel       = document.getElementById("shipai-cfg-model");
  const btnCfgSave     = document.getElementById("shipai-cfg-save");
  const cfgFeedback    = document.getElementById("shipai-cfg-feedback");
  const btnVoiceTest   = document.getElementById("shipai-cfg-test-voice");
  const resBody        = document.getElementById("shipai-res-body");
  const btnResAdd      = document.getElementById("shipai-res-add");

  // ── Estado ────────────────────────────────────────────────────────────────────
  let cfg = { ai_name: "MADRE", model: "", personality: "", ship_context: "", redlines: "", voice_lang: "es-ES", voice_name: "" };
  let _hasClaudeKey = false;
  let _pendingClaudeModel = null;

  let isListening  = false;
  let wakeActive   = false;
  let isProcessing = false;
  let isSpeaking   = false;
  let wakeTimeout  = null;

  let mediaStream    = null;
  let mediaRecorder  = null;
  let chunkInterval  = null;
  let audioChunks    = [];
  let pendingXcr     = false;   // transcripción en curso

  let ttsBuffer  = "";
  let ttsQueue   = [];
  let ttsGen     = 0;   // generación TTS: onend de utterances viejas se ignora
  let selectedVoice = null;

  let cmdBuf = "";   // buffer para detectar [CMD:...] que pueden venir partidos entre tokens

  // ── Panel / tabs ──────────────────────────────────────────────────────────────
  fab.addEventListener("click", () => panel.classList.toggle("collapsed"));
  closeBtn.addEventListener("click", () => panel.classList.add("collapsed"));
  tabLive.addEventListener("click", () => switchTab("live"));
  tabCfg.addEventListener("click",  () => switchTab("cfg"));

  function switchTab(name) {
    const live = name === "live";
    tabLive.classList.toggle("active",  live);
    tabCfg.classList.toggle("active",  !live);
    secLive.style.display = live ? ""     : "none";
    secCfg.style.display  = live ? "none" : "";
    if (!live) populateVoices();
  }

  // ── Config ────────────────────────────────────────────────────────────────────
  function loadConfig() {
    fetch("/api/ship-ai/config").then(r => r.json()).then(data => {
      cfg = data;
      applyConfig();
    }).catch(console.error);
  }

  function applyConfig() {
    nameEl.textContent      = cfg.ai_name || "MADRE";
    cfgName.value           = cfg.ai_name || "MADRE";
    cfgPersonality.value    = cfg.personality || "";
    cfgContext.value        = cfg.ship_context || "";
    cfgRedlines.value       = cfg.redlines || "";
    selectedVoice           = getVoiceByName(cfg.voice_name);
    renderResources(cfg.resources || []);
    if (cfg.model && cfgModel) cfgModel.value = cfg.model;
  }

  // ── Modelos de lenguaje ───────────────────────────────────────────────────────
  async function loadModels() {
    try {
      const data = await fetch("/api/ship-ai/models").then(r => r.json());
      _hasClaudeKey = data.has_claude_key;
      cfgModel.innerHTML = '<option value="">Ollama (defecto del sistema)</option>';
      if (data.ollama && data.ollama.length > 0) {
        const grp = document.createElement("optgroup");
        grp.label = "Ollama (local)";
        data.ollama.forEach(m => {
          const opt = document.createElement("option");
          opt.value = m.id; opt.textContent = m.label;
          grp.appendChild(opt);
        });
        cfgModel.appendChild(grp);
      }
      if (data.claude && data.claude.length > 0) {
        const grp = document.createElement("optgroup");
        grp.label = "Claude (Anthropic API)";
        data.claude.forEach(m => {
          const opt = document.createElement("option");
          opt.value = m.id;
          opt.textContent = m.label + (data.has_claude_key ? "" : " 🔑");
          grp.appendChild(opt);
        });
        cfgModel.appendChild(grp);
      }
      if (cfg.model) cfgModel.value = cfg.model;
    } catch (e) { console.warn("[ShipAI] No se pudieron cargar los modelos:", e); }
  }

  cfgModel.addEventListener("change", () => {
    const val = cfgModel.value;
    if (val.startsWith("claude") && !_hasClaudeKey) {
      _pendingClaudeModel = val;
      cfgModel.value = cfg.model || "";
      openShipAiKeyModal();
    }
  });

  function openShipAiKeyModal() {
    const modal   = document.getElementById("claude-key-modal");
    const keyInp  = document.getElementById("claude-key-input");
    const keyErr  = document.getElementById("claude-key-error");
    const saveBtn = document.getElementById("claude-key-save");
    const cancelBtn = document.getElementById("claude-key-cancel");
    if (!modal) return;
    keyInp.value = ""; keyErr.style.display = "none";
    modal.style.display = "flex"; keyInp.focus();

    saveBtn.onclick = async () => {
      const key = keyInp.value.trim();
      if (!key.startsWith("sk-ant-")) {
        keyErr.textContent = "La clave debe empezar por sk-ant-";
        keyErr.style.display = "block"; return;
      }
      saveBtn.disabled = true;
      try {
        const res = await fetch("/api/assistant/set-claude-key", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key }),
        });
        const d = await res.json();
        if (d.error) { keyErr.textContent = d.error; keyErr.style.display = "block"; return; }
        _hasClaudeKey = true;
        modal.style.display = "none";
        if (_pendingClaudeModel) {
          await loadModels();
          cfgModel.value = _pendingClaudeModel;
          _pendingClaudeModel = null;
        }
      } catch (e) { keyErr.textContent = "Error: " + e.message; keyErr.style.display = "block"; }
      finally { saveBtn.disabled = false; }
    };

    cancelBtn.onclick = () => { modal.style.display = "none"; _pendingClaudeModel = null; };
  }

  // ── Tabla de recursos ─────────────────────────────────────────────────────────
  function renderResources(list) {
    resBody.innerHTML = "";
    list.forEach(r => addResourceRow(r.id || "", r.description || "", r.url || "", r.type || "image"));
  }

  function addResourceRow(id, desc, url, type) {
    const tr = document.createElement("tr");
    const sel = `<select class="res-type">
      <option value="image" ${type === "image" ? "selected" : ""}>🖼 imagen</option>
      <option value="audio" ${type === "audio" ? "selected" : ""}>🔊 audio</option>
    </select>`;
    tr.innerHTML = `
      <td><input class="res-id"   value="${_esc(id)}"   placeholder="alarma_nave"></td>
      <td><input class="res-desc" value="${_esc(desc)}" placeholder="Alarma de emergencia"></td>
      <td>${sel}</td>
      <td><input class="res-url"  value="${_esc(url)}"  placeholder="https://... o /static/uploads/audio/..."></td>
      <td><button class="del-btn" title="Eliminar">✕</button></td>`;
    tr.querySelector(".del-btn").addEventListener("click", () => tr.remove());
    resBody.appendChild(tr);
  }

  function _esc(s) { return (s || "").replace(/"/g, "&quot;"); }

  function collectResources() {
    return Array.from(resBody.querySelectorAll("tr")).map(tr => ({
      id:          tr.querySelector(".res-id").value.trim(),
      description: tr.querySelector(".res-desc").value.trim(),
      type:        tr.querySelector(".res-type").value,
      url:         tr.querySelector(".res-url").value.trim(),
    })).filter(r => r.id);
  }

  btnResAdd.addEventListener("click", () => addResourceRow("", "", ""));

  btnCfgSave.addEventListener("click", () => {
    const newCfg = {
      ai_name:      cfgName.value.trim() || "MADRE",
      model:        cfgModel.value,
      personality:  cfgPersonality.value.trim(),
      ship_context: cfgContext.value.trim(),
      redlines:     cfgRedlines.value.trim(),
      voice_lang:   "es-ES",
      voice_name:   cfgVoice.value,
      resources:    collectResources(),
    };
    fetch("/api/ship-ai/config", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(newCfg),
    }).then(r => r.json()).then(() => {
      cfg = newCfg;
      applyConfig();
      cfgFeedback.textContent = "✓ Guardado";
      cfgFeedback.className   = "shipai-feedback ok";
      setTimeout(() => { cfgFeedback.textContent = ""; }, 2500);
    }).catch(() => {
      cfgFeedback.textContent = "Error al guardar";
      cfgFeedback.className   = "shipai-feedback err";
    });
  });

  // ── Voz / TTS ─────────────────────────────────────────────────────────────────
  function getVoiceByName(name) {
    return name ? (speechSynthesis.getVoices().find(v => v.name === name) || null) : null;
  }

  function populateVoices() {
    const voices = speechSynthesis.getVoices();
    cfgVoice.innerHTML = '<option value="">— Voz por defecto —</option>';
    const addGrp = (label, list) => {
      if (!list.length) return;
      const g = document.createElement("optgroup");
      g.label = label;
      list.forEach(v => {
        const o = document.createElement("option");
        o.value = v.name;
        o.textContent = `${v.name} (${v.lang})`;
        if (v.name === cfg.voice_name) o.selected = true;
        g.appendChild(o);
      });
      cfgVoice.appendChild(g);
    };
    addGrp("Español",       voices.filter(v =>  v.lang.startsWith("es")));
    addGrp("Otros idiomas", voices.filter(v => !v.lang.startsWith("es")));
    selectedVoice = getVoiceByName(cfg.voice_name);
  }
  speechSynthesis.onvoiceschanged = () => { selectedVoice = getVoiceByName(cfg.voice_name); populateVoices(); };

  btnVoiceTest.addEventListener("click", () => {
    selectedVoice = getVoiceByName(cfgVoice.value);
    speakImmediate((cfg.ai_name || "MADRE") + " en línea. Sistemas operativos.");
  });

  function speakImmediate(text) {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    if (selectedVoice) u.voice = selectedVoice;
    u.lang = cfg.voice_lang || "es-ES";
    u.rate = 0.92;
    speechSynthesis.speak(u);
  }

  function ttsAppendToken(token) {
    ttsBuffer += token;
    const m = /[.!?][\s\n]/.exec(ttsBuffer);
    if (m) {
      const s = ttsBuffer.slice(0, m.index + 1).trim();
      ttsBuffer = ttsBuffer.slice(m.index + m[0].length);
      if (s.length > 4) ttsPush(s);
    }
  }
  function ttsFlush() { if (ttsBuffer.trim().length > 2) ttsPush(ttsBuffer.trim()); ttsBuffer = ""; }
  function ttsPush(text) { ttsQueue.push(text); if (!isSpeaking) ttsNext(ttsGen); }
  function ttsNext(gen) {
    if (gen !== ttsGen) return;   // onend de respuesta anterior, ignorar
    if (!ttsQueue.length) {
      isSpeaking = false;
      if (isListening && !isProcessing) resumeListening();
      return;
    }
    isSpeaking = true;
    const myGen  = ttsGen;
    const ttsText = ttsQueue.shift();
    const u = new SpeechSynthesisUtterance(ttsText);
    if (selectedVoice) u.voice = selectedVoice;
    u.lang = cfg.voice_lang || "es-ES";
    u.rate = 0.92;
    // Guardia: si onend no dispara (bug Chrome/Brave), forzar avance
    const guard = setTimeout(() => {
      console.warn("[ShipAI] TTS onend no disparó, forzando siguiente");
      ttsNext(myGen);
    }, Math.max(4000, (ttsText.length / 8) * 1000 + 2000));
    u.onend = u.onerror = () => { clearTimeout(guard); ttsNext(myGen); };
    speechSynthesis.resume();   // workaround bug Chrome: TTS pausado en background
    speechSynthesis.speak(u);
  }
  function ttsClear() {
    ttsGen++;   // invalida todos los onend pendientes
    speechSynthesis.cancel();
    ttsQueue = []; ttsBuffer = ""; isSpeaking = false;
  }

  btnMute.addEventListener("click", () => {
    ttsClear();
    btnMute.style.display = "none";
    if (isListening && !isProcessing) resumeListening();
  });

  // ── MediaRecorder continuo ────────────────────────────────────────────────────
  const CHUNK_MS = 4000;   // enviar fragmento de audio cada 4 s

  async function acquireMic() {
    if (!navigator.mediaDevices) return false;
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      return true;
    } catch (err) {
      console.error("[ShipAI] getUserMedia falló:", err.name, err.message);
      setWakeState("error", "Permiso de micrófono denegado: " + err.name);
      return false;
    }
  }

  function releaseMic() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }
  }

  async function startListening() {
    if (!navigator.mediaDevices) {
      setWakeState("error", "API de audio no disponible");
      return;
    }
    if (!await acquireMic()) return;
    isListening = true;
    btnListen.textContent = "🔴 Detener escucha";
    btnListen.classList.add("active");
    setWakeState("listening");
    startChunkRecording();
  }

  function startChunkRecording() {
    if (!mediaStream || !isListening) return;
    audioChunks = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    const mr = new MediaRecorder(mediaStream, { mimeType });
    mediaRecorder = mr;
    mr.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mr.onstop = () => {
      if (mr !== mediaRecorder) return;   // timer de un recorder antiguo, ignorar
      if (!isListening || isSpeaking || isProcessing) return;
      const blob = new Blob(audioChunks, { type: mr.mimeType });
      audioChunks = [];
      if (blob.size > 2000) transcribeChunk(blob);
      setTimeout(() => {
        if (isListening && !isSpeaking && !isProcessing) startChunkRecording();
      }, 50);
    };
    mr.start();
    // Timer capturado en closure: solo para ESTE recorder, no el global
    setTimeout(() => {
      if (mr === mediaRecorder && mr.state === "recording") mr.stop();
    }, CHUNK_MS);
  }

  function pauseListening() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.onstop = null;
      mediaRecorder.stop();
    }
    audioChunks = [];
    releaseMic();   // apagar micrófono físicamente para evitar eco TTS
  }

  async function resumeListening() {
    if (!isListening) return;
    if (!await acquireMic()) return;
    startChunkRecording();
    setWakeState("listening");
  }

  function stopListening() {
    isListening  = false;
    wakeActive   = false;
    clearTimeout(wakeTimeout);
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.onstop = null;
      mediaRecorder.stop();
    }
    mediaRecorder = null;
    releaseMic();
    btnListen.textContent = "🎙 Activar escucha";
    btnListen.classList.remove("active");
    setWakeState("off");
    interimEl.textContent = "";
  }

  btnListen.addEventListener("click", () => {
    isListening ? stopListening() : startListening();
  });

  // ── Transcripción Whisper ────────────────────────────────────────────────────
  function transcribeChunk(blob) {
    const fd = new FormData();
    fd.append("audio", blob, "chunk.webm");

    fetch("/api/ship-ai/transcribe", { method: "POST", body: fd })
      .then(r => r.json())
      .then(data => {
        const text = (data.text || "").trim();
        console.log("[ShipAI] transcripción:", JSON.stringify(text));
        if (!text) return;
        processTranscript(text);
      })
      .catch(err => console.warn("[ShipAI] transcribe error:", err));
  }

  function processTranscript(text) {
    const lower    = text.toLowerCase();
    const wakeWord = (cfg.ai_name || "MADRE").toLowerCase();
    interimEl.textContent = "✓ " + text;
    setTimeout(() => { interimEl.textContent = ""; }, 2000);

    if (wakeActive && !isProcessing) {
      clearTimeout(wakeTimeout);
      triggerQuery(text);
      return;
    }

    if (!isProcessing) {
      const idx = lower.indexOf(wakeWord);
      if (idx !== -1) {
        const after = text.slice(idx + wakeWord.length).replace(/^[\s,.:!?]+/, "").trim();
        if (after.length > 3) {
          triggerQuery(after);
        } else {
          enterWakeMode();
        }
      }
    }
  }

  function enterWakeMode() {
    wakeActive = true;
    pauseListening();    // parar chunks actuales
    audioChunks = [];
    resumeListening();   // empezar chunk fresco para la pregunta
    setWakeState("wake");
    wakeTimeout = setTimeout(() => {
      wakeActive = false;
      if (isListening) setWakeState("listening");
    }, 10000);
  }

  function triggerQuery(query) {
    wakeActive   = false;
    isProcessing = true;
    ttsClear();          // cancelar TTS de respuesta anterior + invalidar onend viejos
    pauseListening();
    setWakeState("processing");
    appendLog("user", query);
    sendQuery(query);
  }

  // ── Disparadores de pantalla ──────────────────────────────────────────────────
  const _CMD_RE = /\[CMD:(\w+):([^\]]+)\]/g;

  // Filtra marcadores [CMD:...] del token entrante; ejecuta los que estén completos.
  // Devuelve el texto limpio para TTS/log. Usa cmdBuf para manejar marcadores partidos.
  function filterCmds(token) {
    cmdBuf += token;
    // Reemplazar los CMD completos y ejecutarlos
    const safe = cmdBuf.replace(_CMD_RE, (_, type, id) => {
      executeScreenCmd(type.trim(), id.trim());
      return "";
    });
    // Si hay un '[' sin cerrar al final, puede ser un CMD incompleto — retener
    const lastOpen = safe.lastIndexOf("[");
    if (lastOpen !== -1 && safe.indexOf("]", lastOpen) === -1) {
      cmdBuf = safe.slice(lastOpen);
      return safe.slice(0, lastOpen);
    }
    cmdBuf = "";
    return safe;
  }

  function flushCmdBuf() {
    // Al terminar el stream, descartar cualquier marcador incompleto
    cmdBuf = "";
  }

  function executeScreenCmd(type, id) {
    if (type === "image") {
      const res = (cfg.resources || []).find(r => r.id === id);
      if (!res || !res.url) {
        console.warn("[ShipAI] CMD image: recurso desconocido o sin URL:", id);
        return;
      }
      console.log("[ShipAI] CMD → pantalla player: imagen", id, res.url);
      fetch("/api/screen/show-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: res.url }),
      }).catch(console.error);
    } else if (type === "audio") {
      const res = (cfg.resources || []).find(r => r.id === id);
      if (!res || !res.url) {
        console.warn("[ShipAI] CMD audio: recurso desconocido o sin URL:", id);
        return;
      }
      console.log("[ShipAI] CMD → pantalla player: audio", id, res.url);
      fetch("/api/screen/play-audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: res.url, loop: true }),
      }).catch(console.error);
    } else if (type === "audio_stop") {
      fetch("/api/screen/stop-audio", { method: "POST" }).catch(console.error);
    } else if (type === "clear") {
      fetch("/api/screen/clear", { method: "POST" }).catch(console.error);
    } else {
      console.warn("[ShipAI] CMD desconocido:", type, id);
    }
  }

  // ── Query / SSE ───────────────────────────────────────────────────────────────
  function sendQuery(query) {
    const aiEntry = appendLog("ai", "");
    const textEl  = aiEntry.querySelector(".shipai-log-text");
    ttsGen++;            // nueva generación para esta respuesta
    ttsBuffer = ""; ttsQueue = [];
    btnMute.style.display = "";

    cmdBuf = "";   // resetear buffer de CMDs para esta respuesta

    fetch("/api/ship-ai/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    }).then(resp => {
      const reader  = resp.body.getReader();
      const decoder = new TextDecoder();
      let full      = "";
      (function read() {
        reader.read().then(({ done, value }) => {
          if (done) { flushCmdBuf(); finishQuery(textEl); return; }
          decoder.decode(value).split("\n").forEach(line => {
            if (!line.startsWith("data: ")) return;
            try {
              const d = JSON.parse(line.slice(6));
              if (d.token) {
                const clean = filterCmds(d.token);   // extrae CMDs, devuelve texto limpio
                full += clean;
                textEl.textContent = full;
                if (clean) ttsAppendToken(clean);
                logEl.scrollTop = logEl.scrollHeight;
              }
              if (d.done)  { flushCmdBuf(); ttsFlush(); finishQuery(textEl); }
              if (d.error) { textEl.textContent = "[Error: " + d.error + "]"; textEl.style.color = "var(--danger)"; finishQuery(textEl); }
            } catch (_) {}
          });
          if (!isSpeaking && ttsQueue.length) ttsNext(ttsGen);
          read();
        }).catch(() => finishQuery(textEl));
      })();
    }).catch(() => {
      textEl.textContent = "[Error de conexión]";
      textEl.style.color = "var(--danger)";
      finishQuery(textEl);
    });
  }

  function finishQuery(textEl) {
    isProcessing = false;
    if (!isSpeaking && isListening) {
      resumeListening();
      setWakeState("listening");
    } else if (!isListening) {
      setWakeState("off");
      btnMute.style.display = "none";
    }
    // Si TTS sigue hablando, ttsNext() llamará resumeListening() al terminar
  }

  // ── Wake state UI ─────────────────────────────────────────────────────────────
  function setWakeState(state, msg) {
    wakeOuter.dataset.state = state;
    const name = (cfg.ai_name || "MADRE").toLowerCase();
    const texts = {
      off:        'Di "' + name + '" para activar',
      listening:  'Escuchando... di "' + name + '"',
      wake:       "Escuchando pregunta...",
      processing: "Procesando...",
      error:      msg || "Error",
    };
    wakeText.textContent = texts[state] || state;
  }

  // ── Log ───────────────────────────────────────────────────────────────────────
  function appendLog(role, text) {
    const entry = document.createElement("div");
    entry.className = "shipai-log-entry shipai-log-" + role;
    const label = document.createElement("span");
    label.className   = "shipai-log-label";
    label.textContent = role === "user" ? "👤" : (cfg.ai_name || "MADRE");
    const body = document.createElement("span");
    body.className    = "shipai-log-text";
    body.textContent  = text;
    entry.appendChild(label);
    entry.appendChild(body);
    logEl.appendChild(entry);
    logEl.scrollTop = logEl.scrollHeight;
    return entry;
  }

  document.getElementById("shipai-btn-clear").addEventListener("click", () => { logEl.innerHTML = ""; });

  // ── Watchdog ──────────────────────────────────────────────────────────────────
  // Si debería estar grabando pero el recorder está inactivo, reiniciar
  setInterval(() => {
    if (!isListening || isSpeaking || isProcessing) return;
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      console.warn("[ShipAI] watchdog: recorder inactivo, reiniciando");
      startChunkRecording();
    }
  }, 7000);

  // ── Init ──────────────────────────────────────────────────────────────────────
  loadConfig();
  loadModels();
  if (speechSynthesis.getVoices().length) populateVoices();
  setWakeState("off");

})();
