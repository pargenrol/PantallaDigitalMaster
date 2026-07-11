import os
import re
import frontmatter

from flask import Blueprint, current_app, jsonify, request, session

from systems.registry import get_system, DEFAULT_SYSTEM
from utils.markdown_content import load_markdown_content

bp = Blueprint("api_players", __name__, url_prefix="/api/players")


def _players_dir() -> str:
    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    return system["resources"].get("players", "")


def _slug(nombre: str) -> str:
    s = nombre.lower().strip()
    s = re.sub(r"[áàä]", "a", s)
    s = re.sub(r"[éèë]", "e", s)
    s = re.sub(r"[íìï]", "i", s)
    s = re.sub(r"[óòö]", "o", s)
    s = re.sub(r"[úùü]", "u", s)
    s = re.sub(r"[ñ]", "n", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _save_player(players_dir: str, slug: str, data: dict) -> None:
    os.makedirs(players_dir, exist_ok=True)
    post = frontmatter.Post("", **data)
    filepath = os.path.join(players_dir, f"{slug}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


@bp.get("")
def api_get_players():
    players_dir = _players_dir()
    players = load_markdown_content(players_dir)
    return jsonify({"success": True, "players": players})


@bp.post("")
def api_create_player():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"success": False, "error": "nombre requerido"}), 400

    players_dir = _players_dir()
    slug = _slug(nombre)

    filepath = os.path.join(players_dir, f"{slug}.md")
    if os.path.exists(filepath):
        return jsonify({"success": False, "error": "Ya existe un jugador con ese nombre"}), 409

    _save_player(players_dir, slug, data)
    return jsonify({"success": True, "slug": slug})


@bp.put("/<slug>")
def api_update_player(slug: str):
    data = request.get_json(silent=True) or {}
    players_dir = _players_dir()
    filepath = os.path.join(players_dir, f"{slug}.md")

    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Jugador no encontrado"}), 404

    _save_player(players_dir, slug, data)
    return jsonify({"success": True})


@bp.delete("/<slug>")
def api_delete_player(slug: str):
    players_dir = _players_dir()
    filepath = os.path.join(players_dir, f"{slug}.md")

    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Jugador no encontrado"}), 404

    os.remove(filepath)
    return jsonify({"success": True})
