from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from database.services.character_service import get_active_characters
from database.services.game_state_service import get_game_state
from systems.registry import get_all_systems, get_system, DEFAULT_SYSTEM
from utils.markdown_content import load_markdown_content, get_markdown_detail

bp = Blueprint("views", __name__)


def _active_system() -> dict:
    return get_system(session.get("active_system", DEFAULT_SYSTEM))


@bp.route("/")
def index():
    if "active_system" not in session:
        return redirect(url_for("views.select_system"))
    return redirect(url_for("views.master"))


@bp.route("/select-system")
def select_system():
    return render_template("select_system.html", systems=get_all_systems())


@bp.route("/select-system", methods=["POST"])
def set_system():
    system_id = request.form.get("system_id", DEFAULT_SYSTEM)
    session["active_system"] = system_id
    return redirect(url_for("views.master"))


@bp.route("/change-system")
def change_system():
    session.pop("active_system", None)
    return redirect(url_for("views.select_system"))


@bp.route("/master")
def master():
    if "active_system" not in session:
        return redirect(url_for("views.select_system"))

    system = _active_system()
    res = system["resources"]

    characters_data = get_active_characters()
    game_state = get_game_state()

    monsters = load_markdown_content(res["monsters"])
    spells = load_markdown_content(res["spells"])
    rules = load_markdown_content(res["rules"])

    return render_template(
        "master.html",
        system=system,
        characters=characters_data,
        current_turn=game_state.current_turn,
        grimorio_monsters=monsters,
        grimorio_spells=spells,
        grimorio_rules=rules,
    )


@bp.route("/player")
def player():
    system = _active_system()
    return render_template("player.html", system=system)


@bp.route("/player/screen")
def player_screen():
    system = _active_system()
    return render_template("player.html", system=system, fullscreen=True)


@bp.route("/content/<ctype>/<slug>")
def get_content_detail(ctype, slug):
    system = _active_system()
    res = system["resources"]

    if ctype == "monster":
        dir_path = res["monsters"]
    elif ctype == "spell":
        dir_path = res["spells"]
    elif ctype == "rule":
        dir_path = res["rules"]
    else:
        return '<div class="error">Tipo no válido</div>', 400

    metadata, html = get_markdown_detail(dir_path, slug)
    if not metadata:
        return '<div class="error">No encontrado</div>', 404

    return render_template("content_detail.html", metadata=metadata, contenido=html, type=ctype)
