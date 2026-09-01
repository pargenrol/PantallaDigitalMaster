from flask import Blueprint, jsonify, request

from database.services import equipo_service as svc

bp = Blueprint("api_equipo", __name__, url_prefix="/api/equipo")


def _item_to_dict(item):
    return {
        "id": item.id,
        "nombre": item.nombre,
        "descripcion": item.descripcion or "",
        "precio": item.precio,
        "sistema": item.sistema,
        "categoria": item.categoria or "",
    }


@bp.route("", methods=["GET"])
def list_equipo():
    sistema = request.args.get("sistema", "adnd2e")
    items = svc.list_equipo(sistema)
    return jsonify([_item_to_dict(i) for i in items])


@bp.route("", methods=["POST"])
def add_equipo():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "nombre requerido"}), 400
    item = svc.get_or_create_item(
        nombre=nombre,
        descripcion=data.get("descripcion"),
        precio=data.get("precio"),
        sistema=data.get("sistema", "adnd2e"),
        categoria=data.get("categoria"),
    )
    return jsonify(_item_to_dict(item)), 201


@bp.route("/<int:item_id>", methods=["PUT"])
def update_equipo(item_id):
    data = request.get_json(silent=True) or {}
    item = svc.update_item(item_id, nombre=data.get("nombre"), descripcion=data.get("descripcion"),
                            precio=data.get("precio"), categoria=data.get("categoria"))
    if not item:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(_item_to_dict(item))


@bp.route("/<int:item_id>", methods=["DELETE"])
def delete_equipo(item_id):
    if not svc.delete_item(item_id):
        return jsonify({"error": "no encontrado"}), 404
    return jsonify({"ok": True})


@bp.route("/categoria/<int:categoria_id>", methods=["GET"])
def list_asignaciones(categoria_id):
    asignaciones = svc.list_asignaciones_categoria(categoria_id)
    return jsonify([
        {"equipo_id": a.equipo_id, "nombre": a.equipo.nombre, "nivel_minimo": a.nivel_minimo}
        for a in asignaciones
    ])


@bp.route("/categoria/<int:categoria_id>/asignar", methods=["POST"])
def asignar(categoria_id):
    data = request.get_json(silent=True) or {}
    equipo_id = data.get("equipo_id")
    nivel_minimo = int(data.get("nivel_minimo", 1))
    if not equipo_id:
        return jsonify({"error": "equipo_id requerido"}), 400
    svc.asignar_a_categoria(categoria_id, equipo_id, nivel_minimo)
    return jsonify({"ok": True})


@bp.route("/categoria/<int:categoria_id>/desasignar/<int:equipo_id>", methods=["DELETE"])
def desasignar(categoria_id, equipo_id):
    if not svc.desasignar_de_categoria(categoria_id, equipo_id):
        return jsonify({"error": "no encontrada"}), 404
    return jsonify({"ok": True})
