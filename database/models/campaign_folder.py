from extensions import db


class CampaignFolder(db.Model):
    """
    Carpeta de campaña registrada por el usuario para el explorador de
    Campañas — una raíz de exploración más, además de la raíz "por defecto"
    (`system["vault_partidas_path"]`). Solo guarda la ruta; nunca borra ni
    crea contenido dentro salvo la propia carpeta si no existe todavía.
    """
    __tablename__ = "campaign_folders"

    id = db.Column(db.Integer, primary_key=True)
    sistema = db.Column(db.String(50), nullable=False, default="adnd2e")
    nombre = db.Column(db.String(150), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("sistema", "path", name="uq_campaign_sistema_path"),
    )
