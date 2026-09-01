from extensions import db
from database.models.equipo_item import EquipoItem, PnjCategoriaEquipo


def list_equipo(sistema: str = "adnd2e") -> list[EquipoItem]:
    return EquipoItem.query.filter_by(sistema=sistema).order_by(EquipoItem.nombre.asc()).all()


def get_or_create_item(nombre: str, descripcion: str | None = None, precio: float | None = None,
                        sistema: str = "adnd2e", categoria: str | None = None) -> EquipoItem:
    item = EquipoItem.query.filter_by(nombre=nombre.strip(), sistema=sistema).first()
    if item:
        return item
    item = EquipoItem(nombre=nombre.strip(), descripcion=descripcion, precio=precio, sistema=sistema,
                       categoria=categoria)
    db.session.add(item)
    db.session.commit()
    return item


def update_item(item_id: int, nombre: str | None = None, descripcion: str | None = None,
                 precio: float | None = None, categoria: str | None = None) -> EquipoItem | None:
    item = EquipoItem.query.get(item_id)
    if not item:
        return None
    if nombre is not None:
        item.nombre = nombre.strip()
    if descripcion is not None:
        item.descripcion = descripcion
    if precio is not None:
        item.precio = precio
    if categoria is not None:
        item.categoria = categoria
    db.session.commit()
    return item


def delete_item(item_id: int) -> bool:
    item = EquipoItem.query.get(item_id)
    if not item:
        return False
    PnjCategoriaEquipo.query.filter_by(equipo_id=item_id).delete()
    db.session.delete(item)
    db.session.commit()
    return True


def asignar_a_categoria(categoria_id: int, equipo_id: int, nivel_minimo: int = 1) -> PnjCategoriaEquipo:
    asignacion = PnjCategoriaEquipo.query.filter_by(categoria_id=categoria_id, equipo_id=equipo_id).first()
    if asignacion:
        asignacion.nivel_minimo = nivel_minimo
    else:
        asignacion = PnjCategoriaEquipo(categoria_id=categoria_id, equipo_id=equipo_id, nivel_minimo=nivel_minimo)
        db.session.add(asignacion)
    db.session.commit()
    return asignacion


def desasignar_de_categoria(categoria_id: int, equipo_id: int) -> bool:
    asignacion = PnjCategoriaEquipo.query.filter_by(categoria_id=categoria_id, equipo_id=equipo_id).first()
    if not asignacion:
        return False
    db.session.delete(asignacion)
    db.session.commit()
    return True


def list_asignaciones_categoria(categoria_id: int) -> list[PnjCategoriaEquipo]:
    return (
        PnjCategoriaEquipo.query
        .filter_by(categoria_id=categoria_id)
        .join(PnjCategoriaEquipo.equipo)
        .order_by(PnjCategoriaEquipo.nivel_minimo.asc())
        .all()
    )
