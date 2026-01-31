from flask import Blueprint, current_app, jsonify, request

from database.services.character_service import get_active_characters, add_character, soft_delete_character, update_hp
from database.services.game_state_service import get_game_state
from utils.state_files import save_screen_command
from utils.markdown_content import get_markdown_detail

# Flask template registration
bp = Blueprint("api_characters", __name__, url_prefix="/api/characters")


@bp.get("")
def api_get_characters():
    """
    Fetches the list of active characters and the current game state, formats the character data, and returns a JSON response containing character details, current turn, and round number.
    Returns:
        Response: A JSON response with the following structure:
            {
                "characters": [
                    {
                        "id": int,
                        "name": str,
                        "initiative": int,
                        "hp": int,
                        "max_hp": int,
                        "type": str,
                        "order": int,
                        "isCurrent": bool,
                        "portrait_path": Optional[str]
                    },
                    ...
                ],
                "current_turn": int,
                "round_number": int
            }
    """
    characters = get_active_characters()
    game_state = get_game_state()

    characters_list = []
    for i, ch in enumerate(characters):
        portrait_path = None
        if ch.type_character == "monster" and ch.monster_slug:
            meta, _ = get_markdown_detail(current_app.config["MONSTERS_DIR"], ch.monster_slug)
            if meta:
                portrait_path = meta.get("portrait_path")

        characters_list.append({
            "id": ch.id,
            "name": ch.name,
            "initiative": ch.initiative,
            "hp": ch.health_points,
            "max_hp": ch.max_health_points,
            "type": ch.type_character,
            "order": i + 1,
            "isCurrent": (i == game_state.current_turn),
            "portrait_path": portrait_path,
        })

    return jsonify({
        "success": True,
        "characters": characters_list,
        "current_turn": game_state.current_turn,
        "round_number": game_state.round_number,
    })


@bp.post("")
def api_add_character():
    """
    Handles the API request to add a new character.
    Parses JSON data from the request body, validates the presence of the "name" field, and adds the character using the provided data. If the "name" field is missing,
    returns a 400 Bad Request response. Upon successful addition, saves the screen command and returns a success response.
    
    Returns:
        Response: A JSON response indicating success or failure, with appropriate HTTP status code.
    """
    data = request.get_json(silent=True) or {}
    if data.get("name"):
        add_character(data)
        save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 400


@bp.delete("/<int:char_id>")
def api_delete_character(char_id: int):
    """
    Deletes a character by performing a soft delete operation.
    Args:
        char_id (int): The unique identifier of the character to delete.
    Returns:
        Response: A Flask JSON response indicating success or failure.
            - If the character is not found or cannot be deleted, returns a 404 response with {"success": False}.
            - If the deletion is successful, saves the screen command and returns {"success": True}.
    """
    if soft_delete_character(char_id):
        save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 404


@bp.put("/<int:char_id>/hp")
def api_update_hp(char_id: int):
    """
    Update the HP (health points) of a character via API.
    Args:
        char_id (int): The unique identifier of the character to update.
    Returns:
        tuple: A tuple containing:
            - dict: A JSON response with a "success" key indicating operation status.
            - int: HTTP status code (200 on success, 400 if "hp" is missing, 404 if character not found).
    Request Body:
        - hp (required): The new HP value for the character.
         - Saves a screen command with type "initiative" to the screen command file.
    """
    data = request.get_json(silent=True) or {}
    if "hp" in data:
        if update_hp(char_id, data["hp"]):
            save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False}), 404
    else:
        return jsonify({"success": False}), 400