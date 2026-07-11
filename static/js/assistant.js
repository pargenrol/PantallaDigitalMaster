/**
 * Asistente IA — Pantallasistemas
 * Drawer lateral de chat con RAG via SSE.
 * El filtro de sistema se aplica automáticamente en el servidor
 * según el sistema activo en sesión.
 */

(function () {
  "use strict";

  const fab       = document.getElementById("assistant-fab");
  const drawer    = document.getElementById("assistant-drawer");
  const closeBtn  = document.getElementById("assistant-close");
  const messages  = document.getElementById("assistant-messages");
  const input     = document.getElementById("assistant-input");
  const sendBtn   = document.getElementById("assistant-send");
  const statusDot = document.getElementById("assistant-status-dot");
  const sysLabel  = document.getElementById("assistant-system-label");

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

  // ── Toggle del drawer ──────────────────────────────────────────────────────

  function openDrawer()  { drawer.classList.remove("collapsed"); input.focus(); }
  function closeDrawer() { drawer.classList.add("collapsed"); }

  fab.addEventListener("click", () => {
    drawer.classList.contains("collapsed") ? openDrawer() : closeDrawer();
  });
  closeBtn.addEventListener("click", closeDrawer);

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
    // Intenta extraer el nombre del frontmatter
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

  function addSavePanel(content, parentMsg) {
    const slug = slugFromContent(content);
    const panel = document.createElement("div");
    panel.className = "assistant-save-panel";
    panel.innerHTML = `
      <div class="assistant-save-title">💾 Guardar ficha en el grimorio</div>
      <div class="assistant-save-row">
        <select class="assistant-save-type">
          <option value="monster">${TYPE_LABELS.monster}</option>
          <option value="spell">${TYPE_LABELS.spell}</option>
          <option value="rule">${TYPE_LABELS.rule}</option>
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
      try {
        const res  = await fetch("/api/assistant/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, file_type: fileType, name }),
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
          game_context: getGameContext(),
          // filter_system se aplica automáticamente en el servidor (sesión activa)
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
            if (mdBlock) addSavePanel(mdBlock, assistantMsg);
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
