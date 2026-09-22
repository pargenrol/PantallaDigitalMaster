from extensions import db
from database.models.system_state import SystemState
from systems.registry import DEFAULT_SYSTEM


def get_active_system_id() -> str:
    """Devuelve el id del sistema activo compartido (crea la fila con el
    valor por defecto la primera vez que se pide)."""
    state = SystemState.query.get(1)
    if state is None:
        state = SystemState(id=1, system_id=DEFAULT_SYSTEM)
        db.session.add(state)
        db.session.commit()
    return state.system_id


def set_active_system_id(system_id: str) -> None:
    """Cambia el sistema activo compartido, visible para cualquier
    dispositivo (máster, jugador, tablets de apoyo) sin selección propia."""
    state = SystemState.query.get(1)
    if state is None:
        state = SystemState(id=1, system_id=system_id)
        db.session.add(state)
    else:
        state.system_id = system_id
    db.session.commit()
