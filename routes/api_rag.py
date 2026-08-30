"""
Blueprint de administración del índice RAG.

Rutas:
  GET  /api/rag/status  — si hay una indexación en curso y el resultado de la última
  POST /api/rag/reindex — lanza utils/rag_indexer.py en segundo plano

Pensado para que rol-biblioteca (proyecto hermano) pueda pedir una
reindexación tras subir contenido nuevo sin acoplarse al código de este
proyecto — solo una llamada HTTP a este endpoint, ver utils/biblioteca.py
para el enlace en sentido contrario.
"""
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify

bp = Blueprint("api_rag", __name__, url_prefix="/api/rag")

BASE_DIR = Path(__file__).parent.parent
INDEXER  = BASE_DIR / "utils" / "rag_indexer.py"
LOG_FILE = BASE_DIR / "instance" / "rag_indexer.log"

_lock = threading.Lock()
_state = {"running": False, "started_at": None, "finished_at": None, "error": None, "returncode": None}


def _run_indexer():
    with _lock:
        _state.update(running=True, started_at=datetime.now().isoformat(),
                       finished_at=None, error=None, returncode=None)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w") as log:
            proc = subprocess.run(
                [sys.executable, str(INDEXER)],
                cwd=BASE_DIR, stdout=log, stderr=subprocess.STDOUT,
            )
        with _lock:
            _state.update(running=False, finished_at=datetime.now().isoformat(),
                           returncode=proc.returncode,
                           error=None if proc.returncode == 0 else f"El indexador terminó con código {proc.returncode} (ver {LOG_FILE.name})")
    except Exception as e:
        with _lock:
            _state.update(running=False, finished_at=datetime.now().isoformat(), error=str(e))


@bp.get("/status")
def rag_status():
    with _lock:
        return jsonify(dict(_state))


@bp.post("/reindex")
def rag_reindex():
    with _lock:
        if _state["running"]:
            return jsonify({"ok": False, "error": "Ya hay una indexación en curso"}), 409
    threading.Thread(target=_run_indexer, daemon=True).start()
    return jsonify({"ok": True, "message": "Indexación lanzada en segundo plano"}), 202
