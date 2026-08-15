"""
Módulo de recuperación RAG para el asistente IA.
Se importa en runtime por el blueprint api_assistant.
"""

import json
import os
import urllib.request
import urllib.error

import chromadb

from config import Config
from pathlib import Path

CHROMA_DIR   = Path(Config.CHROMA_DIR)
OLLAMA_URL   = Config.OLLAMA_URL
EMBED_MODEL  = Config.OLLAMA_EMBED_MODEL
CHAT_MODEL   = Config.OLLAMA_CHAT_MODEL
RAG_K        = Config.RAG_K


COLLECTION_PDFS     = "biblioteca_pdfs"
COLLECTION_GRIMOIRE = "grimoire_md"

# Libros core con prioridad en la búsqueda semántica (por ID de sistema)
_CORE_DND5E  = ["Manual del Jugador", "Guía del Dungeon Master", "Manual de Monstruos"]
_CORE_ADND2E = ["Manual del Jugador", "Guía del Dungeon Master", "Manual Monstruoso", "Compendio de Monstruos"]

PRIORITY_SOURCES = {
    "dnd5e":            _CORE_DND5E,
    "ravenloft":        _CORE_DND5E,
    "adnd2e":           _CORE_ADND2E,
    "darksun":          _CORE_ADND2E + ["Sol Oscuro", "Dark Sun"],
    "greyhawk":         _CORE_ADND2E + ["Greyhawk"],
    "ravenloft_adnd":   _CORE_ADND2E + ["Ravenloft", "Van Richten"],
    "forgotten_realms": _CORE_ADND2E + ["Forgotten Realms", "Vademécum"],
}

# Sistemas AD&D que necesitan incluir libros core de AD&D 2e en todas las búsquedas
_ADND_SYSTEMS = {"adnd2e", "darksun", "greyhawk", "ravenloft_adnd", "forgotten_realms"}

SYSTEM_PROMPT = (
    "Eres un asistente experto en juegos de rol de mesa (TTRPGs). "
    "Responde SIEMPRE en español, de forma concisa y práctica para uso en mesa. "
    "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. "
    "Si el contexto no contiene la información necesaria, dilo claramente "
    "en lugar de inventar datos. Cita el libro y página cuando sea relevante. "
    "Prioriza siempre las reglas y terminología del sistema de juego activo indicado en el contexto."
)

_FICHA_ADND = (
    "Cuando se te pida crear una ficha de monstruo, conjuro o regla para guardar, "
    "incluye el contenido completo dentro de un bloque de código markdown así:\n"
    "```markdown\n"
    "---\n"
    "nombre: Nombre del monstruo\n"
    "ca: 5\n"
    "dg: \"3+3\"\n"
    "thac0: 17\n"
    "ataques: 1\n"
    "daño: \"1d8\"\n"
    "movimiento: 9\n"
    "px: 175\n"
    "alineamiento: Caótico Malo\n"
    "---\n"
    "# Nombre\n\n"
    "Descripción y contenido...\n"
    "```\n"
    "Así el máster podrá guardarlo directamente en el bestiario."
)

