from extensions import db


class PantallaConfig(db.Model):
    """
    Programación de pantalla guardada: una lista con nombre de popups de
    referencia fijados (GAC0, una regla/conjuro/monstruo concreto...) junto a
    su posición en pantalla, para poder recuperar de golpe toda la
    disposición en vez de fijar cada uno a mano cada sesión.

    `paneles` es una lista de dicts, cada uno describiendo un panel fijado:
    {"tipo": "gac0" | "rule" | "spell" | "monster", "slug": str|None,
     "titulo": str, "x": int, "y": int}
    ("slug"/"titulo" no aplican a tipo "gac0", que se reconstruye desde
    datos ya cargados en el cliente, no desde una ficha markdown).
    """
    __tablename__ = "pantalla_configs"

    id = db.Column(db.Integer, primary_key=True)
    sistema = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    paneles = db.Column(db.JSON, nullable=False, default=list)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("sistema", "nombre", name="uq_pantalla_config_sistema_nombre"),
    )
