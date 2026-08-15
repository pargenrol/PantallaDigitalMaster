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
    """Plantilla inicial de ficha AD&D2e (rellenable luego con el editor de /sheet/player/<slug>)."""
    nombre = data.get("nombre") or ""
    clase = data.get("clase") or ""
    raza = data.get("raza") or ""
    nivel = data.get("nivel") or ""
    alineamiento = data.get("alineamiento") or ""
    thac0 = data.get("thac0") if data.get("thac0") is not None else ""
    ca = data.get("ca") if data.get("ca") is not None else ""
    hp_max = data.get("hp_max") if data.get("hp_max") is not None else ""
    experiencia = data.get("experiencia") if data.get("experiencia") is not None else ""
    deidad = data.get("deidad") or ""
    altura = data.get("altura") or ""
    peso = data.get("peso") or ""
    edad = data.get("edad") or ""
    ataques = data.get("ataques") or ""
    pericias = data.get("pericias") or ""
    pericias_armas = data.get("pericias_armas") or ""
    idiomas = data.get("idiomas") or ""
    conjuros = data.get("conjuros") or ""
    tesoro = data.get("tesoro") or ""
    st_muerte = data.get("st_muerte") if data.get("st_muerte") is not None else ""
    st_varita = data.get("st_varita") if data.get("st_varita") is not None else ""
    st_petrificacion = data.get("st_petrificacion") if data.get("st_petrificacion") is not None else ""
    st_aliento = data.get("st_aliento") if data.get("st_aliento") is not None else ""
    st_conjuros = data.get("st_conjuros") if data.get("st_conjuros") is not None else ""
    notas = data.get("notas") or ""
    titulo = f"{nombre} — {clase} {raza}".strip()
    if nivel:
        titulo += f" Nv.{nivel}"

    from systems.adnd2e_data import HABILIDADES_CLASE
    habilidades = HABILIDADES_CLASE.get(clase) or []
    habilidades_md = "\n".join(f"- {h}" for h in habilidades) if habilidades else ""

    conjuros_seccion = f"\n\n## Conjuros\n\n{conjuros}" if conjuros else ""

    return f"""# {titulo}

**Alineamiento:** {alineamiento} · **Deidad:** {deidad} · **Altura:** {altura} · **Peso:** {peso} · **Edad:** {edad}

## Combate

| GAC0 | CA | PG | PX | Ataques |
|------|----|----|----| --------|
| {thac0} | {ca} | {hp_max} | {experiencia} | {ataques} |

## Equipo


## Habilidades de clase

{habilidades_md}

## Pericias

**Armas:** {pericias_armas}

**No armas:** {pericias}

**Idiomas:** {idiomas}{conjuros_seccion}

## Tiradas de Salvación

| Muerte/Veneno | Varita | Petri./Polimorfia | Aliento | Conjuros |
|--------------|--------|--------|-------|---------|
| {st_muerte} | {st_varita} | {st_petrificacion} | {st_aliento} | {st_conjuros} |

## Tesoro

{tesoro}

## Notas

{notas}
"""


def _save_player(players_dir: str, slug: str, data: dict) -> None:
    os.makedirs(players_dir, exist_ok=True)
    filepath = os.path.join(players_dir, f"{slug}.md")

    # Preservar el cuerpo Markdown (ficha completa) si el fichero ya existe —
    # este endpoint solo edita los campos planos del frontmatter, nunca debe
    # pisar la ficha rica escrita a mano o desde /sheet.
    is_new = not os.path.exists(filepath)
    body = ""
    if not is_new:
        with open(filepath, "r", encoding="utf-8") as f:
            body = frontmatter.load(f).content
    elif "thac0" in data:
        # Solo sistemas AD&D2e (y familia) tienen thac0 en sus campos de jugador.
        body = _default_body_adnd2e(data)

    post = frontmatter.Post(body, **data)
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