SYSTEM_PROMPTS = {
    "adnd2e": (
        "Eres Gygax, asistente experto en Advanced Dungeons & Dragons 2ª Edición (AD&D 2e). "
        "Responde SIEMPRE en español, de forma concisa y práctica para uso en mesa. "
        "Usa terminología AD&D 2e: THAC0, CA (escala inversa, CA 10 sin armadura), DG (Dados de Golpe), "
        "PX (Puntos de Experiencia), tiradas de salvación (muerte, varita, petrificación, aliento, hechizo), "
        "alineamiento en 9 posiciones, clases originales (guerrero/mago/clérigo/ladrón y subclases). "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. " + _FICHA_ADND
    ),
    "darksun": (
        "Eres Boris, un antiguo templario de la ciudad-estado de Tiro que conoce los secretos de Athas. "
        "Hablas con brutalidad pragmática, sin adornos: en Athas la supervivencia es lo único que importa. "
        "Eres experto en Dark Sun (AD&D 2ª Edición ambientada en Athas). "
        "Responde SIEMPRE en español. Usa terminología AD&D 2e adaptada a Athas: THAC0, CA, DG, PX, "
        "psiónica (puntos psiónicos, disciplinas: telepatía/telequinesis/clarisenciencia/psicometabolismo/psicoportación), "
        "magia destructiva, defilers/preservers, señores-dragón, ciudades-estado. "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. "
        "Cuando se te pida crear una ficha, inclúyela en un bloque ```markdown con frontmatter YAML."
    ),
    "dnd5e": (
        "Eres Elminster, asistente experto en Dungeons & Dragons 5ª Edición. "
        "Responde SIEMPRE en español, de forma concisa y práctica para uso en mesa. "
        "Usa terminología D&D 5e: bonificador de competencia, tiradas de salvación por atributo, "
        "ventaja/desventaja, acciones/acciones adicionales/reacciones, FD (Fuerza de Dificultad). "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. "
        "Cuando se te pida crear una ficha, inclúyela en un bloque ```markdown con frontmatter YAML."
    ),
    "mothership": (
        "Eres ARIA, asistente experto en Mothership RPG 1e. "
        "Responde SIEMPRE en español. Usa terminología Mothership: "
        "Puntos de Casco, Estrés, pánico, dados de salvación (% basado en atributos), "
        "infestación/infección, módulos de nave, rol de Warden. "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. "
        "Cuando se te pida crear una ficha, inclúyela en un bloque ```markdown con frontmatter YAML."
    ),
    "ravenloft_adnd": (
        "Eres Van Richten, el más célebre cazador de monstruos de las Tierras de Bruma. "
        "Hablas con tono solemne y erudito, marcado por años de horror y pérdida. "
        "Conoces los dominios, los Señores Oscuros, los poderes de las tinieblas y las debilidades "
        "de cada criatura sobrenatural de Ravenloft en su versión original de AD&D 2ª Edición. "
        "Eres experto en Advanced Dungeons & Dragons 2ª Edición aplicado al horror gótico. "
        "Responde SIEMPRE en español. Usa terminología AD&D 2e: THAC0, CA (escala inversa), DG, PX, "
        "tiradas de salvación (muerte, varita, petrificación, aliento, hechizo). "
        "Conoces las mecánicas de poderes oscuros, chequeos de miedos y horrores, y los señores oscuros. "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. " + _FICHA_ADND
    ),
    "ravenloft": (
        "Eres Van Richten, el más célebre cazador de monstruos de las Tierras de Bruma. "
        "Hablas con tono solemne y erudito, marcado por años de horror y pérdida. "
        "Conoces los dominios, los Señores Oscuros, los poderes de las tinieblas y las debilidades "
        "de cada criatura sobrenatural de Ravenloft. "
        "Eres experto en D&D 5ª Edición aplicada al horror gótico. "
        "Responde SIEMPRE en español. Usa terminología D&D 5e: bonificador de competencia, "
        "tiradas de salvación por atributo, ventaja/desventaja, FD (Fuerza de Dificultad). "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. "
        "Cuando se te pida crear una ficha, inclúyela en un bloque ```markdown con frontmatter YAML."
    ),
    "greyhawk": (
        "Eres Mordenkainen, archmago del Círculo de los Ocho y guardián del equilibrio en los Flanaess. "
        "Hablas con autoridad académica y cierta condescendencia propia de quien conoce los secretos del mundo. "
        "Eres experto en Advanced Dungeons & Dragons 2ª Edición ambientado en el Mundo del Pasado (Greyhawk). "
        "Responde SIEMPRE en español. Usa terminología AD&D 2e: THAC0, CA, DG, PX, "
        "tiradas de salvación, alineamiento en 9 posiciones. "
        "Conoces la geografía de los Flanaess, las facciones, los grandes magos y las guerras de Greyhawk. "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. " + _FICHA_ADND
    ),
    "forgotten_realms": (
        "Eres Volo — Volothamp Geddarm —, el famoso cronista y viajero de los Reinos Olvidados. "
        "Hablas con entusiasmo desbordante, siempre con una anécdota de tus viajes por Faerûn. "
        "Eres experto en Advanced Dungeons & Dragons 2ª Edición ambientado en los Reinos Olvidados. "
        "Responde SIEMPRE en español. Usa terminología AD&D 2e: THAC0, CA, DG, PX, tiradas de salvación. "
        "Conoces bien Faerûn: sus ciudades (Waterdeep, Calimport, Silverymoon), facciones, panteón y geografía. "
        "Basa tus respuestas ÚNICAMENTE en el contexto proporcionado. Cita el libro y página. " + _FICHA_ADND
    ),
}


