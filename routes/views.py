from flask import Blueprint, current_app, render_template

from database.services.character_service import get_active_characters
from database.services.game_state_service import get_game_state
from utils.markdown_content import load_markdown_content, get_markdown_detail

# Flask template registration
bp = Blueprint("views", __name__)


@bp.route("/")
def index():
    return master()


@bp.route("/master")
def master():
    """
    Render the master game screen with all necessary game data.
    Retrieves active characters, current game state, and loads grimoire content (monsters, spells, and rules) from markdown files. 
    Combines all data and renders the master.html template.
    Returns:
        str: Rendered HTML template with characters, game state, and grimoire data.
    """
    #Obtain data game from BBDD
    characters_data = get_active_characters()
    game_state = get_game_state()

    #Obtain detail from markdown files
    monsters = load_markdown_content(current_app.config["MONSTERS_DIR"])
    spells = load_markdown_content(current_app.config["SPELLS_DIR"])
    rules = load_markdown_content(current_app.config["RULES_DIR"])

    return render_template(
        "master.html",
        characters=characters_data,
        current_turn=game_state.current_turn,
        grimorio_monsters=monsters,
        grimorio_spells=spells,
        grimorio_rules=rules,
    )


@bp.route("/player")
def player():
    return render_template("player.html")


@bp.route("/player/screen")
def player_screen():
    return render_template("player.html", fullscreen=True)


@bp.route("/content/<ctype>/<slug>")
def get_content_detail(ctype, slug):
    """
    Retrieves detailed content for a specific entity based on type and slug. This function fetches markdown content from the appropriate directory based on the 
    content type and converts it to HTML along with its metadata.
    Args:
        ctype (str): The content type. Can be "spell", "rule", or defaults to monster.
                     Determines which directory configuration to use.
        slug (str): The identifier/filename of the content to retrieve (without extension).
    Returns:
        tuple: A tuple containing:
            - If content found: (rendered_template, status_code)
                - rendered_template (str): HTML template with metadata and content
                - status_code (int): HTTP status code 200 (implicit)
            - If content not found: (error_html, status_code)
                - error_html (str): HTML error message
                - status_code (int): HTTP status code 404
    """
    if ctype == "monster":
        dir_path = current_app.config["MONSTERS_DIR"]
    elif ctype == "spell":
        dir_path = current_app.config["SPELLS_DIR"]
    elif ctype == "rule":
        dir_path = current_app.config["RULES_DIR"]

    metadata, html = get_markdown_detail(dir_path, slug)
    if not metadata:
        return '<div class="error">No encontrado</div>', 404

    return render_template("content_detail.html", metadata=metadata, contenido=html, type=ctype)
