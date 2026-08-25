from flask import Blueprint, jsonify, request

from database.services import pnj_categoria_service as svc
from utils.nombre_generator import generar_nombre

bp = Blueprint("api_pnj_categorias", __name__, url_prefix="/api/pnj-categorias")


def _cat_to_dict(cat):
    return {
        "id": cat.id,
        "nombre": cat.nombre,
        "sistema": cat.sistema,
        "stats_config": cat.stats_dict(),
        "equipo_basico": cat.equipo_basico or "",
    }


@bp.route("", methods=["GET"])
def list_categorias():
    sistema = request.args.get("sistema", "adnd2e")
    cats = svc.list_categorias(sistema)
    return jsonify([_cat_to_dict(c) for c in cats])


@bp.route("", methods=["POST"])
def add_categoria():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "nombre requerido"}), 400
    cat = svc.add_categoria(
        nombre=nombre,
        stats_config=data.get("stats_config") or {},
        equipo_basico=data.get("equipo_basico") or "",
        sistema=data.get("sistema", "adnd2e"),
    )
    return jsonify(_cat_to_dict(cat)), 201


@bp.route("/<int:categoria_id>", methods=["PUT"])
def update_categoria(categoria_id):
    data = request.get_json(silent=True) or {}
    cat = svc.update_categoria(
        categoria_id,
        nombre=data.get("nombre"),
        stats_config=data.get("stats_config"),
        equipo_basico=data.get("equipo_basico"),
    )
    if not cat:
        return jsonify({"error": "no encontrada"}), 404
    return jsonify(_cat_to_dict(cat))


@bp.route("/<int:categoria_id>", methods=["DELETE"])
def delete_categoria(categoria_id):
    if not svc.delete_categoria(categoria_id):
        return jsonify({"error": "no encontrada"}), 404
    return jsonify({"ok": True})


@bp.route("/nombre", methods=["POST"])
def nombre():
    data = request.get_json(silent=True) or {}
    genero = data.get("genero", "aleatorio")
    return jsonify({"nombre": generar_nombre(genero)})


@bp.route("/generar", methods=["POST"])
def generar_pnj():
    data = request.get_json(silent=True) or {}
    dg = data.get("dg")
    categoria_id = data.get("categoria_id")
    genero = data.get("genero", "aleatorio")

    try:
        dg = int(dg)
    except (TypeError, ValueError):
        return jsonify({"error": "dg debe ser un número"}), 400

    if not categoria_id:
        cat = svc.categoria_al_azar(data.get("sistema", "adnd2e"))
        if not cat:
            return jsonify({"error": "no hay categorías de PNJ creadas todavía"}), 404
        categoria_id = cat.id

    resultado = svc.generar_pnj(categoria_id, dg)
    if not resultado:
        return jsonify({"error": "categoría no encontrada"}), 404

    resultado["nombre"] = generar_nombre(genero)
    resultado["genero"] = genero
    return jsonify(resultado)
