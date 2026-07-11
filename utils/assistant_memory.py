"""
Módulo de memoria persistente por asistente.

Almacena entradas de memoria en ficheros JSON por sistema de juego:
  instance/memory/{system_id}.json

Funciones exportadas:
  load_memory(system_id) -> list[dict]
  add_entry(system_id, text, entry_type="nota") -> dict
  delete_entry(system_id, entry_id) -> bool
  clear_memory(system_id) -> None
  format_memory_for_prompt(system_id, assistant_name) -> str
"""

import json
import uuid
from datetime import date
from pathlib import Path

# Directorio base para los ficheros de memoria
_MEMORY_DIR = Path(__file__).parent.parent / "instance" / "memory"


def _memory_path(system_id: str) -> Path:
    """Devuelve la ruta al fichero JSON de memoria para el sistema dado."""
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return _MEMORY_DIR / f"{system_id}.json"


def load_memory(system_id: str) -> list[dict]:
    """Carga y devuelve la lista de entradas de memoria para el sistema indicado."""
    path = _memory_path(system_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("entries", [])
    except Exception:
        return []


def _save_memory(system_id: str, entries: list[dict]) -> None:
    """Serializa y guarda la lista de entradas en disco."""
    path = _memory_path(system_id)
    path.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")


def add_entry(system_id: str, text: str, entry_type: str = "nota") -> dict:
    """
    Añade una nueva entrada a la memoria del sistema.
    Genera un UUID y la fecha actual automáticamente.
    Devuelve el dict de la entrada creada.
    """
    entries = load_memory(system_id)
    entry = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "date": date.today().isoformat(),
        "type": entry_type,
    }
    entries.append(entry)
    _save_memory(system_id, entries)
    return entry


def delete_entry(system_id: str, entry_id: str) -> bool:
    """
    Elimina la entrada con el id dado de la memoria del sistema.
    Devuelve True si se encontró y eliminó, False si no existía.
    """
    entries = load_memory(system_id)
    new_entries = [e for e in entries if e.get("id") != entry_id]
    if len(new_entries) == len(entries):
        return False
    _save_memory(system_id, new_entries)
    return True


def clear_memory(system_id: str) -> None:
    """Borra toda la memoria del sistema indicado."""
    _save_memory(system_id, [])


def format_memory_for_prompt(system_id: str, assistant_name: str) -> str:
    """
    Devuelve un bloque de texto con las entradas de memoria listo para inyectar
    en el prompt del LLM. Devuelve cadena vacía si no hay entradas.
    """
    entries = load_memory(system_id)
    if not entries:
        return ""
    lines = [f"[MEMORIA PERSONAL DE {assistant_name.upper()}]"]
    for entry in entries:
        lines.append(f"- [{entry.get('date', '')}] {entry.get('text', '')}")
    return "\n".join(lines)
