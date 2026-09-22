from datetime import datetime, timezone

from extensions import db
from database.models.torch_state import TorchState


def _now():
    return datetime.now(timezone.utc)


def get_torch_state() -> TorchState:
    """Devuelve el singleton de TorchState, creándolo con valores por
    defecto (parado, 60 minutos) si todavía no existe."""
    state = TorchState.query.get(1)
    if state is None:
        state = TorchState(id=1, is_running=False, duration_seconds=3600, elapsed_seconds=0)
        db.session.add(state)
        db.session.commit()
    return state


def get_remaining_seconds(state: TorchState) -> int:
    """Segundos restantes ahora mismo, sin mutar el estado."""
    elapsed = state.elapsed_seconds
    if state.is_running and state.segment_started_at:
        started = state.segment_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed += int((_now() - started).total_seconds())
    return max(0, state.duration_seconds - elapsed)


def to_dict(state: TorchState) -> dict:
    remaining = get_remaining_seconds(state)
    # Si se agotó el tiempo estando en marcha, se refleja como parada al
    # consultarla (sin necesidad de que nadie llame a stop() a tiempo).
    running = state.is_running and remaining > 0
    return {
        "is_running": running,
        "duration_seconds": state.duration_seconds,
        "remaining_seconds": remaining,
    }


def start(duration_seconds: int = 3600) -> TorchState:
    state = get_torch_state()
    state.duration_seconds = duration_seconds
    state.elapsed_seconds = 0
    state.is_running = True
    state.segment_started_at = _now()
    db.session.commit()
    return state


def pause(state: TorchState | None = None) -> TorchState:
    state = state or get_torch_state()
    if state.is_running:
        state.elapsed_seconds = state.duration_seconds - get_remaining_seconds(state)
        state.is_running = False
        state.segment_started_at = None
        db.session.commit()
    return state


def resume(state: TorchState | None = None) -> TorchState:
    state = state or get_torch_state()
    if not state.is_running and state.elapsed_seconds < state.duration_seconds:
        state.is_running = True
        state.segment_started_at = _now()
        db.session.commit()
    return state


def adjust(delta_seconds: int, state: TorchState | None = None) -> TorchState:
    """Suma o resta tiempo a la antorcha activa (en marcha o en pausa), sin
    tocar elapsed_seconds/segment_started_at — el restante siempre se
    recalcula como duration - elapsed, así que cambiar duration_seconds
    directamente ajusta el restante tanto si está corriendo como si no."""
    state = state or get_torch_state()
    state.duration_seconds = max(0, state.duration_seconds + delta_seconds)
    db.session.commit()
    return state


def stop(state: TorchState | None = None) -> TorchState:
    state = state or get_torch_state()
    state.is_running = False
    state.elapsed_seconds = 0
    state.segment_started_at = None
    db.session.commit()
    return state
