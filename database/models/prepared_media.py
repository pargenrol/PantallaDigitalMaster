from extensions import db


class PreparedMedia(db.Model):
    """Recurso multimedia preparado de antemano (audio, vídeo, html o
    imagen) con una descripción y una ruta, para proyectarlo a la pantalla
    de jugadores con un clic. Compartido entre todos los sistemas, igual
    que la biblioteca de YouTube."""
    __tablename__ = "prepared_media"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # "audio" | "video" | "html" | "imagen"
    ruta = db.Column(db.String(500), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
