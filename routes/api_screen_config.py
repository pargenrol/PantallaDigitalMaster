from flask import Blueprint, jsonify, request

from database.services import screen_config_service as svc

bp = Blueprint("api_screen_config", __name__, url_prefix="/api/screen-configs")


def _config_to_dict(config):
    return {
        "id": config.id,
        "sistema": config.sistema,
        "nombre": config.nombre,
        "paneles": config.paneles,
    }


@bp.route("", methods=["GET"])
def list_configs():
    sistema = request.args.get("sistema", "adnd2e")
    configs = svc.list_configs(sistema)
    return jsonify([_config_to_dict(c) for c in configs])


@bp.route("", methods=["POST"])
def save_config():
    data = request.get_json(silent=True) or {}
    sistema = data.get("sistema", "adnd2e")
    nombre = (data.get("nombre") or "").strip()
    paneles = data.get("paneles")
    if not nombre:
        return jsonify({"error": "nombre requerido"}), 400
    if not isinstance(paneles, list):
        return jsonify({"error": "paneles debe ser una lista"}), 400
    config = svc.save_config(sistema, nombre, paneles)
    return jsonify(_config_to_dict(config)), 201


@bp.route("/<int:config_id>", methods=["DELETE"])
def delete_config(config_id):
    if not svc.delete_config(config_id):
        return jsonify({"error": "no encontrada"}), 404
    return jsonify({"ok": True})
