from flask import Blueprint, current_app, jsonify
from database.services.game_state_service import next_turn, prev_turn, reset_game
from utils.state_files import save_screen_command

# Flask template registration
bp = Blueprint("api_game", __name__, url_prefix="/api/game")


@bp.post("/next-turn")
def api_next_turn():
    """
    Handle the API request to advance to the next turn in the game.
    Attempts to progress the game to the next turn. If successful, saves a screen command to display the initiative. Returns a JSON response indicating success or failure.

    Returns:
        Flask.Response: A JSON response with a "success" boolean field.
            - {"success": False} if next_turn() fails
            - {"success": True} if next_turn() succeeds and screen command is saved
    """
    if next_turn():
        save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


@bp.post("/prev-turn")
def api_prev_turn():
    """
    Handle the API request to advance to the previous turn in the game.
    Attempts to progress the game to the previous turn. If successful, saves a screen command to display the initiative. Returns a JSON response indicating success or failure.

    Returns:
        Flask.Response: A JSON response with a "success" boolean field.
            - {"success": False} if prev_turn() fails
            - {"success": True} if prev_turn() succeeds and screen command is saved
    """
    if prev_turn():
        save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


@bp.post("/reset")
def api_reset_game():
    """
    Resets the game state and clears the screen command.

    This endpoint handler performs the following actions:
        1. Calls the `reset_game()` function to reset the game state.
        2. Saves the "clear" command to the screen command file specified in the app configuration.
        3. Returns a JSON response indicating success.

    Returns:
        Response: A JSON response with {"success": True}.
    """
    reset_game()
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "clear")
    return jsonify({"success": True})
