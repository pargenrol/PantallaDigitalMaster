from pathlib import Path

from extensions import db
from database.models.campaign_folder import CampaignFolder


def list_folders(sistema: str = "adnd2e") -> list[CampaignFolder]:
    return (
        CampaignFolder.query
        .filter_by(sistema=sistema)
        .order_by(CampaignFolder.nombre.asc())
        .all()
    )


def get_folder(folder_id: int) -> CampaignFolder | None:
    return CampaignFolder.query.get(folder_id)


def add_folder(sistema: str, nombre: str, path: str) -> CampaignFolder:
    """Crea la carpeta en disco si no existe (para que un usuario nuevo no
    tenga que crearla a mano antes) y registra la ruta."""
    Path(path).mkdir(parents=True, exist_ok=True)
    folder = CampaignFolder(sistema=sistema, nombre=nombre.strip(), path=path)
    db.session.add(folder)
    db.session.commit()
    return folder


def delete_folder(folder_id: int) -> bool:
    """Desregistra la carpeta — nunca borra los ficheros dentro."""
    folder = CampaignFolder.query.get(folder_id)
    if not folder:
        return False
    db.session.delete(folder)
    db.session.commit()
    return True
