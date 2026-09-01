from extensions import db
from database.models.screen_config import PantallaConfig


def list_configs(sistema: str) -> list[PantallaConfig]:
    return PantallaConfig.query.filter_by(sistema=sistema).order_by(PantallaConfig.nombre.asc()).all()


def get_config(config_id: int) -> PantallaConfig | None:
    return PantallaConfig.query.get(config_id)


def save_config(sistema: str, nombre: str, paneles: list) -> PantallaConfig:
    """Crea la configuración, o la sobrescribe si ya existe una con ese
    nombre en ese sistema (guardar con el mismo nombre = actualizar)."""
    nombre = nombre.strip()
    config = PantallaConfig.query.filter_by(sistema=sistema, nombre=nombre).first()
    if config:
        config.paneles = paneles
    else:
        config = PantallaConfig(sistema=sistema, nombre=nombre, paneles=paneles)
        db.session.add(config)
    db.session.commit()
    return config


def delete_config(config_id: int) -> bool:
    config = PantallaConfig.query.get(config_id)
    if not config:
        return False
    db.session.delete(config)
    db.session.commit()
    return True
