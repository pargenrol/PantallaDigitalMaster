import os
import frontmatter

from flask import Blueprint, current_app, jsonify, request, session

from database.services.character_service import get_active_characters, add_character, soft_delete_character, update_hp, update_stress, update_initiative, get_character
from database.services.game_state_service import get_game_state, touch as touch_state
from systems.registry import get_system, DEFAULT_SYSTEM
from utils.state_files import save_screen_command
from utils.markdown_content import get_markdown_detail, parse_px

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

    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    monsters_dir = system["resources"]["monsters"]
    players_dir = system["resources"].get("players")

    characters_list = []
    for i, ch in enumerate(characters):
        portrait_path = None
        if ch.type_character == "monster" and ch.monster_slug:
            meta, _ = get_markdown_detail(monsters_dir, ch.monster_slug)
            if meta:
                portrait_path = meta.get("portrait_path")
        elif ch.type_character == "player" and ch.monster_slug and players_dir:
            meta, _ = get_markdown_detail(players_dir, ch.monster_slug)
            if meta:
                portrait_path = meta.get("portrait_path")

        characters_list.append({
            "id": ch.id,
            "name": ch.name,
            "initiative": ch.initiative,
            "hp": ch.health_points,
            "max_hp": ch.max_health_points,
            "stress": ch.stress,
            "max_stress": ch.max_stress,
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
        touch_state()
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
        touch_state()
        save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 404


@bp.put("/<int:char_id>/stress")
def api_update_stress(char_id: int):
    data = request.get_json(silent=True) or {}
    if "stress" in data:
        if update_stress(char_id, data["stress"]):
            touch_state()
            save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False}), 404
    else:
        return jsonify({"success": False}), 400


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
            touch_state()
            save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False}), 404
    else:
        return jsonify({"success": False}), 400


@bp.put("/<int:char_id>/initiative")
def api_update_initiative(char_id: int):
    data = request.get_json(silent=True) or {}
    if "initiative" in data:
        if update_initiative(char_id, data["initiative"]):
            touch_state()
            save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False}), 404
    else:
        return jsonify({"success": False}), 400


@bp.get("/<int:char_id>/sheet")
def api_get_character_sheet(char_id: int):
    """
    Devuelve la ficha (metadata + html) del monstruo o jugador vinculado a
    este combatiente, para mostrar un resumen de stats/ataques cuando tiene
    el turno activo.
    """
    ch = get_character(char_id)
    if not ch:
        return jsonify({"success": False}), 404
    if not ch.monster_slug:
        return jsonify({"success": True, "sheet": None})

    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    res = system["resources"]
    dir_path = res["monsters"] if ch.type_character == "monster" else res.get("players")
    if not dir_path:
        return jsonify({"success": True, "sheet": None})

    metadata, html = get_markdown_detail(dir_path, ch.monster_slug)
    if not metadata:
        return jsonify({"success": True, "sheet": None})

    return jsonify({"success": True, "sheet": {"metadata": metadata, "html": html}})


@bp.get("/xp-summary")
def api_xp_summary():
    """
    Calculadora de PX de combate (reglas AD&D2e): suma los Puntos de
    Experiencia de los monstruos actualmente en la iniciativa (leídos de su
    ficha real, campo `px`) y lista a los jugadores activos para repartirla.
    """
    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    res = system["resources"]
    monsters_dir = res["monsters"]

    characters = get_active_characters()
    monster_breakdown = []
    total_px = 0
    players = []

    for ch in characters:
        if ch.type_character == "monster" and ch.monster_slug:
            meta, _ = get_markdown_detail(monsters_dir, ch.monster_slug)
            px = parse_px(meta.get("px")) if meta else None
            monster_breakdown.append({
                "id": ch.id, "name": ch.name, "slug": ch.monster_slug,
                "px": px, "px_raw": (meta.get("px") if meta else None),
            })
            if px:
                total_px += px
        elif ch.type_character == "player" and ch.monster_slug:
            players.append({"id": ch.id, "name": ch.name, "slug": ch.monster_slug})

    return jsonify({"monsters": monster_breakdown, "total_px": total_px, "players": players})


@bp.post("/xp-award")
def api_xp_award():
    """Aplica una cantidad de PX a la ficha de cada jugador indicado (se suma
    a su `experiencia` actual)."""
    data = request.get_json(silent=True) or {}
    slugs = data.get("player_slugs") or []
    try:
        amount = int(data.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0

    if not slugs or amount <= 0:
        return jsonify({"success": False, "error": "Faltan jugadores o la cantidad de PX"}), 400

    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    players_dir = system["resources"].get("players")
    if not players_dir:
        return jsonify({"success": False, "error": "Este sistema no tiene jugadores"}), 400

    resultados = []
    for slug in slugs:
        filepath = os.path.join(players_dir, f"{slug}.md")
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        actual = 0
        try:
            actual = int(post.get("experiencia") or 0)
        except (TypeError, ValueError):
            actual = 0
        nuevo = actual + amount
        post["experiencia"] = nuevo
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
        resultados.append({"slug": slug, "experiencia_anterior": actual, "experiencia": nuevo})

    return jsonify({"success": True, "resultados": resultados})