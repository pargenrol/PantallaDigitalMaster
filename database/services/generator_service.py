import random

from extensions import db
from database.models.generator import GeneratorTable, GeneratorEntry


def get_table_by_slug(slug: str) -> GeneratorTable | None:
    return GeneratorTable.query.filter_by(slug=slug).first()


def get_or_create_table(slug: str, nombre: str, sistema: str = "adnd2e", dado: int = 30) -> GeneratorTable:
    tabla = get_table_by_slug(slug)
    if tabla:
        return tabla
    tabla = GeneratorTable(slug=slug, nombre=nombre, sistema=sistema, dado=dado)
    db.session.add(tabla)
    db.session.commit()
    return tabla


def list_entries(slug: str) -> list[GeneratorEntry]:
    tabla = get_table_by_slug(slug)
    if not tabla:
        return []
    return tabla.entries


def add_entry(slug: str, texto: str) -> GeneratorEntry | None:
    tabla = get_table_by_slug(slug)
    if not tabla:
        return None
    max_orden = db.session.query(db.func.max(GeneratorEntry.orden)).filter_by(table_id=tabla.id).scalar() or 0
    entry = GeneratorEntry(table_id=tabla.id, texto=texto.strip(), orden=max_orden + 1, usado=False)
    db.session.add(entry)
    db.session.commit()
    return entry


def update_entry(entry_id: int, texto: str | None = None, usado: bool | None = None) -> GeneratorEntry | None:
    entry = GeneratorEntry.query.get(entry_id)
    if not entry:
        return None
    if texto is not None:
        entry.texto = texto.strip()
    if usado is not None:
        entry.usado = usado
    db.session.commit()
    return entry


def delete_entry(entry_id: int) -> bool:
    entry = GeneratorEntry.query.get(entry_id)
    if not entry:
        return False
    db.session.delete(entry)
    db.session.commit()
    return True


def reset_usados(slug: str) -> None:
    """Desmarca todas las entradas de una tabla como no-usadas (para empezar una sesión nueva)."""
    tabla = get_table_by_slug(slug)
    if not tabla:
        return
    for e in tabla.entries:
        e.usado = False
    db.session.commit()


def roll(slug: str, evitar_usadas: bool = True) -> GeneratorEntry | None:
    """
    Tira sobre las entradas de la tabla y devuelve una al azar. Si
    evitar_usadas es True y quedan entradas sin usar, solo elige entre esas
    (para no repetir en la misma sesión); si todas están usadas, tira sobre
    el total. Marca la entrada elegida como usada.
    """
    tabla = get_table_by_slug(slug)
    if not tabla or not tabla.entries:
        return None

    pool = [e for e in tabla.entries if not e.usado] if evitar_usadas else list(tabla.entries)
    if not pool:
        pool = list(tabla.entries)

    elegido = random.choice(pool)
    elegido.usado = True
    db.session.commit()
    return elegido
