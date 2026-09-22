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
    grimoire = svc.list_grimoire_pnjs(sistema)
    entries = svc.list_roster(sistema)
    return jsonify(grimoire + [_entry_to_dict(e) for e in entries])


@bp.route("/<entry_id>", methods=["GET"])
def get_roster_entry(entry_id):
    if entry_id.startswith("grimoire:"):
        sistema = request.args.get("sistema", "adnd2e")
        entry = svc.get_grimoire_pnj(sistema, entry_id.split(":", 1)[1])
        if not entry:
            return jsonify({"error": "no encontrado"}), 404
        return jsonify(entry)

    try:
        entry = svc.get_roster_entry(int(entry_id))
    except ValueError:
        return jsonify({"error": "id inválido"}), 400
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


@bp.route("/<entry_id>", methods=["PUT"])
def update_roster_entry(entry_id):
    if entry_id.startswith("grimoire:"):
        return jsonify({"error": "Es un PNJ de campaña del grimorio — edítalo desde su ficha, no desde aquí"}), 400
    data = request.get_json(silent=True) or {}
    try:
        entry = svc.update_roster_entry(int(entry_id), notas=data.get("notas"), descripcion=data.get("descripcion"))
    except ValueError:
        return jsonify({"error": "id inválido"}), 400
    if not entry:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(_entry_to_dict(entry))


@bp.route("/<entry_id>", methods=["DELETE"])
def delete_roster_entry(entry_id):
    if entry_id.startswith("grimoire:"):
        return jsonify({"error": "Es un PNJ de campaña del grimorio — no se puede eliminar desde aquí"}), 400
    try:
        ok = svc.delete_roster_entry(int(entry_id))
    except ValueError:
        return jsonify({"error": "id inválido"}), 400
    if not ok:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify({"ok": True})
