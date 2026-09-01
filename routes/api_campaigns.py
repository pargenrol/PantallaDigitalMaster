import os
import re
import unicodedata
import urllib.parse
import markdown
import frontmatter

from flask import Blueprint, jsonify, request, session

from systems.registry import get_system, DEFAULT_SYSTEM
from database.services import campaign_folder_service as folder_svc

bp = Blueprint("api_campaigns", __name__, url_prefix="/api/campaigns")

IGNORED = {".obsidian", ".trash", "Adjuntos", "Attachments"}


def _active_sistema() -> str:
    return session.get("active_system", DEFAULT_SYSTEM)


def _partidas_path() -> str:
    """Raíz "por defecto": la del sistema activo (comportamiento histórico,
    sin cambios — sigue siendo la campaña real de este servidor)."""
    system = get_system(_active_sistema())
    return system.get("vault_partidas_path", "")


def _resolve_root(root: str) -> str:
    """root == "default" (o vacío) -> raíz de siempre del sistema activo.
    root == id numérico -> ruta de una CampaignFolder registrada por el usuario."""
    if not root or root == "default":
        return _partidas_path()
    try:
        folder = folder_svc.get_folder(int(root))
    except (TypeError, ValueError):
        return ""
    return folder.path if folder else ""


def _safe_path(root: str, note_path: str) -> str | None:
    base = _resolve_root(root)
    if not note_path or not base:
        return None
    real_note = os.path.realpath(note_path)
    real_base = os.path.realpath(os.path.dirname(base))
    if not real_note.startswith(real_base):
        return None
    return real_note


def _is_visible(name: str) -> bool:
    return not name.startswith(".") and name not in IGNORED


_INDEX_CANDIDATES = ["00_indice", "00-indice", "indice", "campana", "index", "readme"]


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def _wikilinks_a_enlaces(texto: str) -> str:
    """Convierte enlaces estilo Obsidian [[Nota]] / [[Nota|Texto]] en enlaces
    markdown normales (que markdown.markdown() ya sabe convertir a <a>), con
    un esquema propio "wikilink:" para poder interceptarlos en el cliente y
    reabrir la nota destino en el mismo visor en vez de navegar fuera."""
    def _reemplazar(m):
        objetivo = m.group(1).strip()
        texto_mostrado = (m.group(2) or objetivo).strip()
        return f"[{texto_mostrado}](wikilink:{urllib.parse.quote(objetivo)})"
    return _WIKILINK_RE.sub(_reemplazar, texto)


def _normalizar_nombre(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


def _buscar_nota_por_nombre(base_dir: str, nombre_objetivo: str) -> str | None:
    """Busca recursivamente (dentro de base_dir) un .md cuyo nombre de
    fichero (sin extensión) coincida con nombre_objetivo, ignorando
    mayúsculas/acentos. Para resolver enlaces [[Nota]] sin ruta."""
    objetivo_norm = _normalizar_nombre(nombre_objetivo)
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if _is_visible(d)]
        for filename in filenames:
            if not filename.lower().endswith(".md"):
                continue
            stem = filename[:-3]
            if _normalizar_nombre(stem) == objetivo_norm:
                return os.path.join(dirpath, filename)
    return None


def _find_index_note(folder_path: str) -> str | None:
    """Al fijar una carpeta entera (una campaña), busca una nota "índice"
    razonable dentro para abrirla ya en el visor, en vez de dejarlo vacío —
    coincide por nombre exacto de la carpeta, o por convenciones habituales
    (00_INDICE, CAMPANA, index...). Solo mira el primer nivel."""
    if not os.path.isdir(folder_path):
        return None
    folder_name = os.path.basename(folder_path.rstrip(os.sep)).strip().lower()
    candidatos = [folder_name] + _INDEX_CANDIDATES
    try:
        archivos = {f.lower(): f for f in os.listdir(folder_path) if f.lower().endswith(".md")}
    except OSError:
        return None
    for candidato in candidatos:
        nombre_fichero = archivos.get(f"{candidato}.md")
        if nombre_fichero:
            return os.path.join(folder_path, nombre_fichero)
    return None


def _scan_dir(path: str, depth: int = 0) -> list[dict]:
    if not os.path.isdir(path) or depth > 2:
        return []
    items = []
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return []
    for entry in entries:
        if not _is_visible(entry.name):
            continue
        if entry.is_dir():
            children = _scan_dir(entry.path, depth + 1)
            items.append({"type": "folder", "name": entry.name, "path": entry.path, "children": children})
        elif entry.name.endswith(".md"):
            items.append({"type": "note", "name": entry.name[:-3], "path": entry.path})
    return items


