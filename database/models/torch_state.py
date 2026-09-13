from extensions import db


class TorchState(db.Model):
    """
    Estado del contador de antorcha (AD&D2e y derivados) — singleton, igual
    que GameState. Guarda el tiempo acumulado de tramos anteriores
    (`elapsed_seconds`) más el instante en que empezó el tramo actual
    (`segment_started_at`, None si está en pausa/parado), para poder
    calcular el tiempo restante en cualquier momento sin depender de que
    nadie esté conectado mientras corre.
    """
    __tablename__ = "torch_states"

    id = db.Column(db.Integer, primary_key=True)
    is_running = db.Column(db.Boolean, default=False, nullable=False)
    duration_seconds = db.Column(db.Integer, default=3600, nullable=False)
    elapsed_seconds = db.Column(db.Integer, default=0, nullable=False)
    segment_started_at = db.Column(db.DateTime, nullable=True)
