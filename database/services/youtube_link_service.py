from extensions import db
from database.models.youtube_link import YoutubeLink


def list_links() -> list[YoutubeLink]:
    return YoutubeLink.query.order_by(YoutubeLink.nombre.asc()).all()


def add_link(nombre: str, url: str) -> YoutubeLink:
    link = YoutubeLink(nombre=nombre, url=url)
    db.session.add(link)
    db.session.commit()
    return link


def delete_link(link_id: int) -> bool:
    link = YoutubeLink.query.get(link_id)
    if not link:
        return False
    db.session.delete(link)
    db.session.commit()
    return True
