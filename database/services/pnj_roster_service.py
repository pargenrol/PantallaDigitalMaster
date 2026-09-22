import json

from extensions import db
from database.models.pnj_roster import PnjRosterEntry
from systems.registry import get_system
from utils.markdown_content import load_markdown_content, get_markdown_detail, parse_dg


def list_grimoire_pnjs(sistema: str = "adnd2e") -> list[dict]:
    """PNJs de campaña ya escritos a mano en el grimorio (frontmatter
    `pnj_campana: true`) — personajes con historia propia como Silas o
    Madre Salmuera, a diferencia de los generados al azar y guardados en
    PnjRosterEntry. Se devuelven con la misma forma que _entry_to_dict()
    para que el frontend los pinte igual, con id string "grimoire:<slug>"
    para distinguirlos de los ids enteros del roster."""
    system = get_system(sistema)
    monsters_dir = (system.get("resources") or {}).get("monsters")
    if not monsters_dir:
        return []

    result = []
    for meta in load_markdown_content(monsters_dir):
        if not meta.get("pnj_campana"):
            continue
        slug = meta["slug"]
        _, html = get_markdown_detail(monsters_dir, slug)
        stats = {}
        if meta.get("ca") is not None:
            stats["ca"] = meta["ca"]
        if meta.get("thac0") is not None:
            stats["thac0"] = meta["thac0"]
        result.append({
            "id": f"grimoire:{slug}",
            "slug": slug,
            "sistema": sistema,
            "nombre": meta.get("nombre", slug),
            "categoria": "PNJ de campaña",
            "dg": parse_dg(meta.get("dg")) or 1,
            "genero": "—",
            "stats": stats,
            "equipo": [],
            "rasgos": [],
            "descripcion": html or "",
            "notas": "",
            "portrait_path": meta.get("portrait_path"),
            "source": "grimoire",
        })
    return result


def get_grimoire_pnj(sistema: str, slug: str) -> dict | None:
    system = get_system(sistema)
    monsters_dir = (system.get("resources") or {}).get("monsters")
    if not monsters_dir:
        return None
    meta, html = get_markdown_detail(monsters_dir, slug)
    if not meta or not meta.get("pnj_campana"):
        return None
    stats = {}
    if meta.get("ca") is not None:
        stats["ca"] = meta["ca"]
    if meta.get("thac0") is not None:
        stats["thac0"] = meta["thac0"]
    return {
        "id": f"grimoire:{slug}",
        "slug": slug,
        "sistema": sistema,
        "nombre": meta.get("nombre", slug),
        "categoria": "PNJ de campaña",
        "dg": parse_dg(meta.get("dg")) or 1,
        "genero": "—",
        "stats": stats,
        "equipo": [],
        "rasgos": [],
        "descripcion": html or "",
        "notas": "",
        "portrait_path": meta.get("portrait_path"),
        "source": "grimoire",
    }


def list_roster(sistema: str = "adnd2e") -> list[PnjRosterEntry]:
    return (
        PnjRosterEntry.query
        .filter_by(sistema=sistema)
        .order_by(PnjRosterEntry.time_created.desc())
        .all()
    )


def get_roster_entry(entry_id: int) -> PnjRosterEntry | None:
    return PnjRosterEntry.query.get(entry_id)


def add_roster_entry(nombre: str, categoria_nombre: str, dg: int, genero: str,
                      stats: dict, equipo: list[str], rasgos: list[str] | None = None,
                      descripcion: str = "", notas: str = "",
                      sistema: str = "adnd2e") -> PnjRosterEntry:
    entry = PnjRosterEntry(
        sistema=sistema,
        nombre=nombre,
        categoria_nombre=categoria_nombre,
        dg=dg,
        genero=genero,
        stats_snapshot=json.dumps(stats or {}, ensure_ascii=False),
        equipo_snapshot=json.dumps(equipo or [], ensure_ascii=False),
        rasgos_snapshot=json.dumps(rasgos or [], ensure_ascii=False),
        descripcion=descripcion or "",
        notas=notas or "",
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def update_roster_entry(entry_id: int, notas: str | None = None,
                         descripcion: str | None = None) -> PnjRosterEntry | None:
    entry = PnjRosterEntry.query.get(entry_id)
    if not entry:
        return None
    if notas is not None:
        entry.notas = notas
    if descripcion is not None:
        entry.descripcion = descripcion
    db.session.commit()
    return entry


def delete_roster_entry(entry_id: int) -> bool:
    entry = PnjRosterEntry.query.get(entry_id)
    if not entry:
        return False
    db.session.delete(entry)
    db.session.commit()
    return True
