"""Resuelve la URL pública de rol-biblioteca, el proyecto hermano de PDFs.

Deriva el host del propio request entrante para que el enlace funcione
tanto en local como accediendo por red local o Tailscale, en vez de
quedar fijo a "localhost".
"""
from flask import request, current_app


def get_biblioteca_url() -> str:
    cfg_url = current_app.config.get("BIBLIOTECA_URL", "http://localhost:8765")
    req_host = request.host.split(":")[0]
    url = f"http://{req_host}:8765"
    # Solo usar la config si el admin definió una URL explícita que no sea localhost
    if "localhost" not in cfg_url and "127.0.0.1" not in cfg_url:
        url = cfg_url
    return url
