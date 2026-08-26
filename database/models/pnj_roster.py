import json

from extensions import db


class PnjRosterEntry(db.Model):
    """
    Un PNJ generado y guardado por el usuario desde el generador de PNJ
    Rápido. Es una foto fija (snapshot) del resultado en el momento de
    guardarlo: no tiene FK a PnjCategoria para que editar o borrar la
    categoría no rompa nunca los PNJs ya guardados. Solo `notas` y
    `descripcion` se pueden editar después de guardado.
    """
    __tablename__ = "pnj_roster_entries"

    id = db.Column(db.Integer, primary_key=True)
    sistema = db.Column(db.String(50), nullable=False, default="adnd2e")
    nombre = db.Column(db.String(150), nullable=False)
    categoria_nombre = db.Column(db.String(100), nullable=False)
    dg = db.Column(db.Integer, nullable=False, default=1)
    genero = db.Column(db.String(20), nullable=False, default="aleatorio")
    stats_snapshot = db.Column(db.Text, nullable=False, default="{}")
    equipo_snapshot = db.Column(db.Text, nullable=False, default="[]")
    rasgos_snapshot = db.Column(db.Text, nullable=True, default="[]")
    descripcion = db.Column(db.Text, nullable=True, default="")
    notas = db.Column(db.Text, nullable=True, default="")
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def stats_dict(self) -> dict:
        try:
            return json.loads(self.stats_snapshot or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def equipo_lista(self) -> list[str]:
        try:
            return json.loads(self.equipo_snapshot or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def rasgos_lista(self) -> list[str]:
        try:
            return json.loads(self.rasgos_snapshot or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
