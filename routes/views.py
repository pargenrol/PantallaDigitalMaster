import base64
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from database.services.character_service import get_active_characters
from database.services.game_state_service import get_game_state
from systems.registry import get_all_systems, get_system, DEFAULT_SYSTEM
from version import VERSION
from utils.markdown_content import load_markdown_content, get_markdown_detail, parse_dg

bp = Blueprint("views", __name__)


def _active_system() -> dict:
    return get_system(session.get("active_system", DEFAULT_SYSTEM))


def _content_dir(system: dict, ctype: str) -> str | None:
    res = system["resources"]
    if ctype == "monster":
        return res["monsters"]
    if ctype == "spell":
        return res["spells"]
    if ctype == "rule":
        return res["rules"]
    if ctype == "player":
        return res.get("players")
    return None


def _delete_from_grimoire_index(file_type: str, slug: str):
    try:
        from utils.rag_indexer import get_chroma_client, get_collection, COLLECTION_GRIMOIRE
        client = get_chroma_client()
        col = get_collection(client, COLLECTION_GRIMOIRE)
        col.delete(where={"source": f"grimoire/{file_type}/{slug}.md"})
    except Exception as e:
        print(f"[content] Error eliminando índice de {slug}: {e}")


def _reindex_grimoire_file(file_type: str, slug: str, dir_path: str, system_id: str):
    import threading

    def _run():
        try:
            import frontmatter as fm
            from utils.rag_indexer import (
                get_chroma_client, get_collection, COLLECTION_GRIMOIRE,
                chunk_text, embed, make_id,
            )
            filepath = Path(dir_path) / f"{slug}.md"
            post = fm.load(str(filepath))
            text = post.content.strip()
            nombre = post.metadata.get("nombre") or post.metadata.get("title") or slug

            client = get_chroma_client()
            col = get_collection(client, COLLECTION_GRIMOIRE)
            col.delete(where={"source": f"grimoire/{file_type}/{slug}.md"})
            if not text:
                return

            chunks = chunk_text(text)
            ids, embeddings, documents, metadatas = [], [], [], []
            for i, chunk in enumerate(chunks):
                ids.append(make_id(f"grimoire/{file_type}/{slug}", 0, i))
                embeddings.append(embed(chunk))
                documents.append(chunk)
                metadatas.append({
                    "source": f"grimoire/{file_type}/{slug}.md",
                    "type": file_type,
                    "slug": slug,
                    "name": nombre,
                    "system": system_id,
                    "page": 0,
                    "chunk_index": i,
                })
            if ids:
                col.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        except Exception as e:
            print(f"[content] Error reindexando {slug}: {e}")

    threading.Thread(target=_run, daemon=True).start()


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
    if system["id"] in ADND2E_FAMILY:
        for m in monsters:
            m["dg_num"] = parse_dg(m.get("dg"))
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
        version=VERSION,
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
    if system["id"] in ADND2E_FAMILY:
        for m in monsters:
            m["dg_num"] = parse_dg(m.get("dg"))
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
    dir_path = _content_dir(system, ctype)
    if not dir_path:
        return '<div class="error">Tipo no válido</div>', 400

    metadata, html = get_markdown_detail(dir_path, slug)
    if not metadata:
        return '<div class="error">No encontrado</div>', 404

    return render_template("content_detail.html", metadata=metadata, contenido=html, type=ctype)


ADND2E_FAMILY = {"adnd2e", "darksun", "greyhawk", "forgotten_realms", "ravenloft_adnd"}


@bp.route("/sheet/player/<slug>")
def player_sheet(slug):
    """Ficha de personaje independiente, pensada para imprimir — sin el resto de la interfaz del máster."""
    system = _active_system()
    players_dir = system["resources"].get("players")
    if not players_dir:
        return '<div class="error">Este sistema no tiene jugadores</div>', 400

    metadata, html = get_markdown_detail(players_dir, slug)
    if not metadata:
        return '<div class="error">Ficha no encontrada</div>', 404

    derivados = None
    if system["id"] in ADND2E_FAMILY:
        from systems.adnd2e_data import (
            FUE_DERIVADOS, DES_DERIVADOS, CON_DERIVADOS, INT_DERIVADOS,
            SAB_DERIVADOS, CAR_DERIVADOS, derivados_caracteristica,
        )
        derivados = {
            "fue": derivados_caracteristica(FUE_DERIVADOS, metadata.get("fue")),
            "des": derivados_caracteristica(DES_DERIVADOS, metadata.get("des")),
            "con": derivados_caracteristica(CON_DERIVADOS, metadata.get("con")),
            "int": derivados_caracteristica(INT_DERIVADOS, metadata.get("int")),
            "sab": derivados_caracteristica(SAB_DERIVADOS, metadata.get("sab")),
            "car": derivados_caracteristica(CAR_DERIVADOS, metadata.get("car")),
        }

    return render_template("player_sheet.html", metadata=metadata, contenido=html, system=system, slug=slug, derivados=derivados)


@bp.route("/api/content/<ctype>/<slug>", methods=["GET"])
def get_content_raw(ctype, slug):
    """Devuelve el markdown crudo (frontmatter + cuerpo) para editar."""
    system = _active_system()
    dir_path = _content_dir(system, ctype)
    if not dir_path:
        return jsonify({"error": "Tipo no válido"}), 400

    filepath = Path(dir_path) / f"{slug}.md"
    if not filepath.exists():
        return jsonify({"error": "No encontrado"}), 404

    return jsonify({"content": filepath.read_text(encoding="utf-8"), "slug": slug})


