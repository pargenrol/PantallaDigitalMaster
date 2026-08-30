"""
Blueprint del asistente IA con RAG.

Rutas:
  GET  /api/assistant/status        — estado de Ollama y ChromaDB
  GET  /api/assistant/models        — modelos disponibles (Ollama + Claude)
  POST /api/assistant/set-claude-key — guarda la API key de Anthropic
  POST /api/assistant/query         — consulta con respuesta SSE en streaming

El sistema activo (session["active_system"]) se usa automáticamente para
acotar la búsqueda RAG al filtro de PDFs correspondiente (rag_pdf_filter).
"""

import json
import os
import queue
import re
import threading
import urllib.request
import urllib.error
from pathlib import Path
from flask import Blueprint, request, Response, current_app, jsonify, session

import ollama as _ollama

from utils.rag_retriever import retrieve, build_prompt, format_sources, status, get_system_prompt, CHAT_MODEL, OLLAMA_URL, retrieve_by_name, PRIORITY_SOURCES, _ADND_SYSTEMS
from utils.assistant_memory import load_memory, add_entry, delete_entry, clear_memory, format_memory_for_prompt
from systems.registry import get_system, DEFAULT_SYSTEM

bp = Blueprint("api_assistant", __name__, url_prefix="/api/assistant")

CLAUDE_MODELS = [
    {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (rápido)"},
    {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (preciso)"},
]

RECOMMENDED_OLLAMA_MODELS = [
    {"id": "qwen2.5:7b-instruct-q4_K_M", "label": "Qwen 2.5 7B", "note": "Recomendado, equilibrado", "size_gb": 4.7},
    {"id": "qwen2.5:3b-instruct", "label": "Qwen 2.5 3B", "note": "Más rápido, equipos modestos", "size_gb": 2.0},
    {"id": "llama3.1:8b-instruct-q4_K_M", "label": "Llama 3.1 8B", "note": "Alternativa", "size_gb": 4.9},
]


def _add_viewer_urls(sources: list[dict], biblioteca_url: str) -> list[dict]:
    """Añade viewer_url a las fuentes de tipo PDF para enlazar a rol-biblioteca."""
    from urllib.parse import quote
    biblioteca_url = biblioteca_url.rstrip("/")
    if not biblioteca_url:
        return sources
    for s in sources:
        if s.get("type") == "pdf" and s.get("source_path"):
            encoded = quote(s["source_path"], safe="/")
            url = f"{biblioteca_url}/viewer/{encoded}"
            if s.get("page"):
                url += f"?page={s['page']}"
            s["viewer_url"] = url
    return sources


@bp.get("/status")
def assistant_status():
    return jsonify(status())


@bp.get("/models")
def assistant_models():
    ollama_models = []
    try:
        for m in _ollama.list().models:
            name = m.model
            if "embed" in name.lower():
                continue
            ollama_models.append({"id": name, "label": name, "type": "ollama"})
    except Exception:
        pass
    claude = [{"id": m["id"], "label": m["label"], "type": "claude"} for m in CLAUDE_MODELS]
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return jsonify({"ollama": ollama_models, "claude": claude, "has_claude_key": has_key})


@bp.post("/set-claude-key")
def set_claude_key():
    data = request.get_json(force=True)
    key = (data.get("key") or "").strip()
    if not key.startswith("sk-ant-"):
        return jsonify({"error": "Clave inválida (debe empezar por sk-ant-)"}), 400
    os.environ["ANTHROPIC_API_KEY"] = key
    env_file = os.path.join(current_app.root_path, ".env")
    lines = []
    if os.path.exists(env_file):
        lines = [l for l in open(env_file) if not l.startswith("ANTHROPIC_API_KEY")]
    lines.append(f"ANTHROPIC_API_KEY={key}\n")
    open(env_file, "w").writelines(lines)
    return jsonify({"ok": True})


@bp.post("/test-claude-key")
def test_claude_key():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"ok": False, "error": "No hay clave configurada"}), 400
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        client.models.list(limit=1)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@bp.get("/ollama/recommended")
def ollama_recommended():
    instalados = set()
    try:
        for m in _ollama.list().models:
            instalados.add(m.model)
    except Exception:
        pass
    modelos = [{**m, "installed": m["id"] in instalados} for m in RECOMMENDED_OLLAMA_MODELS]
    return jsonify(modelos)


