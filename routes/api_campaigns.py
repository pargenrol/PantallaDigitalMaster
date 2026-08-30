import os
import re
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
        html = markdown.markdown(post.content, extensions=["tables", "fenced_code"])
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

    return jsonify({"success": True, "name": session["campaign_pin_name"]})


@bp.post("/unpin")
def api_unpin_note():
    session.pop("campaign_pin_path", None)
    session.pop("campaign_pin_type", None)
    session.pop("campaign_pin_name", None)
    # backwards compat
    session.pop("campaign_note_path", None)
    session.pop("campaign_note_name", None)
    return jsonify({"success": True})


@bp.get("/pinned")
def api_get_pinned():
    path = session.get("campaign_pin_path") or session.get("campaign_note_path")
    pin_type = session.get("campaign_pin_type", "note")
    name = session.get("campaign_pin_name") or session.get("campaign_note_name", "")
    if not path:
        return jsonify({"success": True, "pinned": None})
    if pin_type == "folder":
        if not os.path.isdir(path):
            return jsonify({"success": True, "pinned": None})
        return jsonify({"success": True, "pinned": {"path": path, "name": name, "type": "folder"}})
    else:
        if not os.path.isfile(path):
            return jsonify({"success": True, "pinned": None})
        try:
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            return jsonify({"success": True, "pinned": {"path": path, "name": name, "type": "note", "content": post.content}})
        except Exception:
            return jsonify({"success": True, "pinned": None})
