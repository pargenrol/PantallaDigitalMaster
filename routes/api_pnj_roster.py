from flask import Blueprint, jsonify, request

from database.services import pnj_roster_service as svc

bp = Blueprint("api_pnj_roster", __name__, url_prefix="/api/pnj-roster")


def _entry_to_dict(e):
    return {
        "id": e.id,
        "sistema": e.sistema,
        "nombre": e.nombre,
        "categoria": e.categoria_nombre,
        "dg": e.dg,
        "genero": e.genero,
        "stats": e.stats_dict(),
        "equipo": e.equipo_lista(),
        "rasgos": e.rasgos_lista(),
        "descripcion": e.descripcion or "",
        "notas": e.notas or "",
    }


@bp.route("", methods=["GET"])
def list_roster():
    sistema = request.args.get("sistema", "adnd2e")
    entries = svc.list_roster(sistema)
    return jsonify([_entry_to_dict(e) for e in entries])


@bp.route("/<int:entry_id>", methods=["GET"])
def get_roster_entry(entry_id):
    entry = svc.get_roster_entry(entry_id)
    if not entry:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(_entry_to_dict(entry))


@bp.route("", methods=["POST"])
def add_roster_entry():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    categoria = (data.get("categoria") or "").strip()
    if not nombre or not categoria:
        return jsonify({"error": "nombre y categoria requeridos"}), 400

    try:
        dg = int(data.get("dg", 1))
    except (TypeError, ValueError):
        dg = 1

    entry = svc.add_roster_entry(
        nombre=nombre,
        categoria_nombre=categoria,
        dg=dg,
        genero=data.get("genero", "aleatorio"),
        stats=data.get("stats") or {},
        equipo=data.get("equipo") or [],
        rasgos=data.get("rasgos") or [],
        descripcion=data.get("descripcion") or "",
        notas=data.get("notas") or "",
        sistema=data.get("sistema", "adnd2e"),
    )
    return jsonify(_entry_to_dict(entry)), 201


@bp.route("/<int:entry_id>", methods=["PUT"])
def update_roster_entry(entry_id):
    data = request.get_json(silent=True) or {}
    entry = svc.update_roster_entry(entry_id, notas=data.get("notas"), descripcion=data.get("descripcion"))
    if not entry:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(_entry_to_dict(entry))


@bp.route("/<int:entry_id>", methods=["DELETE"])
def delete_roster_entry(entry_id):
    if not svc.delete_roster_entry(entry_id):
        return jsonify({"error": "no encontrado"}), 404
    return jsonify({"ok": True})