def get_system_prompt(system_id: str | None = None, assistant_name: str | None = None) -> str:
    """Devuelve el prompt de sistema específico para el juego activo.

    Si se pasa assistant_name, añade al final una instrucción para que el
    asistente responda de forma natural cuando el máster lo llame por su nombre.
    """
    prompt = SYSTEM_PROMPTS.get(system_id or "", SYSTEM_PROMPT)
    if assistant_name:
        prompt += f" Responde de forma natural cuando el máster te llame por tu nombre: {assistant_name}."
    return prompt

# Singleton: la conexión a ChromaDB se inicializa una sola vez
_client = None
_col_pdfs = None
_col_grimoire = None


def _get_collections():
    global _client, _col_pdfs, _col_grimoire
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            _col_pdfs = _client.get_collection(COLLECTION_PDFS)
        except Exception:
            _col_pdfs = None
        try:
            _col_grimoire = _client.get_collection(COLLECTION_GRIMOIRE)
        except Exception:
            _col_grimoire = None
    return _col_pdfs, _col_grimoire


def get_embedding(text: str) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


def retrieve(query: str, k: int = RAG_K, filter_system: str | None = None, filter_source: str | None = None, priority_sources: list[str] | None = None, also_core_adnd: bool = False) -> list[dict]:
    """
    Busca los k chunks más relevantes para la query.
    Busca primero en el grimorio (prioridad) y luego en los PDFs.
    filter_system: filtra por game_line en ChromaDB.
    filter_source: sub-filtro adicional por ruta de fuente (substring, aplicado en Python).
    Devuelve lista de dicts con: text, source, page, system, type (si es grimoire).
    """
    col_pdfs, col_grimoire = _get_collections()
    if col_pdfs is None and col_grimoire is None:
        return []

    try:
        query_emb = get_embedding(query)
    except Exception:
        return []

    results = []

    # Buscar en el grimorio (prioridad alta, k//2 + 1 resultados)
    if col_grimoire is not None:
        try:
            k_grimoire = max(2, k // 2 + 1)
            res = col_grimoire.query(
                query_embeddings=[query_emb],
                n_results=min(k_grimoire, col_grimoire.count()),
                include=["documents", "metadatas", "distances"],
            )
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                results.append({
                    "text": doc,
                    "source": meta.get("source", ""),
                    "page": meta.get("page", 0),
                    "system": meta.get("system", "grimoire"),
                    "type": meta.get("type", ""),
                    "name": meta.get("name", ""),
                    "distance": dist,
                    "collection": "grimoire",
                })
        except Exception:
            pass

    # Buscar en los PDFs
    if col_pdfs is not None:
        try:
            # Más candidatos si hay filtros post-query o prioridad de fuentes
            k_pdfs = k * 15 if filter_source else (k * 8 if (priority_sources or also_core_adnd) else k)
            where = {"game_line": {"$eq": filter_system}} if filter_system else None
            count = col_pdfs.count()
            if count > 0:
                res = col_pdfs.query(
                    query_embeddings=[query_emb],
                    n_results=min(k_pdfs, count),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
                for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                    source = meta.get("source", "")
                    if filter_source and filter_source not in source:
                        # Para settings AD&D: incluir también los libros core aunque no estén en la carpeta del setting
                        if not (also_core_adnd and "AD&D 2ª edición/Core" in source):
                            continue
                    results.append({
                        "text": doc,
                        "source": source,
                        "page": meta.get("page", 0),
                        "system": meta.get("system", ""),
                        "type": "",
                        "name": "",
                        "distance": dist,
                        "collection": "pdfs",
                    })
        except Exception:
            pass

        # Dark Sun y otros sistemas con game_line propio: búsqueda secundaria en libros core AD&D 2e
        if also_core_adnd and filter_system and filter_system != "adnd2e" and col_pdfs is not None:
            try:
                k_core = k * 4
                where_core = {"game_line": {"$eq": "adnd2e"}}
                res_core = col_pdfs.query(
                    query_embeddings=[query_emb],
                    n_results=min(k_core, col_pdfs.count()),
                    where=where_core,
                    include=["documents", "metadatas", "distances"],
                )
                for doc, meta, dist in zip(res_core["documents"][0], res_core["metadatas"][0], res_core["distances"][0]):
                    source = meta.get("source", "")
                    if "Core y Suplementos" not in source:
                        continue
                    results.append({
                        "text": doc,
                        "source": source,
                        "page": meta.get("page", 0),
                        "system": meta.get("system", ""),
                        "type": "",
                        "name": "",
                        "distance": dist,
                        "collection": "pdfs",
                    })
            except Exception:
                pass

    # Ordenar: libros core primero (si se indicaron), luego por distancia semántica
    if priority_sources:
        def _sort_key(r):
            is_prio = r["collection"] == "pdfs" and any(p in r["source"] for p in priority_sources)
            return (0 if is_prio else 1, r["distance"])
        results.sort(key=_sort_key)
    else:
        results.sort(key=lambda x: x["distance"])
    return results[:k]


def build_prompt(query: str, chunks: list[dict], game_context: dict | None = None, active_system: str | None = None, memory_block: str = "", campaign_block: str = "") -> str:
    """Construye el prompt completo para el LLM."""
    parts = []

    if active_system:
        parts.append(f"[SISTEMA DE JUEGO ACTIVO]\n{active_system}")

    if memory_block:
        parts.append(memory_block)

    if campaign_block:
        parts.append(campaign_block)

    if game_context:
        ctx_lines = []
        if game_context.get("current_turn"):
            ctx_lines.append(f"Turno activo: {game_context['current_turn']}")
        if game_context.get("round"):
            ctx_lines.append(f"Ronda: {game_context['round']}")
        if game_context.get("characters"):
            ctx_lines.append(f"Personajes en juego: {', '.join(game_context['characters'])}")
        if ctx_lines:
            parts.append("[CONTEXTO DEL JUEGO ACTUAL]\n" + "\n".join(ctx_lines))

    if chunks:
        fragment_lines = ["[FRAGMENTOS RELEVANTES DE LOS LIBROS]"]
        for chunk in chunks:
            src = chunk["source"]
            if chunk["collection"] == "grimoire" and chunk.get("name"):
                header = f"--- {chunk['name']} ({chunk['type']}) ---"
            elif chunk["page"]:
                header = f"--- {src} (pág. {chunk['page']}) ---"
            else:
                header = f"--- {src} ---"
            text = chunk["text"]
            if len(text) > 800:
                text = text[:800] + "…"
            fragment_lines.append(f"{header}\n{text}")
        parts.append("\n\n".join(fragment_lines))
    else:
        parts.append("[NOTA: No se encontraron fragmentos relevantes en la biblioteca indexada]")

    parts.append(f"[PREGUNTA DEL MÁSTER]\n{query}")
    return "\n\n".join(parts)


def retrieve_by_name(name: str, filter_system: str | None = None, filter_source: str | None = None, k: int = 4) -> list[dict]:
    """
    Búsqueda textual por nombre en los PDFs indexados.
    Prueba varias variantes de capitalización, recoge todos los matches y prioriza
    los chunks donde el nombre aparece como cabecera (stat blocks, entradas de reglas).

    Nota: NO usa where+where_document combinados en ChromaDB (bug que excluye resultados).
    El filtro de game_line se aplica en Python.
    """
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    except Exception:
        return []

    variants = list(dict.fromkeys([name.upper(), name.lower(), name, name.title()]))

    candidates = []
    seen_ids: set = set()

    for col_name, coll_type in [(COLLECTION_GRIMOIRE, "grimoire"), (COLLECTION_PDFS, "pdfs")]:
        try:
            col = client.get_collection(col_name)
            if col.count() == 0:
                continue
        except Exception:
            continue

        for variant in variants:
            try:
                res = col.get(
                    where_document={"$contains": variant},
                    include=["documents", "metadatas"],
                    limit=50,
                )
                for doc_id, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
                    if doc_id in seen_ids:
                        continue
                    # Filtro de sistema en Python (evita bug ChromaDB con where+where_document)
                    if filter_system and coll_type == "pdfs" and meta.get("game_line") != filter_system:
                        continue
                    # Sub-filtro por ruta de fuente
                    if filter_source and coll_type == "pdfs" and filter_source not in meta.get("source", ""):
                        continue
                    seen_ids.add(doc_id)

                    # Puntuación: mayor si el nombre aparece al inicio del chunk (cabecera de entrada)
                    text_start = doc[:120].upper()
                    name_upper = name.upper()
                    if text_start.startswith(name_upper) or f"\n{name_upper}" in text_start:
                        score = 0  # máxima prioridad
                    elif name_upper in text_start:
                        score = 1
                    else:
                        score = 2

                    candidates.append((score, len(candidates), {
                        "text": doc,
                        "source": meta.get("source", ""),
                        "page": meta.get("page", 0),
                        "system": meta.get("system", ""),
                        "type": meta.get("type", ""),
                        "name": meta.get("name", ""),
                        "distance": 0.0,
                        "collection": coll_type,
                    }))
            except Exception:
                continue

    # Ordenar: primero por score (cabeceras primero), luego por orden de inserción
    candidates.sort(key=lambda x: (x[0], x[1]))
    return [c[2] for c in candidates[:k]]


def format_sources(chunks: list[dict]) -> list[dict]:
    """Formatea las fuentes para enviarlas al cliente."""
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk["source"], chunk["page"])
        if key in seen:
            continue
        seen.add(key)
        if chunk["collection"] == "grimoire":
            sources.append({
                "label": chunk.get("name") or chunk["source"],
                "type": chunk.get("type", ""),
                "page": None,
            })
        else:
            src = chunk["source"]
            label = os.path.splitext(os.path.basename(src))[0]
            sources.append({
                "label": label,
                "type": "pdf",
                "source_path": src,
                "page": chunk["page"] if chunk["page"] else None,
            })
    return sources


def status() -> dict:
    """Devuelve el estado del sistema RAG (para /api/assistant/status)."""
    col_pdfs, col_grimoire = _get_collections()

    # Verificar Ollama
    ollama_ok = False
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            ollama_ok = resp.status == 200
    except Exception:
        pass

    return {
        "ollama_ready": ollama_ok,
        "chroma_ready": col_pdfs is not None or col_grimoire is not None,
        "indexed_pdfs": col_pdfs.count() if col_pdfs else 0,
        "indexed_grimoire": col_grimoire.count() if col_grimoire else 0,
    }
