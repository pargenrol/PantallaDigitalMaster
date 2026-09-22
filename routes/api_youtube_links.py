from flask import Blueprint, jsonify, request

from database.services import youtube_link_service as svc

bp = Blueprint("api_youtube_links", __name__, url_prefix="/api/youtube-links")


def _to_dict(link) -> dict:
    return {"id": link.id, "nombre": link.nombre, "url": link.url}


@bp.get("")
def list_links():
    return jsonify([_to_dict(l) for l in svc.list_links()])


@bp.post("")
def add_link():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    url = (data.get("url") or "").strip()
    if not nombre or not url:
        return jsonify({"error": "nombre y url requeridos"}), 400
    link = svc.add_link(nombre, url)
    return jsonify(_to_dict(link)), 201


@bp.delete("/<int:link_id>")
def delete_link(link_id: int):
    if not svc.delete_link(link_id):
        return jsonify({"error": "no encontrado"}), 404
    return jsonify({"ok": True})
