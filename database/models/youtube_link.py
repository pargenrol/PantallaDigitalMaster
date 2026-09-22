from extensions import db


class YoutubeLink(db.Model):
    """Enlace de YouTube guardado por el usuario para reproducir solo el
    audio de fondo desde el panel de Audio, sin tener que pegar la URL cada
    vez. Compartido entre todos los sistemas (no depende de la partida)."""
    __tablename__ = "youtube_links"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
