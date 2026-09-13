from flask import Blueprint, jsonify, request

from database.services import torch_service

bp = Blueprint("api_torch", __name__, url_prefix="/api/torch")


@bp.get("/state")
def api_get_state():
    state = torch_service.get_torch_state()
    return jsonify({"success": True, **torch_service.to_dict(state)})


@bp.post("/start")
def api_start():
    data = request.get_json(silent=True) or {}
    duration = int(data.get("duration_seconds", 3600) or 3600)
    state = torch_service.start(duration)
    return jsonify({"success": True, **torch_service.to_dict(state)})


@bp.post("/pause")
def api_pause():
    state = torch_service.pause()
    return jsonify({"success": True, **torch_service.to_dict(state)})


@bp.post("/resume")
def api_resume():
    state = torch_service.resume()
    return jsonify({"success": True, **torch_service.to_dict(state)})


@bp.post("/stop")
def api_stop():
    state = torch_service.stop()
    return jsonify({"success": True, **torch_service.to_dict(state)})
