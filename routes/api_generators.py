from flask import Blueprint, jsonify, request

from database.services import generator_service as svc

bp = Blueprint("api_generators", __name__, url_prefix="/api/generators")


def _entry_to_dict(e):
    return {"id": e.id, "texto": e.texto, "orden": e.orden, "usado": e.usado}


@bp.route("/<slug>/entries", methods=["GET"])
def list_entries(slug):
    entries = svc.list_entries(slug)
    return jsonify([_entry_to_dict(e) for e in entries])


@bp.route("/<slug>/entries", methods=["POST"])
def add_entry(slug):
    data = request.get_json(silent=True) or {}
    texto = (data.get("texto") or "").strip()
    if not texto:
        return jsonify({"error": "texto requerido"}), 400
    entry = svc.add_entry(slug, texto)
    if not entry:
        return jsonify({"error": "tabla no encontrada"}), 404
    return jsonify(_entry_to_dict(entry)), 201


@bp.route("/entries/<int:entry_id>", methods=["PUT"])
def update_entry(entry_id):
    data = request.get_json(silent=True) or {}
    entry = svc.update_entry(entry_id, texto=data.get("texto"), usado=data.get("usado"))
    if not entry:
        return jsonify({"error": "no encontrada"}), 404
    return jsonify(_entry_to_dict(entry))


@bp.route("/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    ok = svc.delete_entry(entry_id)
    if not ok:
        return jsonify({"error": "no encontrada"}), 404
    return jsonify({"ok": True})


@bp.route("/<slug>/reset", methods=["POST"])
def reset_usados(slug):
    svc.reset_usados(slug)
    return jsonify({"ok": True})


@bp.route("/<slug>/roll", methods=["POST"])
def roll(slug):
    data = request.get_json(silent=True) or {}
    evitar_usadas = data.get("evitar_usadas", True)
    entry = svc.roll(slug, evitar_usadas=evitar_usadas)
    if not entry:
        return jsonify({"error": "tabla vacía o no encontrada"}), 404
    return jsonify(_entry_to_dict(entry))