@bp.get("")
def api_list_campaigns():
    root = request.args.get("root", "default")
    path = _resolve_root(root)
    if not path or not os.path.isdir(path):
        return jsonify({"success": True, "items": []})
    return jsonify({"success": True, "items": _scan_dir(path)})


@bp.get("/registered")
def api_list_registered():
    sistema = request.args.get("sistema") or _active_sistema()
    folders = folder_svc.list_folders(sistema)
    return jsonify({"success": True, "folders": [{"id": f.id, "nombre": f.nombre, "path": f.path} for f in folders]})


@bp.post("/registered")
def api_add_registered():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    path = (data.get("path") or "").strip()
    if not nombre or not path:
        return jsonify({"success": False, "error": "Nombre y ruta requeridos"}), 400
    if not os.path.isabs(path):
        return jsonify({"success": False, "error": "La ruta debe ser absoluta (empezar por / o una unidad)"}), 400
    try:
        folder = folder_svc.add_folder(_active_sistema(), nombre, path)
    except Exception as e:
        return jsonify({"success": False, "error": f"No se pudo crear/registrar la carpeta: {e}"}), 400
    return jsonify({"success": True, "folder": {"id": folder.id, "nombre": folder.nombre, "path": folder.path}}), 201


@bp.delete("/registered/<int:folder_id>")
def api_delete_registered(folder_id):
    if not folder_svc.delete_folder(folder_id):
        return jsonify({"success": False, "error": "No encontrada"}), 404
    return jsonify({"success": True})


