from flask import Blueprint, current_app, jsonify, request
from utils.state_files import save_whiteboard_state, load_whiteboard_state

# Flask template registration
bp = Blueprint("api_whiteboard", __name__, url_prefix="/api/whiteboard")


@bp.post("/save")
def api_save_whiteboard():
    """
    Save the current whiteboard state to persistent storage.
    Expects a JSON POST request with a 'state' field containing the whiteboard state data.
    Returns:
        tuple: A tuple containing:
            - dict: JSON response with 'success' key set to True if save was successful
            - int: HTTP status code (200 on success, 400 on missing state)
    """
    data = request.get_json(silent=True) or {}
    state_json = data.get("state")
    if not state_json:
        return jsonify({"success": False}), 400

    save_whiteboard_state(current_app.config["WHITEBOARD_STATE_FILE"], state_json)
    return jsonify({"success": True})


@bp.get("/load")
def api_load_whiteboard():
    return jsonify(load_whiteboard_state(current_app.config["WHITEBOARD_STATE_FILE"]))