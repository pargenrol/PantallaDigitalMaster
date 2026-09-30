from extensions import db
from database.models.prepared_media import PreparedMedia


def list_media() -> list[PreparedMedia]:
    return PreparedMedia.query.order_by(PreparedMedia.nombre.asc()).all()


def add_media(nombre: str, tipo: str, ruta: str, descripcion: str = "") -> PreparedMedia:
    media = PreparedMedia(nombre=nombre, tipo=tipo, ruta=ruta, descripcion=descripcion)
    db.session.add(media)
    db.session.commit()
    return media


def delete_media(media_id: int) -> bool:
    media = PreparedMedia.query.get(media_id)
    if not media:
        return False
    db.session.delete(media)
    db.session.commit()
    return True