@bp.get("/note")
def api_get_note():
    root = request.args.get("root", "default")
    note_path = request.args.get("path", "")
    real_note = _safe_path(root, note_path)
    if not real_note:
        return jsonify({"success": False, "error": "Ruta no válida"}), 400
    if not os.path.isfile(real_note) or not real_note.endswith(".md"):
        return jsonify({"success": False, "error": "Nota no encontrada"}), 404

    try:
        with open(real_note, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        contenido = _wikilinks_a_enlaces(post.content)
        html = markdown.markdown(contenido, extensions=["tables", "fenced_code"])
        pinned = session.get("campaign_note_path") == real_note
        return jsonify({
            "success": True,
            "html": html,
            "raw": post.content,
            "meta": dict(post.metadata),
            "pinned": pinned,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.get("/resolve-link")
def api_resolve_link():
    """Resuelve un enlace [[...]] clicado en una nota: busca la nota destino
    dentro de la misma raíz (root) que la nota de origen. Si el enlace lleva
    ruta relativa (../) y esa ruta cae fuera de la raíz actual (p.ej. apunta
    a la carpeta de otro sistema), se marca como "outside" en vez de
    intentar cruzar a otra raíz — ese caso no está soportado."""
    root = request.args.get("root", "default")
    from_path = request.args.get("from_path", "")
    target = request.args.get("target", "")
    if not target:
        return jsonify({"success": True, "found": False})

    base = _resolve_root(root)
    if not base:
        return jsonify({"success": True, "found": False})
    # A diferencia de _safe_path (que usa el padre de "base" por motivos
    # históricos y queda más laxo), aquí se quiere la raíz real de la propia
    # campaña — si no, una búsqueda por nombre puede colarse en la carpeta
    # hermana de otro sistema (p.ej. la versión 5e de la misma campaña).
    base_dir = os.path.realpath(base)

    objetivo = target[:-3] if target.lower().endswith(".md") else target

    if "/" in objetivo or "\\" in objetivo:
        origen_dir = os.path.dirname(from_path) if from_path else base_dir
        candidato = os.path.realpath(os.path.join(origen_dir, objetivo + ".md"))
        if not candidato.startswith(base_dir):
            return jsonify({"success": True, "found": False, "outside": True})
        if os.path.isfile(candidato):
            return jsonify({"success": True, "found": True, "root": root, "path": candidato,
                             "name": os.path.basename(candidato)[:-3]})
        return jsonify({"success": True, "found": False})

    encontrado = _buscar_nota_por_nombre(base_dir, objetivo)
    if encontrado:
        return jsonify({"success": True, "found": True, "root": root, "path": encontrado,
                         "name": os.path.basename(encontrado)[:-3]})
    return jsonify({"success": True, "found": False})


@bp.put("/note")
def api_save_note():
    data = request.get_json(silent=True) or {}
    root = data.get("root", "default")
    note_path = data.get("path", "")
    content = data.get("content", "")

    real_note = _safe_path(root, note_path)
    if not real_note:
        return jsonify({"success": False, "error": "Ruta no válida"}), 400
    if not real_note.endswith(".md"):
        return jsonify({"success": False, "error": "Solo archivos .md"}), 400

    try:
        # Preserve existing frontmatter if the file exists
        if os.path.isfile(real_note):
            with open(real_note, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            post.content = content
            with open(real_note, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
        else:
            with open(real_note, "w", encoding="utf-8") as f:
                f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.post("/note")
def api_create_note():
    data = request.get_json(silent=True) or {}
    root = data.get("root", "default")
    folder_path = data.get("folder", "")
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Nombre requerido"}), 400

    real_folder = _safe_path(root, folder_path)
    if not real_folder or not os.path.isdir(real_folder):
        # Try using la raíz elegida (default o registrada) directamente
        real_folder = os.path.realpath(_resolve_root(root))

    slug = re.sub(r'[^\w\s\-áéíóúÁÉÍÓÚñÑüÜ]', '', name).strip()
    note_path = os.path.join(real_folder, f"{slug}.md")

    if os.path.exists(note_path):
        return jsonify({"success": False, "error": "Ya existe una nota con ese nombre"}), 409

    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\n")
        return jsonify({"success": True, "path": note_path, "name": name})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _load_folder_content(folder_path: str, max_chars: int = 8000) -> str:
    """Carga todos los .md de una carpeta recursivamente, hasta max_chars."""
    parts = []
    total = 0
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = sorted(d for d in dirs if _is_visible(d))
        for fname in sorted(f for f in files if f.endswith(".md")):
            if total >= max_chars:
                break
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    post = frontmatter.load(f)
                title = fname.replace(".md", "")
                chunk = f"### {title}\n{post.content}"
                parts.append(chunk)
                total += len(chunk)
            except Exception:
                pass
    return "\n\n---\n\n".join(parts)[:max_chars]


@bp.post("/pin")
def api_pin_note():
    data = request.get_json(silent=True) or {}
    root = data.get("root", "default")
    path = data.get("path", "")
    pin_type = data.get("type", "note")  # "note" or "folder"
    name = data.get("name", "")

    real_path = _safe_path(root, path)
    if not real_path:
        return jsonify({"success": False, "error": "Ruta no válida"}), 400

    if pin_type == "folder":
        if not os.path.isdir(real_path):
            return jsonify({"success": False, "error": "Carpeta no encontrada"}), 404
        session["campaign_pin_path"] = real_path
        session["campaign_pin_type"] = "folder"
        session["campaign_pin_name"] = name or os.path.basename(real_path)
    else:
        if not os.path.isfile(real_path):
            return jsonify({"success": False, "error": "Nota no encontrada"}), 404
        session["campaign_pin_path"] = real_path
        session["campaign_pin_type"] = "note"
        session["campaign_pin_name"] = name or os.path.basename(real_path).replace(".md", "")

    # Se guarda también el root para poder reabrir la nota/carpeta fijada
    # directamente en el visor con la misma llamada que un clic manual en el
    # árbol (/api/campaigns/note necesita root+path; "path" aquí ya es
    # absoluta y coincide con la que guarda _safe_path, no hace falta
    # guardarla dos veces).
    session["campaign_pin_root"] = root

    index_path = _find_index_note(real_path) if pin_type == "folder" else None
    return jsonify({"success": True, "name": session["campaign_pin_name"], "indexPath": index_path})


@bp.post("/unpin")
def api_unpin_note():
    session.pop("campaign_pin_path", None)
    session.pop("campaign_pin_type", None)
    session.pop("campaign_pin_name", None)
    session.pop("campaign_pin_root", None)
    # backwards compat
    session.pop("campaign_note_path", None)
    session.pop("campaign_note_name", None)
    return jsonify({"success": True})


@bp.get("/pinned")
def api_get_pinned():
    path = session.get("campaign_pin_path") or session.get("campaign_note_path")
    pin_type = session.get("campaign_pin_type", "note")
    name = session.get("campaign_pin_name") or session.get("campaign_note_name", "")
    root = session.get("campaign_pin_root")
    if not path:
        return jsonify({"success": True, "pinned": None})
    if pin_type == "folder":
        if not os.path.isdir(path):
            return jsonify({"success": True, "pinned": None})
        return jsonify({"success": True, "pinned": {"path": path, "name": name, "type": "folder", "root": root,
                                                      "indexPath": _find_index_note(path)}})
    else:
        if not os.path.isfile(path):
            return jsonify({"success": True, "pinned": None})
        try:
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            return jsonify({"success": True, "pinned": {"path": path, "name": name, "type": "note",
                                                          "content": post.content, "root": root}})
        except Exception:
            return jsonify({"success": True, "pinned": None})
