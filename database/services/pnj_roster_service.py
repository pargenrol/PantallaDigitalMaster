import json

from extensions import db
from database.models.pnj_roster import PnjRosterEntry


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
