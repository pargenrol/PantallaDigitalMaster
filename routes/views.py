import base64
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

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
    players = load_markdown_content(res.get("players", ""))

    return render_template(
        "master.html",
        system=system,
        characters=characters_data,
        current_turn=game_state.current_turn,
        grimorio_monsters=monsters,
        grimorio_spells=spells,
        grimorio_rules=rules,
        grimorio_players=players,
    )


@bp.route("/player")
def player():
    system = _active_system()
    return render_template("player.html", system=system)


@bp.route("/player/screen")
def player_screen():
    system = _active_system()
    return render_template("player.html", system=system, fullscreen=True)


# ── Tablet views ─────────────────────────────────────────────────────────────

@bp.route("/view")
def tablet_dashboard():
    system = _active_system()
    host = request.host  # ip:puerto
    return render_template("views/tablet_dashboard.html", system=system, host=host)


@bp.route("/view/initiative")
def tablet_initiative():
    if "active_system" not in session:
        return redirect(url_for("views.select_system"))
    system = _active_system()
    return render_template("views/initiative_tablet.html", system=system)


@bp.route("/view/rules")
def tablet_rules():
    if "active_system" not in session:
        return redirect(url_for("views.select_system"))
    system = _active_system()
    res = system["resources"]
    monsters = load_markdown_content(res["monsters"])
    spells   = load_markdown_content(res["spells"])
    rules    = load_markdown_content(res["rules"])
    return render_template(
        "views/rules_tablet.html",
        system=system,
        grimorio_monsters=monsters,
        grimorio_spells=spells,
        grimorio_rules=rules,
    )


@bp.route("/view/whiteboard")
def tablet_whiteboard():
    system = _active_system()
    return render_template("views/whiteboard_tablet.html", system=system)


@bp.route("/view/audio")
def tablet_audio():
    system = _active_system()
    return render_template("views/audio_tablet.html", system=system)


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


@bp.route("/api/monsters/<slug>/portrait", methods=["POST"])
def save_monster_portrait(slug):
    system = _active_system()
    system_id = session.get("active_system", DEFAULT_SYSTEM)
    data = request.get_json(silent=True) or {}
    img_data = data.get("image", "")

    if not img_data:
        return jsonify({"error": "No image data"}), 400

    # Strip data URL prefix (data:image/jpeg;base64,...)
    if "," in img_data:
        img_data = img_data.split(",", 1)[1]

    # Save image file
    img_dir = Path(current_app.root_path) / "static" / "img" / "monsters" / system_id
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"{slug}.jpeg"
    img_path.write_bytes(base64.b64decode(img_data))

    portrait_url = f"/static/img/monsters/{system_id}/{slug}.jpeg"

    # Update portrait_path in the markdown frontmatter
    res = system["resources"]
    md_path = Path(res["monsters"]) / f"{slug}.md"
    if md_path.exists():
        content = md_path.read_text(encoding="utf-8")
        if re.search(r"^portrait_path:", content, re.MULTILINE):
            content = re.sub(r"^portrait_path:.*$", f"portrait_path: {portrait_url}", content, flags=re.MULTILINE)
        else:
            # Insert after the opening --- line
            content = re.sub(r"^---\n", f"---\nportrait_path: {portrait_url}\n", content, count=1)
        md_path.write_text(content, encoding="utf-8")

    return jsonify({"ok": True, "portrait_path": portrait_url})
