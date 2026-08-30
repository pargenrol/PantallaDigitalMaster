/**
 * Asistente IA — Pantallasistemas
 * Drawer lateral de chat con RAG via SSE.
 * El filtro de sistema se aplica automáticamente en el servidor
 * según el sistema activo en sesión.
 */

(function () {
  "use strict";

  const fab         = document.getElementById("assistant-fab");
  const drawer      = document.getElementById("assistant-drawer");
  const closeBtn    = document.getElementById("assistant-close");
  const newChatBtn  = document.getElementById("assistant-new-chat");
  const messages    = document.getElementById("assistant-messages");
  const input       = document.getElementById("assistant-input");
  const sendBtn     = document.getElementById("assistant-send");
  const statusDot   = document.getElementById("assistant-status-dot");
  const sysLabel    = document.getElementById("assistant-system-label");
  const modelSel    = document.getElementById("assistant-model-sel");
  const modelHint   = document.getElementById("assistant-model-hint");

  // Historial de conversación en memoria (máx. 3 intercambios = 6 mensajes)
  let conversationHistory = [];
  let hasClaudeKey = false;
  let pendingClaudeModel = null;

  // Lee el sistema activo del bloque JSON embebido en el template
  const systemConfig = JSON.parse(
    document.getElementById("system-config")?.textContent || "{}"
  );
  if (sysLabel && systemConfig.short_name) {
    sysLabel.textContent = systemConfig.short_name;
  }

  // Etiquetas de tipo según el sistema activo
  const TYPE_LABELS = {
    monster: systemConfig.tab_labels?.monsters || "Monstruo",
    spell:   systemConfig.tab_labels?.spells   || "Conjuro",
    rule:    systemConfig.tab_labels?.rules     || "Regla",
  };

  // ── Selector de modelo ────────────────────────────────────────────────────

  // Un modelo Claude solo es utilizable si hay clave configurada; los Ollama
  // listados vienen ya filtrados por el servidor a los realmente instalados.
  function isModelUsable(value) {
    return !!value && !(value.startsWith("claude") && !hasClaudeKey);
  }

  function applySelection() {
    const saved = localStorage.getItem("pdm-assistant-model");
    let candidate = saved && isModelUsable(saved) ? saved : "";
    if (!candidate) {
      const firstUsable = Array.from(modelSel.options).find(o => isModelUsable(o.value));
      candidate = firstUsable ? firstUsable.value : "";
    }
    if (candidate) {
      modelSel.value = candidate;
      modelSel.disabled = false;
      sendBtn.disabled = false;
      modelHint.style.display = "none";
    } else {
      modelSel.value = "";
      modelSel.disabled = true;
      sendBtn.disabled = true;
      modelHint.style.display = "block";
    }
  }

  async function loadModels() {
    try {
      const data = await fetch("/api/assistant/models").then(r => r.json());
      hasClaudeKey = data.has_claude_key;
      modelSel.innerHTML = "";
      if (data.ollama && data.ollama.length > 0) {
        const grp = document.createElement("optgroup");
        grp.label = "Ollama (local)";
        data.ollama.forEach(m => {
          const opt = document.createElement("option");
          opt.value = m.id; opt.textContent = m.label;
          grp.appendChild(opt);
        });
        modelSel.appendChild(grp);
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
        modelSel.appendChild(grp);
      }
      if (modelSel.options.length === 0) {
        const opt = document.createElement("option");
        opt.value = ""; opt.textContent = "— Sin modelos disponibles —";
        modelSel.appendChild(opt);
      }
      applySelection();
    } catch (e) {
      console.warn("No se pudieron cargar los modelos:", e);
    }
  }

  modelSel.addEventListener("change", () => {
    const val = modelSel.value;
    if (val.startsWith("claude") && !hasClaudeKey) {
      pendingClaudeModel = val;
      applySelection();
      openApiModal(); return;
    }
    localStorage.setItem("pdm-assistant-model", val);
  });

  loadModels();

  // ── Modal API key Claude ───────────────────────────────────────────────────

  const claudeModal    = document.getElementById("claude-key-modal");
  const claudeKeyInput = document.getElementById("claude-key-input");
  const claudeKeyError = document.getElementById("claude-key-error");
  const claudeKeySave  = document.getElementById("claude-key-save");
  const claudeKeyCancel = document.getElementById("claude-key-cancel");

  function openApiModal() {
    claudeKeyInput.value = "";
    claudeKeyError.style.display = "none";
    claudeModal.style.display = "flex";
    claudeKeyInput.focus();
  }

  function closeApiModal() { claudeModal.style.display = "none"; pendingClaudeModel = null; }

  claudeKeyCancel.addEventListener("click", closeApiModal);
  claudeModal.addEventListener("click", e => { if (e.target === claudeModal) closeApiModal(); });

  claudeKeySave.addEventListener("click", async () => {
    const key = claudeKeyInput.value.trim();
    if (!key.startsWith("sk-ant-")) {
      claudeKeyError.textContent = "La clave debe empezar por sk-ant-";
      claudeKeyError.style.display = "block"; return;
    }
    claudeKeySave.disabled = true;
    try {
      const res  = await fetch("/api/assistant/set-claude-key", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      const data = await res.json();
      if (data.error) {
        claudeKeyError.textContent = data.error;
        claudeKeyError.style.display = "block"; return;
      }
      hasClaudeKey = true;
      claudeModal.style.display = "none";
      if (pendingClaudeModel) {
        const m = pendingClaudeModel; pendingClaudeModel = null;
        await loadModels();
        modelSel.value = m;
        localStorage.setItem("pdm-assistant-model", m);
      }
    } catch (e) {
      claudeKeyError.textContent = "Error de red: " + e.message;
      claudeKeyError.style.display = "block";
    } finally { claudeKeySave.disabled = false; }
  });

  claudeKeyInput.addEventListener("keydown", e => { if (e.key === "Enter") claudeKeySave.click(); });

  // ── Toggle del drawer ──────────────────────────────────────────────────────

  function openDrawer()  { drawer.classList.remove("collapsed"); input.focus(); }
  function closeDrawer() { drawer.classList.add("collapsed"); }

  function clearChat() {
    conversationHistory = [];
    messages.innerHTML = "";
  }

  fab.addEventListener("click", () => {
    drawer.classList.contains("collapsed") ? openDrawer() : closeDrawer();
  });
  closeBtn.addEventListener("click", closeDrawer);
  newChatBtn.addEventListener("click", clearChat);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !drawer.classList.contains("collapsed")) closeDrawer();
  });

  // ── Estado del sistema ─────────────────────────────────────────────────────

  async function checkStatus() {
    try {
      const res  = await fetch("/api/assistant/status");
      const data = await res.json();
      if (data.ollama_ready && data.chroma_ready) {
        statusDot.className = "status-dot ok";
        const total = data.indexed_pdfs + data.indexed_grimoire;
        statusDot.title = `Listo · ${total.toLocaleString()} chunks indexados`;
      } else if (data.ollama_ready) {
        statusDot.className = "status-dot warn";
        statusDot.title = "Ollama OK · Base de conocimiento vacía (indexado pendiente)";
      } else {
        statusDot.className = "status-dot err";
        statusDot.title = "Ollama no disponible";
      }
    } catch {
      statusDot.className = "status-dot err";
      statusDot.title = "Error al comprobar el estado";
    }
  }

  checkStatus();
  setInterval(checkStatus, 30_000);

  // ── Renderizado de mensajes ────────────────────────────────────────────────

  function addMessage(role, text = "") {
    const div = document.createElement("div");
    div.className = `assistant-msg ${role}`;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addSources(sources, parentMsg) {
    if (!sources || sources.length === 0) return;
    const div = document.createElement("div");
    div.className = "assistant-sources";
    sources.forEach((s) => {
      const page = s.page ? ` · pág. ${s.page}` : "";
      const text = `📖 ${s.label}${page}`;
      if (s.viewer_url) {
        const a = document.createElement("a");
        a.href = s.viewer_url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = text;
        div.appendChild(a);
      } else {
        const span = document.createElement("span");
        span.textContent = text;
        div.appendChild(span);
      }
    });
    parentMsg.appendChild(div);
  }

  // ── Detección y guardado de fichas markdown ────────────────────────────────

  function extractMarkdownBlock(text) {
    // Detecta ```markdown, ```yaml o ``` con frontmatter YAML (---)
    const fenced = text.match(/```(?:markdown|yaml)?\s*\n(---[\s\S]+?---[\s\S]*?)```/);
    if (fenced) return fenced[1].trim();
    return null;
  }

  function slugFromContent(content) {
    const m = content.match(/^---[\s\S]*?nombre:\s*(.+)/m)
           || content.match(/^---[\s\S]*?title:\s*(.+)/m)
           || content.match(/^#\s+(.+)/m);
    if (!m) return "";
    return m[1].trim()
      .toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "_");
  }

  function slugFromQuery(query) {
    const prefixes = ["hechizo ", "conjuro ", "monstruo ", "criatura ", "npc ", "raza ", "objeto ", "arma "];
    let name = query.toLowerCase().trim();
    for (const p of prefixes) {
      if (name.startsWith(p)) { name = name.slice(p.length); break; }
    }
    return name
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "_")
      .slice(0, 60);
  }

  function detectTypeFromQuery(query) {
    const q = query.toLowerCase().trim();
    if (/^(hechizo|conjuro|spell)\b/.test(q)) return "spell";
    if (/^(monstruo|criatura|npc|bestia|monster|raza)\b/.test(q)) return "monster";
    return "rule";
  }

  // rawMode=true: content es texto plano; se genera frontmatter b\u00e1sico al guardar
  function addSavePanel(content, parentMsg, query = "", rawMode = false) {
    const autoType = detectTypeFromQuery(query);
    const slug = rawMode ? slugFromQuery(query) : slugFromContent(content);
    const panel = document.createElement("div");
    panel.className = "assistant-save-panel";
    panel.innerHTML = `
      <div class="assistant-save-title">💾 Guardar en el grimorio</div>
      <div class="assistant-save-row">
        <select class="assistant-save-type">
          <option value="spell"   ${autoType==="spell"   ?"selected":""}>${TYPE_LABELS.spell}</option>
          <option value="monster" ${autoType==="monster" ?"selected":""}>${TYPE_LABELS.monster}</option>
          <option value="rule"    ${autoType==="rule"    ?"selected":""}>${TYPE_LABELS.rule}</option>
        </select>
        <input class="assistant-save-name" type="text" placeholder="nombre_del_fichero" value="${slug}" spellcheck="false" />
        <button class="assistant-save-btn">Guardar</button>
      </div>
      <div class="assistant-save-feedback"></div>
    `;
    const btn      = panel.querySelector(".assistant-save-btn");
    const nameInp  = panel.querySelector(".assistant-save-name");
    const typeInp  = panel.querySelector(".assistant-save-type");
    const feedback = panel.querySelector(".assistant-save-feedback");

    btn.addEventListener("click", async () => {
      const name     = nameInp.value.trim();
      const fileType = typeInp.value;
      if (!name) { feedback.textContent = "Introduce un nombre."; return; }
      btn.disabled = true;
      feedback.textContent = "Guardando…";

      let finalContent = content;
      if (rawMode) {
        const displayName = name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        finalContent = `---\nnombre: "${displayName}"\ntipo: "${fileType}"\n---\n\n${content}`;
      }

      try {
        const res  = await fetch("/api/assistant/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: finalContent, file_type: fileType, name }),
        });
        const data = await res.json();
        if (data.ok) {
          feedback.className = "assistant-save-feedback ok";
          feedback.textContent = `✓ Guardado como ${data.slug}.md · indexando en background…`;
          btn.disabled = true;
          nameInp.disabled = true;
          typeInp.disabled = true;
        } else {
          feedback.className = "assistant-save-feedback err";
          feedback.textContent = `✗ ${data.error}`;
          btn.disabled = false;
        }
      } catch (e) {
        feedback.className = "assistant-save-feedback err";
        feedback.textContent = `✗ ${e.message}`;
        btn.disabled = false;
      }
    });

    parentMsg.appendChild(panel);
  }

  // ── Contexto del juego ─────────────────────────────────────────────────────

  function getGameContext() {
    try {
      const turnEl  = document.getElementById("currentTurnName");
      const roundEl = document.getElementById("roundNumber");
      const charEls = document.querySelectorAll(".char-name");
      const context = {};
      if (turnEl  && turnEl.textContent.trim())  context.current_turn = turnEl.textContent.trim();
      if (roundEl && roundEl.textContent.trim())  context.round = parseInt(roundEl.textContent.trim()) || undefined;
      if (charEls.length > 0) {
        context.characters = Array.from(charEls).map((el) => el.textContent.trim()).filter(Boolean);
      }
      return Object.keys(context).length > 0 ? context : null;
    } catch {
      return null;
    }
  }

  // ── Envío de consulta ──────────────────────────────────────────────────────

  async function sendQuery() {
    const query = input.value.trim();
    if (!query) return;
    if (!isModelUsable(modelSel.value)) {
      modelHint.style.display = "block";
      return;
    }

    input.value = "";
    input.style.height = "";
    sendBtn.disabled = true;

    addMessage("user", query);
    const assistantMsg = addMessage("assistant thinking");

    try {
      const res = await fetch("/api/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          model: modelSel.value,
          game_context: getGameContext(),
          history: conversationHistory,
        }),
      });

      if (!res.ok) {
        assistantMsg.className = "assistant-msg error";
        assistantMsg.textContent = `Error ${res.status}: ${res.statusText}`;
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      assistantMsg.textContent = "";
      assistantMsg.className = "assistant-msg assistant thinking";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let payload;
          try {
            payload = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (payload.error) {
            assistantMsg.className = "assistant-msg error";
            assistantMsg.textContent = `⚠ ${payload.error}`;
            return;
          }

          if (payload.status === "searching") {
            const sys = payload.system ? ` [${payload.system}]` : "";
            assistantMsg.textContent = `🔍 Buscando en la biblioteca${sys}…`;
            continue;
          }
          if (payload.status === "generating") {
            assistantMsg.textContent = "";
            assistantMsg.className = "assistant-msg assistant thinking";
            fullText = "";
            continue;
          }

          if (payload.token) {
            fullText += payload.token;
            assistantMsg.textContent = fullText;
            messages.scrollTop = messages.scrollHeight;
          }

          if (payload.done) {
            assistantMsg.classList.remove("thinking");
            addSources(payload.sources, assistantMsg);
            const mdBlock = extractMarkdownBlock(fullText);
            if (mdBlock) {
              addSavePanel(mdBlock, assistantMsg, query);
            } else if (fullText.length > 100) {
              addSavePanel(fullText, assistantMsg, query, true);
            }
            // Guardar intercambio en historial (máx. 3 turnos = 6 mensajes)
            conversationHistory.push({ role: "user",      content: query });
            conversationHistory.push({ role: "assistant", content: fullText.slice(0, 400) });
            if (conversationHistory.length > 6) conversationHistory.splice(0, 2);
            messages.scrollTop = messages.scrollHeight;
          }
        }
      }

      assistantMsg.classList.remove("thinking");

    } catch (err) {
      assistantMsg.className = "assistant-msg error";
      assistantMsg.textContent = `⚠ ${err.message}`;
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // ── Modal de importación desde biblioteca RAG ──────────────────────────────

  const ragModal      = document.getElementById("ragImportModal");
  const ragClose      = document.getElementById("ragImportClose");
  const ragTitle      = document.getElementById("ragImportTitle");
  const ragQueryInput = document.getElementById("ragImportQuery");
  const ragSearchBtn  = document.getElementById("ragImportSearchBtn");
  const ragResponse   = document.getElementById("ragImportResponse");

  let ragImportType = "monster";

  const IMPORT_PROMPTS = {
    monster: (name) =>
      `Busca en el contexto el stat block o ficha de "${name}" y transcríbelo completo. ` +
      `Si encuentras sus estadísticas, ponlas EXACTAMENTE en un bloque que empiece con \`\`\`markdown y termine con \`\`\`, ` +
      `con frontmatter YAML (---) con los campos: nombre, tipo, ca/armor_class, pg/hp, movimiento, ataques, daño, y descripción breve. ` +
      `Usa SOLO datos del contexto proporcionado, no inventes estadísticas.`,
    rule: (name) =>
      `Busca en el contexto la regla "${name}" y transcríbela completa. ` +
      `Pon el resultado en un bloque que empiece con \`\`\`markdown y termine con \`\`\`, ` +
      `con frontmatter YAML (---) con los campos: nombre, categoría, y el contenido de la regla. ` +
      `Usa SOLO datos del contexto proporcionado.`,
  };

  const IMPORT_TITLES = {
    monster: `📥 Importar ${TYPE_LABELS.monster} de biblioteca`,
    rule:    `📥 Importar ${TYPE_LABELS.rules || "Regla"} de biblioteca`,
  };

  function openRagImportModal(type) {
    ragImportType = type;
    ragTitle.textContent = IMPORT_TITLES[type] || "📥 Importar de biblioteca";
    ragQueryInput.value = "";
    ragQueryInput.placeholder = type === "monster"
      ? `Nombre del ${TYPE_LABELS.monster?.toLowerCase() || "monstruo"}…`
      : `Nombre de la regla…`;
    ragResponse.innerHTML = "";
    ragSearchBtn.disabled = false;
    ragModal.style.display = "flex";
    setTimeout(() => ragQueryInput.focus(), 50);
  }

  function closeRagImportModal() {
    ragModal.style.display = "none";
  }

  ragClose.addEventListener("click", closeRagImportModal);
  ragModal.addEventListener("click", (e) => { if (e.target === ragModal) closeRagImportModal(); });

  document.querySelectorAll(".btn-import-rag").forEach((btn) => {
    btn.addEventListener("click", () => openRagImportModal(btn.dataset.importType));
  });

  async function runRagImport() {
    const name = ragQueryInput.value.trim();
    if (!name) return;

    const prompt = (IMPORT_PROMPTS[ragImportType] || IMPORT_PROMPTS.monster)(name);

    ragSearchBtn.disabled = true;
    ragResponse.innerHTML = "";

    const statusEl = document.createElement("div");
    statusEl.className = "assistant-msg assistant thinking";
    statusEl.textContent = "🔍 Buscando en la biblioteca…";
    ragResponse.appendChild(statusEl);

    try {
      const res = await fetch("/api/assistant/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, item_type: ragImportType }),
      });

      if (!res.ok) {
        statusEl.className = "assistant-msg error";
        statusEl.textContent = `Error ${res.status}: ${res.statusText}`;
        ragSearchBtn.disabled = false;
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "", fullText = "";

      statusEl.textContent = "";
      statusEl.className = "assistant-msg assistant thinking";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let payload;
          try { payload = JSON.parse(line.slice(6)); } catch { continue; }

          if (payload.error) {
            statusEl.className = "assistant-msg error";
            statusEl.textContent = `⚠ ${payload.error}`;
            ragSearchBtn.disabled = false;
            return;
          }
          if (payload.status === "searching") {
            statusEl.textContent = `🔍 Buscando en la biblioteca…`;
            continue;
          }
          if (payload.status === "generating") {
            statusEl.textContent = "";
            statusEl.className = "assistant-msg assistant thinking";
            fullText = "";
            continue;
          }
          if (payload.token) {
            fullText += payload.token;
            statusEl.textContent = fullText;
            ragResponse.scrollTop = ragResponse.scrollHeight;
          }
          if (payload.done) {
            statusEl.classList.remove("thinking");
            addSources(payload.sources, statusEl);
            const mdBlock = extractMarkdownBlock(fullText);
            if (mdBlock) {
              const savePanel = document.createElement("div");
              ragResponse.appendChild(savePanel);
              // Reutiliza addSavePanel pero preselecciona el tipo correcto
              const fakeParent = { appendChild: (el) => ragResponse.appendChild(el) };
              const panel = buildSavePanel(mdBlock, ragImportType);
              ragResponse.appendChild(panel);
            }
            ragSearchBtn.disabled = false;
          }
        }
      }
      statusEl.classList.remove("thinking");
    } catch (err) {
      statusEl.className = "assistant-msg error";
      statusEl.textContent = `⚠ ${err.message}`;
      ragSearchBtn.disabled = false;
    }
  }

  // buildSavePanel: igual que addSavePanel pero devuelve el elemento y preselecciona tipo
  function buildSavePanel(content, defaultType) {
    const slug = slugFromContent(content);
    const panel = document.createElement("div");
    panel.className = "assistant-save-panel";
    panel.innerHTML = `
      <div class="assistant-save-title">💾 Guardar en el grimorio</div>
      <div class="assistant-save-row">
        <select class="assistant-save-type">
          <option value="monster" ${defaultType === "monster" ? "selected" : ""}>${TYPE_LABELS.monster}</option>
          <option value="spell"   ${defaultType === "spell"   ? "selected" : ""}>${TYPE_LABELS.spell}</option>
          <option value="rule"    ${defaultType === "rule"    ? "selected" : ""}>${TYPE_LABELS.rules || "Regla"}</option>
        </select>
        <input class="assistant-save-name" type="text" placeholder="nombre_fichero" value="${slug}" spellcheck="false">
        <button class="assistant-save-btn">Guardar</button>
      </div>
      <div class="assistant-save-feedback"></div>
    `;
    const btn      = panel.querySelector(".assistant-save-btn");
    const nameInp  = panel.querySelector(".assistant-save-name");
    const typeInp  = panel.querySelector(".assistant-save-type");
    const feedback = panel.querySelector(".assistant-save-feedback");

    btn.addEventListener("click", async () => {
      const name     = nameInp.value.trim();
      const fileType = typeInp.value;
      if (!name) { feedback.textContent = "Introduce un nombre."; return; }
      btn.disabled = true;
      feedback.textContent = "Guardando…";
      try {
        const res  = await fetch("/api/assistant/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, file_type: fileType, name }),
        });
        const data = await res.json();
        if (data.ok) {
          feedback.className = "assistant-save-feedback ok";
          feedback.textContent = `✓ Guardado como ${data.slug}.md`;
          btn.disabled = true; nameInp.disabled = true; typeInp.disabled = true;
        } else {
          feedback.className = "assistant-save-feedback err";
          feedback.textContent = `✗ ${data.error}`;
          btn.disabled = false;
        }
      } catch (e) {
        feedback.className = "assistant-save-feedback err";
        feedback.textContent = `✗ ${e.message}`;
        btn.disabled = false;
      }
    });
    return panel;
  }

  ragSearchBtn.addEventListener("click", runRagImport);
  ragQueryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runRagImport();
  });

  // ── Eventos de input ───────────────────────────────────────────────────────

  sendBtn.addEventListener("click", sendQuery);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  });

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 150) + "px";
  });

})();
