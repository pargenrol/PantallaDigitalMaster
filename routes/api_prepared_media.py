from flask import Blueprint, jsonify, request

from database.services import prepared_media_service as svc

bp = Blueprint("api_prepared_media", __name__, url_prefix="/api/prepared-media")

_TIPOS_VALIDOS = {"audio", "video", "html", "imagen"}


def _to_dict(media) -> dict:
    return {
        "id": media.id,
        "nombre": media.nombre,
        "tipo": media.tipo,
        "ruta": media.ruta,
        "descripcion": media.descripcion or "",
    }


@bp.get("")
def list_media():
    return jsonify([_to_dict(m) for m in svc.list_media()])


@bp.post("")
def add_media():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    tipo = (data.get("tipo") or "").strip()
    ruta = (data.get("ruta") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    if not nombre or not ruta:
        return jsonify({"error": "nombre y ruta requeridos"}), 400
    if tipo not in _TIPOS_VALIDOS:
        return jsonify({"error": f"tipo debe ser uno de {sorted(_TIPOS_VALIDOS)}"}), 400
    media = svc.add_media(nombre, tipo, ruta, descripcion)
    return jsonify(_to_dict(media)), 201


@bp.delete("/<int:media_id>")
def delete_media(media_id: int):
    if not svc.delete_media(media_id):
        return jsonify({"error": "no encontrado"}), 404
    return jsonify({"ok": True})
