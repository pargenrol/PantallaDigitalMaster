import os
import re
import frontmatter

from flask import Blueprint, current_app, jsonify, request, session

from systems.registry import get_system, DEFAULT_SYSTEM
from utils.markdown_content import load_markdown_content

bp = Blueprint("api_players", __name__, url_prefix="/api/players")


@bp.get("/character-data/<system_id>")
def api_character_data(system_id: str):
    """Datos estructurados (razas/clases/pericias) para asistir la creación de
    personajes. De momento solo existe el dataset de AD&D2e (y su familia:
    darksun, greyhawk, forgotten_realms, ravenloft_adnd comparten esquema)."""
    ADND2E_FAMILY = {"adnd2e", "darksun", "greyhawk", "forgotten_realms", "ravenloft_adnd"}
    if system_id not in ADND2E_FAMILY:
        return jsonify({"available": False})

    from systems.adnd2e_data import (
        RAZAS_ADND2E, CLASES_ADND2E, PERICIAS_NO_ARMA, GRUPOS_PERICIA_POR_CLASE,
        GAC0_POR_NIVEL, PG_INFO_POR_GRUPO, CON_MOD_PG, SLOTS_ARMA_POR_GRUPO,
        ARMAS_ADND2E, IDIOMAS_POR_INT, HABILIDADES_CLASE, CONJUROS_ADND2E,
        CLASES_CONJURADORAS, CONJUROS_SLOTS_MAGO, CONJUROS_SLOTS_CLERIGO,
    )

    return jsonify({
        "available": True,
        "razas": RAZAS_ADND2E,
        "clases": CLASES_ADND2E,
        "pericias": PERICIAS_NO_ARMA,
        "grupos_por_clase": GRUPOS_PERICIA_POR_CLASE,
        "gac0_por_nivel": GAC0_POR_NIVEL,
        "pg_info_por_grupo": PG_INFO_POR_GRUPO,
        "con_mod_pg": CON_MOD_PG,
        "slots_arma_por_grupo": SLOTS_ARMA_POR_GRUPO,
        "armas": ARMAS_ADND2E,
        "idiomas_por_int": IDIOMAS_POR_INT,
        "habilidades_clase": HABILIDADES_CLASE,
        "conjuros": CONJUROS_ADND2E,
        "clases_conjuradoras": CLASES_CONJURADORAS,
        "conjuros_slots_mago": CONJUROS_SLOTS_MAGO,
        "conjuros_slots_clerigo": CONJUROS_SLOTS_CLERIGO,
    })


@bp.get("/catalogo-armas")
def api_catalogo_armas():
    """Catálogo de armas del Manual de Jugador AD&D2e (Tabla de Armas), para
    autorrellenar filas de la tabla 'Armas de combate' de la ficha. Solo trae
    los datos propios del arma (no #AT/Aj.daño/GACO, que dependen del
    personaje, no del arma)."""
    import json
    path = os.path.join(current_app.root_path, "resources", "adnd2e", "reference",
                         "armas_armaduras_manual.json")
    if not os.path.exists(path):
        return jsonify({"armas": []})

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    alcances = {a["nombre"]: a for a in data.get("alcance_armas_proyectil_metros", {}).get("items", [])}

    armas = []
    for a in data.get("armas", []):
        alcance = alcances.get(a["nombre"])
        alcance_txt = ""
        if alcance:
            alcance_txt = f"{alcance.get('corto') or ''}/{alcance.get('medio') or ''}/{alcance.get('largo') or ''}"
        armas.append({
            "arma": a["nombre"],
            "peso": a.get("peso_kg"),
            "talla": a.get("tamaño"),
            "tipo": a.get("tipo"),
            "velocidad": a.get("velocidad"),
            "dano_pm_g": f"{a.get('dano_pm', '')}/{a.get('dano_g', '')}",
            "alcance": alcance_txt,
        })

    return jsonify({"armas": armas})


def _players_dir() -> str:
    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    return system["resources"].get("players", "")


def _slug(nombre: str) -> str:
    s = nombre.lower().strip()
    s = re.sub(r"[áàä]", "a", s)
    s = re.sub(r"[éèë]", "e", s)
    s = re.sub(r"[íìï]", "i", s)
    s = re.sub(r"[óòö]", "o", s)
    s = re.sub(r"[úùü]", "u", s)
    s = re.sub(r"[ñ]", "n", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _default_body_adnd2e(data: dict) -> str:
    """Cuerpo markdown inicial de ficha AD&D2e (rellenable luego con el editor
    de /sheet/player/<slug>). Solo lleva "Habilidades de clase" (calculado a
    partir de la clase, no hay un campo estructurado equivalente en la ficha)
    — todo lo demás (identidad, combate, salvaciones, pericias, tesoro,
    notas...) ya tiene su propio apartado estructurado en player_sheet.html a
    partir del frontmatter, y repetirlo aquí solo duplicaba la ficha."""
    clase = data.get("clase") or ""

    from systems.adnd2e_data import HABILIDADES_CLASE
    habilidades = HABILIDADES_CLASE.get(clase) or []
    if not habilidades:
        return ""
    habilidades_md = "\n".join(f"- {h}" for h in habilidades)

    return f"""## Habilidades de clase

{habilidades_md}
"""


def _save_player(players_dir: str, slug: str, data: dict) -> None:
    os.makedirs(players_dir, exist_ok=True)
    filepath = os.path.join(players_dir, f"{slug}.md")

    # Preservar el cuerpo Markdown (ficha completa) si el fichero ya existe —
    # este endpoint solo edita los campos planos del frontmatter, nunca debe
    # pisar la ficha rica escrita a mano o desde /sheet.
    is_new = not os.path.exists(filepath)
    body = ""
    metadata = {}
    if not is_new:
        with open(filepath, "r", encoding="utf-8") as f:
            existing = frontmatter.load(f)
        body = existing.content
        # Conserva campos que no gestiona este formulario (p.ej. portrait_path,
        # escrito por el endpoint de subida de imagen) en vez de perderlos.
        metadata = dict(existing.metadata)
    elif "thac0" in data:
        # Solo sistemas AD&D2e (y familia) tienen thac0 en sus campos de jugador.
        body = _default_body_adnd2e(data)

    metadata.update(data)
    post = frontmatter.Post(body, **metadata)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


@bp.get("")
def api_get_players():
    players_dir = _players_dir()
    players = load_markdown_content(players_dir)
    return jsonify({"success": True, "players": players})


@bp.post("")
def api_create_player():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"success": False, "error": "nombre requerido"}), 400

    players_dir = _players_dir()
    slug = _slug(nombre)

    filepath = os.path.join(players_dir, f"{slug}.md")
    if os.path.exists(filepath):
        return jsonify({"success": False, "error": "Ya existe un jugador con ese nombre"}), 409

    _save_player(players_dir, slug, data)
    return jsonify({"success": True, "slug": slug})


@bp.put("/<slug>")
def api_update_player(slug: str):
    data = request.get_json(silent=True) or {}
    players_dir = _players_dir()
    filepath = os.path.join(players_dir, f"{slug}.md")

    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Jugador no encontrado"}), 404

    _save_player(players_dir, slug, data)
    return jsonify({"success": True})


@bp.delete("/<slug>")
def api_delete_player(slug: str):
    players_dir = _players_dir()
    filepath = os.path.join(players_dir, f"{slug}.md")

    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Jugador no encontrado"}), 404

    os.remove(filepath)
    return jsonify({"success": True})