@bp.post("/ollama/pull")
def ollama_pull():
    data = request.get_json(force=True)
    model = (data.get("model") or "").strip()
    if not model:
        return jsonify({"error": "model requerido"}), 400

    def generate():
        try:
            for chunk in _ollama.pull(model, stream=True):
                payload = {"status": chunk.status}
                if chunk.completed and chunk.total:
                    payload["percent"] = round(chunk.completed / chunk.total * 100, 1)
                yield f"data: {json.dumps(payload)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@bp.post("/query")
def assistant_query():
    """
    Recibe una pregunta del máster y responde con SSE streaming.

    Body JSON:
      query         (str, requerido)  — la pregunta
      game_context  (dict, opcional)  — {current_turn, round, characters: [...]}
      k             (int, opcional)   — número de chunks a recuperar (default: RAG_K)

    El filter_system se obtiene automáticamente del sistema activo en sesión.
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query requerida"}), 400

    selected_model = (data.get("model") or CHAT_MODEL).strip()
    use_claude = selected_model.startswith("claude")
    game_context = data.get("game_context")
    k = int(data.get("k") or current_app.config.get("RAG_K", 3))
    history = data.get("history") or []  # [{role, content}, ...]

    # Filtro automático por sistema activo en sesión
    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    system_id = system.get("id", "agnostico")
    filter_system = system.get("rag_pdf_filter")  # None = sin filtro (agnóstico)
    filter_source = system.get("rag_source_filter")  # sub-filtro por ruta de fuente
    assistant_name = system.get("assistant_name", "Asistente IA")
    system_prompt = get_system_prompt(system.get("id"), assistant_name=assistant_name)

    # Detección de comandos de memorización (antes de llamar a Ollama)
    _MEMORY_PREFIXES = ("recuerda que ", "recuerda: ", "memoriza: ")
    query_lower = query.lower()
    _matched_prefix = next((p for p in _MEMORY_PREFIXES if query_lower.startswith(p)), None)
    if _matched_prefix:
        text_to_save = query[len(_matched_prefix):].strip()

        def _generate_memorized():
            entry = add_entry(system_id, text_to_save)
            yield f"data: {json.dumps({'status': 'memorized', 'text': entry['text'], 'id': entry['id']})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return Response(_generate_memorized(), mimetype="text/event-stream",
                        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    # Cargar bloque de memoria para inyectar en el prompt
    memory_block = format_memory_for_prompt(system_id, assistant_name)

    # Cargar contexto de campaña fijada (nota o carpeta)
    campaign_block = ""
    campaign_path = session.get("campaign_pin_path") or session.get("campaign_note_path")
    campaign_type = session.get("campaign_pin_type", "note")
    campaign_name = session.get("campaign_pin_name") or session.get("campaign_note_name", "")
    if campaign_path:
        try:
            import frontmatter as _fm
            if campaign_type == "folder" and os.path.isdir(campaign_path):
                from routes.api_campaigns import _load_folder_content
                content = _load_folder_content(campaign_path, max_chars=600)
                campaign_block = f"[NOTAS DE CAMPAÑA: {campaign_name}]\n{content}"
            elif os.path.isfile(campaign_path):
                with open(campaign_path, "r", encoding="utf-8") as _f:
                    _post = _fm.load(_f)
                campaign_block = f"[NOTA DE CAMPAÑA: {campaign_name}]\n{_post.content[:600]}"
        except Exception:
            campaign_block = ""

    # Derivar la URL de la biblioteca del mismo host desde el que llega la petición
    # para que el enlace funcione tanto en local como vía Tailscale o red local
    _cfg_url = current_app.config.get("BIBLIOTECA_URL", "http://localhost:8765")
    _req_host = request.host.split(":")[0]
    biblioteca_url = f"http://{_req_host}:8765"
    # Solo usar la config si el admin definió una URL explícita que no sea localhost
    if "localhost" not in _cfg_url and "127.0.0.1" not in _cfg_url:
        biblioteca_url = _cfg_url

    def generate():
        import time as _t
        _t0 = _t.time()

        # 1. Avisar al cliente que estamos buscando
        yield f"data: {json.dumps({'status': 'searching', 'system': system['short_name'], 'assistant': assistant_name})}\n\n"

        # 2. Recuperar chunks relevantes (semántico + textual si es búsqueda de nombre)
        try:
            priority_sources = PRIORITY_SOURCES.get(system_id)
            also_core_adnd = system_id in _ADND_SYSTEMS
            chunks = retrieve(query, k=k, filter_system=filter_system, filter_source=filter_source, priority_sources=priority_sources, also_core_adnd=also_core_adnd)

            # Búsqueda textual complementaria cuando la consulta parece un nombre de hechizo/monstruo
            _LOOKUP_PREFIXES = ("hechizo ", "conjuro ", "monstruo ", "criatura ", "raza ", "objeto ", "arma ")
            _q_lower = query.lower().strip()
            _lookup_name = None
            for _pfx in _LOOKUP_PREFIXES:
                if _q_lower.startswith(_pfx):
                    _lookup_name = query[len(_pfx):].strip()
                    break
            # También si la consulta es corta (≤5 palabras) y no contiene signos de pregunta → probable nombre
            if not _lookup_name and len(query.split()) <= 5 and "?" not in query:
                _lookup_name = query.strip()

            if _lookup_name:
                try:
                    name_chunks = retrieve_by_name(_lookup_name, filter_system=filter_system, filter_source=filter_source, k=3)
                    # Añadir chunks de texto que no estén ya en los semánticos
                    existing_texts = {c["text"] for c in chunks}
                    for nc in name_chunks:
                        if nc["text"] not in existing_texts:
                            chunks.insert(0, nc)
                            existing_texts.add(nc["text"])
                    chunks = chunks[:4]  # máximo 4 chunks en total
                except Exception:
                    pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        _t1 = _t.time()
        print(f"[TIMING] retrieve: {_t1-_t0:.1f}s chunks={len(chunks)}", flush=True)

        # 3. Avisar que empieza la generación
        yield f"data: {json.dumps({'status': 'generating'})}\n\n"

        # 4. Construir prompt (con bloque de memoria y contexto de campaña)
        prompt = build_prompt(query, chunks, game_context, active_system=system.get("name"), memory_block=memory_block, campaign_block=campaign_block)
        print(f"[TIMING] prompt={len(prompt)} chars / ~{len(prompt)//4} tokens. campaign_block={len(campaign_block)} chars", flush=True)

        # 5. Construir lista de mensajes con historial
        messages_payload = [{"role": "system", "content": system_prompt}]
        for h in (history or [])[-6:]:
            role = h.get("role", "")
            content = str(h.get("content", ""))[:400]
            if role in ("user", "assistant") and content:
                messages_payload.append({"role": role, "content": content})
        messages_payload.append({"role": "user", "content": prompt})

        sources = _add_viewer_urls(format_sources(chunks), biblioteca_url)

        # 6. Llamar al LLM (Claude vía SDK o Ollama vía HTTP)
        if use_claude:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                yield f"data: {json.dumps({'error': 'No hay ANTHROPIC_API_KEY configurada.'})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
                return

            q = queue.Queue()

            def _run_claude():
                try:
                    import anthropic
                    client_ai = anthropic.Anthropic(api_key=api_key)
                    claude_msgs = [m for m in messages_payload if m["role"] != "system"]
                    system_txt  = next((m["content"] for m in messages_payload if m["role"] == "system"), "")
                    with client_ai.messages.stream(
                        model=selected_model, max_tokens=1024,
                        system=system_txt, messages=claude_msgs,
                    ) as stream:
                        _first = True
                        for text in stream.text_stream:
                            if text:
                                if _first:
                                    print(f"[TIMING] primer token Claude: {_t.time()-_t0:.1f}s", flush=True)
                                    _first = False
                                q.put(("token", text))
                    q.put(("done", None))
                except Exception as e:
                    q.put(("error", str(e)))

            threading.Thread(target=_run_claude, daemon=True).start()
            while True:
                try:
                    kind, val = q.get(timeout=20)
                    if kind == "token":
                        yield f"data: {json.dumps({'token': val})}\n\n"
                    elif kind == "done":
                        print(f"[TIMING] done Claude: {_t.time()-_t0:.1f}s", flush=True)
                        break
                    else:
                        yield f"data: {json.dumps({'error': val})}\n\n"
                        break
                except queue.Empty:
                    yield ": keepalive\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

        else:
            payload = json.dumps({
                "model": selected_model,
                "messages": messages_payload,
                "stream": True,
                "keep_alive": "5m",
                "options": {
                    "num_predict": 350,
                    "temperature": 0.3,
                },
            }).encode()

            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                _first_token = True
                with urllib.request.urlopen(req, timeout=300) as resp:
                    for line in resp:
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line.decode("utf-8"))
                        except json.JSONDecodeError:
                            continue

                        token = chunk_data.get("message", {}).get("content", "")
                        if token:
                            if _first_token:
                                print(f"[TIMING] primer token: {_t.time()-_t0:.1f}s total", flush=True)
                                _first_token = False
                            yield f"data: {json.dumps({'token': token})}\n\n"

                        if chunk_data.get("done"):
                            print(f"[TIMING] done: {_t.time()-_t0:.1f}s total | prompt_eval={chunk_data.get('prompt_eval_count')} tok eval_count={chunk_data.get('eval_count')} tok", flush=True)
                            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
                            return

            except urllib.error.URLError as e:
                yield f"data: {json.dumps({'error': f'Ollama no disponible: {e.reason}'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------
# Endpoints de gestión de memoria persistente
# ---------------------------------------------------------------------------

def _current_system_id() -> tuple[str, str]:
    """Devuelve (system_id, assistant_name) del sistema activo en sesión."""
    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    return system.get("id", "agnostico"), system.get("assistant_name", "Asistente IA")


@bp.get("/memory")
def memory_get():
    """Devuelve todas las entradas de memoria del sistema activo."""
    system_id, assistant_name = _current_system_id()
    entries = load_memory(system_id)
    return jsonify({"entries": entries, "system_id": system_id, "assistant_name": assistant_name})


@bp.post("/memory")
def memory_add():
    """Añade una nueva entrada a la memoria del sistema activo."""
    system_id, _ = _current_system_id()
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text requerido"}), 400
    entry_type = (data.get("type") or "nota").strip()
    entry = add_entry(system_id, text, entry_type)
    return jsonify(entry), 201


@bp.delete("/memory/<entry_id>")
def memory_delete_entry(entry_id: str):
    """Elimina una entrada de memoria por su id."""
    system_id, _ = _current_system_id()
    found = delete_entry(system_id, entry_id)
    if not found:
        return jsonify({"error": "entrada no encontrada"}), 404
    return jsonify({"ok": True})


@bp.delete("/memory")
def memory_clear():
    """Borra toda la memoria del sistema activo."""
    system_id, _ = _current_system_id()
    clear_memory(system_id)
    return jsonify({"ok": True})


@bp.post("/save")
def assistant_save():
    """
    Guarda contenido markdown generado por el asistente en la carpeta de recursos del sistema.

    Body JSON:
      content   (str)  — contenido markdown completo (con frontmatter)
      file_type (str)  — "monster", "spell" o "rule"
      name      (str)  — slug del fichero (sin .md)
    """
    data = request.get_json(silent=True) or {}
    content   = (data.get("content") or "").strip()
    file_type = (data.get("file_type") or "").strip()
    name      = (data.get("name") or "").strip()

    if not content or not file_type or not name:
        return jsonify({"error": "content, file_type y name son requeridos"}), 400

    # Sanitizar slug: solo letras, números, guiones y guiones bajos
    slug = re.sub(r"[^\w\-]", "_", name.lower()).strip("_")
    if not slug:
        return jsonify({"error": "nombre inválido"}), 400

    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    res = system.get("resources", {})

    type_map = {
        "monster": res.get("monsters"),
        "spell":   res.get("spells"),
        "rule":    res.get("rules"),
    }
    dir_path = type_map.get(file_type)
    if not dir_path:
        return jsonify({"error": f"tipo '{file_type}' no válido"}), 400

    target = Path(dir_path) / f"{slug}.md"
    if target.exists():
        return jsonify({"error": f"Ya existe '{slug}.md'. Usa un nombre diferente."}), 409

    # Validar que el frontmatter YAML es parseable antes de guardar
    try:
        import frontmatter as _fm
        _fm.loads(content)
    except Exception as e:
        return jsonify({"error": f"YAML inválido en el frontmatter: {e}"}), 400

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except Exception as e:
        return jsonify({"error": f"Error al guardar: {e}"}), 500

    # Indexar el nuevo fichero en el grimorio (en background)
    try:
        import threading
        from utils.rag_indexer import get_chroma_client, get_collection, COLLECTION_GRIMOIRE
        import frontmatter as fm

        def _index_new_file():
            import json as _json
            import urllib.request as _req
            from config import Config
            from utils.rag_indexer import chunk_text, embed, make_id
            try:
                post = fm.load(str(target))
                text = post.content.strip()
                nombre = post.metadata.get("nombre") or post.metadata.get("title") or slug
                if not text:
                    return
                chunks = chunk_text(text)
                client = get_chroma_client()
                col = get_collection(client, COLLECTION_GRIMOIRE)
                ids, embeddings, documents, metadatas = [], [], [], []
                for i, chunk in enumerate(chunks):
                    doc_id = make_id(f"grimoire/{file_type}/{slug}", 0, i)
                    emb = embed(chunk)
                    ids.append(doc_id)
                    embeddings.append(emb)
                    documents.append(chunk)
                    metadatas.append({
                        "source": f"grimoire/{file_type}/{slug}.md",
                        "type": file_type,
                        "slug": slug,
                        "name": nombre,
                        "system": system["id"],
                        "page": 0,
                        "chunk_index": i,
                    })
                if ids:
                    col.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
            except Exception as e:
                print(f"[assistant_save] Error indexando {slug}: {e}")

        threading.Thread(target=_index_new_file, daemon=True).start()
    except Exception:
        pass  # El guardado fue exitoso aunque falle el indexado

    return jsonify({
        "ok": True,
        "path": str(target.relative_to(Path(dir_path).parent.parent)),
        "slug": slug,
    })


@bp.post("/import")
def assistant_import():
    """
    Busca un monstruo o regla por nombre en los PDFs indexados (búsqueda textual)
    y genera una ficha markdown formateada para el sistema activo. SSE streaming.

    Body JSON:
      name      (str)  — nombre exacto a buscar
      item_type (str)  — "monster" o "rule"
    """
    data = request.get_json(silent=True) or {}
    name      = (data.get("name") or "").strip()
    item_type = (data.get("item_type") or "monster").strip()
    if not name:
        return jsonify({"error": "name requerido"}), 400

    system        = get_system(session.get("active_system", DEFAULT_SYSTEM))
    filter_system = system.get("rag_pdf_filter")
    filter_source = system.get("rag_source_filter")
    system_prompt = get_system_prompt(system.get("id"))

    # Esquema de campos del frontmatter que realmente reconoce
    # templates/content_detail.html para pintar el bloque de estadísticas.
    # adnd2e/greyhawk/forgotten_realms/ravenloft_adnd usan el esquema clásico
    # de AD&D2e (CA/THAC0/Dados de Golpe); el resto (dnd5e, darksun, mothership,
    # agnóstico...) usa el esquema hp/ac/challenge/xp de 5e.
    ADND2E_SIMPLE_SCHEMA_SYSTEMS = {"adnd2e", "greyhawk", "forgotten_realms", "ravenloft_adnd"}
    if system.get("id") in ADND2E_SIMPLE_SCHEMA_SYSTEMS:
        monster_prompt = (
            f'Busca en el contexto la entrada de "{name}" y extrae su stat block completo de AD&D 2ª edición. '
            f'Formatea el resultado en un bloque ```markdown con frontmatter YAML estrictamente válido (entre ---), '
            f'usando EXACTAMENTE estos campos y nombres (no inventes otros ni los traduzcas):\n'
            f'nombre, ca (Clase de Armadura, número), dg (Dados de Golpe, ej: "4+1", entre comillas), '
            f'thac0 (número), ataques (número), daño (ej: "1d8 / 1d6", entre comillas), '
            f'movimiento (metros, número), px (Puntos de Experiencia, número), alineamiento, '
            f'tamaño (P/M/G, una letra). '
            f'Después del frontmatter, añade un cuerpo con # Nombre y una descripción breve. '
            f'IMPORTANTE: dg y daño siempre entre comillas dobles; nunca incluyas texto sin comillas después de '
            f'un valor entre comillas (ejemplo correcto: daño: "1d8+2"; incorrecto: daño: "1d8" (espada)). '
            f'Si el contexto no contiene esa criatura, dilo claramente.'
        )
    else:
        monster_prompt = (
            f'Busca en el contexto la entrada de "{name}" y extrae su stat block completo. '
            f'Formatea el resultado en un bloque ```markdown con frontmatter YAML estrictamente válido (entre ---), '
            f'usando EXACTAMENTE estos campos y nombres: '
            f'nombre, type, size, alignment, hp (número), hp_roll (ej: "7d8+14", entre comillas), '
            f'ac (número), challenge (ej: "1/4"), xp (número), passive_perception (número), speed. '
            f'IMPORTANTE: todos los valores del frontmatter YAML deben ser strings entre comillas dobles '
            f'o números simples. Nunca incluyas texto sin comillas después de un valor entre comillas. '
            f'Ejemplo correcto: daño: "1d8+2"  Incorrecto: daño: "1d8" (espada) '
            f'Añade estadísticas, ataques, daño y una descripción breve en el cuerpo. '
            f'Si el contexto no contiene esa criatura, dilo claramente.'
        )

    TYPE_PROMPTS = {
        "monster": monster_prompt,
        "rule": (
            f'Busca en el contexto la regla "{name}" y transcríbela. '
            f'Formatea el resultado en un bloque ```markdown con frontmatter YAML estrictamente válido (entre ---). '
            f'IMPORTANTE: todos los valores del frontmatter YAML deben ser strings entre comillas dobles '
            f'o números simples. '
            f'Campos: nombre, categoría, y el texto completo de la regla en el cuerpo. '
            f'Si el contexto no contiene esa regla, dilo claramente.'
        ),
    }
    prompt = TYPE_PROMPTS.get(item_type, TYPE_PROMPTS["monster"])
    _cfg_url = current_app.config.get("BIBLIOTECA_URL", "http://localhost:8765")
    _req_host = request.host.split(":")[0]
    biblioteca_url = f"http://{_req_host}:8765"
    if "localhost" not in _cfg_url and "127.0.0.1" not in _cfg_url:
        biblioteca_url = _cfg_url

    def generate():
        yield f"data: {json.dumps({'status': 'searching'})}\n\n"

        # Búsqueda textual por nombre (más precisa para entidades concretas)
        try:
            chunks = retrieve_by_name(name, filter_system=filter_system, filter_source=filter_source, k=4)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        if not chunks:
            # Fallback a búsqueda semántica si la textual no da resultados
            try:
                chunks = retrieve(name, k=4, filter_system=filter_system, filter_source=filter_source)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

        yield f"data: {json.dumps({'status': 'generating', 'found': len(chunks)})}\n\n"

        full_prompt = build_prompt(prompt, chunks, active_system=system.get("name"))
        payload = json.dumps({
            "model": CHAT_MODEL,
            "system": system_prompt,
            "prompt": full_prompt,
            "stream": True,
            "keep_alive": "5m",
            "options": {"num_predict": 350, "temperature": 0.2},
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    if not line:
                        continue
                    try:
                        chunk_data = json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
                    token = chunk_data.get("response", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                    if chunk_data.get("done"):
                        sources = _add_viewer_urls(format_sources(chunks), biblioteca_url)
                        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
                        return
        except urllib.error.URLError as e:
            yield f"data: {json.dumps({'error': f'Ollama no disponible: {e.reason}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})
