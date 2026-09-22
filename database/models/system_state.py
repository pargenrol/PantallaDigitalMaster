from extensions import db


class SystemState(db.Model):
    """
    Sistema de reglas activo (AD&D2e, D&D5e, etc.) — singleton, igual que
    GameState/TorchState. Antes vivía en `session["active_system"]` (por
    navegador), lo que hacía que cada dispositivo (tablet de apoyo, pantalla
    de jugador...) pudiera acabar viendo un sistema distinto al del máster.
    """
    __tablename__ = "system_states"

    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.String(50), default="dnd5e", nullable=False)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