@bp.route("/api/content/<ctype>/<slug>", methods=["PUT"])
def update_content(ctype, slug):
    """Sobrescribe una ficha existente con contenido markdown editado."""
    system = _active_system()
    dir_path = _content_dir(system, ctype)
    if not dir_path:
        return jsonify({"error": "Tipo no válido"}), 400

    filepath = Path(dir_path) / f"{slug}.md"
    if not filepath.exists():
        return jsonify({"error": "No encontrado"}), 404

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content requerido"}), 400

    try:
        import frontmatter as _fm
        _fm.loads(content)
    except Exception as e:
        return jsonify({"error": f"YAML inválido en el frontmatter: {e}"}), 400

    filepath.write_text(content, encoding="utf-8")
    _reindex_grimoire_file(ctype, slug, dir_path, system["id"])

    import frontmatter as _fm2
    metadata = dict(_fm2.loads(content).metadata or {})
    return jsonify({"ok": True, "slug": slug, "metadata": metadata})


@bp.route("/api/content/<ctype>/<slug>", methods=["DELETE"])
def delete_content(ctype, slug):
    """Elimina una ficha por completo (fichero + índice RAG)."""
    system = _active_system()
    dir_path = _content_dir(system, ctype)
    if not dir_path:
        return jsonify({"error": "Tipo no válido"}), 400

    filepath = Path(dir_path) / f"{slug}.md"
    if not filepath.exists():
        return jsonify({"error": "No encontrado"}), 404

    filepath.unlink()
    _delete_from_grimoire_index(ctype, slug)

    return jsonify({"ok": True, "slug": slug})


VIDEO_PORTRAIT_EXTENSIONS = {".mp4", ".webm", ".mov"}


@bp.route("/api/monsters/<slug>/portrait", methods=["POST"])
def save_monster_portrait(slug):
    system = _active_system()
    system_id = session.get("active_system", DEFAULT_SYSTEM)
    img_dir = Path(current_app.root_path) / "static" / "img" / "monsters" / system_id
    img_dir.mkdir(parents=True, exist_ok=True)

    video_file = request.files.get("video")
    if video_file:
        ext = Path(video_file.filename or "").suffix.lower()
        if ext not in VIDEO_PORTRAIT_EXTENSIONS:
            return jsonify({"error": "Formato de vídeo no soportado"}), 400
        # Borrar retratos previos (imagen o vídeo con otra extensión) antes de guardar el nuevo
        for old in img_dir.glob(f"{slug}.*"):
            old.unlink()
        portrait_path = img_dir / f"{slug}{ext}"
        video_file.save(portrait_path)
        portrait_url = f"/static/img/monsters/{system_id}/{slug}{ext}"
    else:
        data = request.get_json(silent=True) or {}
        img_data = data.get("image", "")
        if not img_data:
            return jsonify({"error": "No image data"}), 400

        # Strip data URL prefix (data:image/jpeg;base64,...)
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]

        # Borrar retratos previos (p.ej. un vídeo anterior) antes de guardar la nueva imagen
        for old in img_dir.glob(f"{slug}.*"):
            old.unlink()
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


@bp.route("/api/players/<slug>/portrait", methods=["POST"])
def save_player_portrait(slug):
    system = _active_system()
    system_id = session.get("active_system", DEFAULT_SYSTEM)
    players_dir = system["resources"].get("players")
    if not players_dir:
        return jsonify({"error": "Este sistema no tiene jugadores"}), 400

    img_dir = Path(current_app.root_path) / "static" / "img" / "players" / system_id
    img_dir.mkdir(parents=True, exist_ok=True)

    video_file = request.files.get("video")
    if video_file:
        ext = Path(video_file.filename or "").suffix.lower()
        if ext not in VIDEO_PORTRAIT_EXTENSIONS:
            return jsonify({"error": "Formato de vídeo no soportado"}), 400
        for old in img_dir.glob(f"{slug}.*"):
            old.unlink()
        portrait_path = img_dir / f"{slug}{ext}"
        video_file.save(portrait_path)
        portrait_url = f"/static/img/players/{system_id}/{slug}{ext}"
    else:
        data = request.get_json(silent=True) or {}
        img_data = data.get("image", "")
        if not img_data:
            return jsonify({"error": "No image data"}), 400

        if "," in img_data:
            img_data = img_data.split(",", 1)[1]

        for old in img_dir.glob(f"{slug}.*"):
            old.unlink()
        img_path = img_dir / f"{slug}.jpeg"
        img_path.write_bytes(base64.b64decode(img_data))
        portrait_url = f"/static/img/players/{system_id}/{slug}.jpeg"

    md_path = Path(players_dir) / f"{slug}.md"
    if md_path.exists():
        content = md_path.read_text(encoding="utf-8")
        if re.search(r"^portrait_path:", content, re.MULTILINE):
            content = re.sub(r"^portrait_path:.*$", f"portrait_path: {portrait_url}", content, flags=re.MULTILINE)
        else:
            content = re.sub(r"^---\n", f"---\nportrait_path: {portrait_url}\n", content, count=1)
        md_path.write_text(content, encoding="utf-8")

    return jsonify({"ok": True, "portrait_path": portrait_url})
