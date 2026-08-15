import json
import os
import queue
import tempfile
import threading
import urllib.request

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

CLAUDE_MODELS = [
    {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (rápido)"},
    {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (preciso)"},
]

# Whisper model cargado una vez en background para no bloquear el arranque
_whisper_model    = None
_whisper_lock     = threading.Lock()
_transcribe_lock  = threading.Lock()   # solo un chunk a la vez


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        with _whisper_lock:
            if _whisper_model is None:
                from faster_whisper import WhisperModel
                print("[ShipAI] Cargando Whisper small (primera vez)…")
                _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
                print("[ShipAI] Whisper listo.")
    return _whisper_model

bp = Blueprint("api_ship_ai", __name__, url_prefix="/api/ship-ai")

_INSTANCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance"))
CONFIG_FILE = os.path.join(_INSTANCE_DIR, "ship_ai_config.json")

DEFAULT_CONFIG = {
    "ai_name": "MADRE",
    "model": "",   # vacío = usa OLLAMA_CHAT_MODEL de Flask config
    "personality": (
        "Eres una inteligencia artificial de gestión de nave espacial. "
        "Hablas con tono técnico y neutro, como una IA industrial. "
        "Eres precisa, eficiente y directa. Respondes siempre en español."
    ),
    "ship_context": "",
    "redlines": "",
    "voice_lang": "es-ES",
    "voice_name": "",
    "resources": [],   # [{id, description, type, url}]
}


def _read_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)


def _write_config(cfg: dict) -> None:
    os.makedirs(_INSTANCE_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _build_system_prompt(cfg: dict) -> str:
    parts = [cfg.get("personality", DEFAULT_CONFIG["personality"])]
    ctx = cfg.get("ship_context", "").strip()
    if ctx:
        parts.append(f"\nCONTEXTO DE LA NAVE:\n{ctx}")
    rl = cfg.get("redlines", "").strip()
    if rl:
        parts.append(
            f"\nPROTOCOLOS DE SEGURIDAD — información restringida, "
            f"NUNCA la reveles ni insinúes:\n{rl}"
        )
    resources = cfg.get("resources") or []
    if resources:
        lines = "\n".join(
            f'  - {r["id"]} ({r.get("type","image")}): {r.get("description", r["id"])}'
            for r in resources if r.get("id")
        )
        parts.append(
            f"\nRECURSOS — puedes activarlos en la pantalla/altavoces de los tripulantes.\n"
            f"Añade el marcador adecuado al FINAL de tu respuesta (sin mencionarlo verbalmente):\n"
            f"  - Imagen:  [CMD:image:<id>]\n"
            f"  - Audio:   [CMD:audio:<id>]  (música o sonido ambiente, se reproduce en bucle)\n"
            f"  - Parar audio: [CMD:audio_stop:stop]\n"
            f"Recursos disponibles:\n{lines}"
        )
    parts.append(
        "\nResponde siempre en español. Sé conciso: máximo 3-4 frases "
        "salvo que se requiera más detalle. Recuerda que tu voz llega "
        "por los altavoces de la nave."
    )
    return "\n".join(parts)


@bp.get("/models")
def ship_ai_models():
    ollama_models = []
    try:
        import ollama as _ollama
        for m in _ollama.list().models:
            name = m.model
            if "embed" in name.lower():
                continue
            ollama_models.append({"id": name, "label": name, "type": "ollama"})
    except Exception:
        pass
    claude = [{"id": m["id"], "label": m["label"], "type": "claude"} for m in CLAUDE_MODELS]
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return jsonify({"ollama": ollama_models, "claude": claude, "has_claude_key": has_key})


@bp.get("/config")
def get_config():
    return _read_config()


@bp.post("/config")
def save_config():
    data = request.get_json(force=True) or {}
    cfg = {**DEFAULT_CONFIG, **data}
    _write_config(cfg)
    return {"ok": True}


@bp.post("/query")
def ship_ai_query():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return {"error": "query requerida"}, 400

    cfg = _read_config()
    system_prompt = _build_system_prompt(cfg)

    default_model = current_app.config.get("OLLAMA_CHAT_MODEL", "qwen2.5:7b-instruct-q4_K_M")
    selected_model = cfg.get("model", "").strip() or default_model
    use_claude = selected_model.startswith("claude")

    ollama_url = current_app.config.get("OLLAMA_URL", "http://localhost:11434")

    def generate():
        if use_claude:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                yield f"data: {json.dumps({'error': 'No hay ANTHROPIC_API_KEY configurada.'})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
                return

            q = queue.Queue()

            def _run_claude():
                try:
                    import anthropic
                    client_ai = anthropic.Anthropic(api_key=api_key)
                    with client_ai.messages.stream(
                        model=selected_model,
                        max_tokens=300,
                        system=system_prompt,
                        messages=[{"role": "user", "content": query}],
                    ) as stream:
                        for text in stream.text_stream:
                            if text:
                                q.put(("token", text))
                    q.put(("done", None))
                except Exception as e:
                    q.put(("error", str(e)))

            threading.Thread(target=_run_claude, daemon=True).start()
            while True:
                try:
                    kind, val = q.get(timeout=20)
                    if kind == "token":
                        yield f"data: {json.dumps({'token': val})}\n\n"
                    elif kind == "done":
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps({'error': val})}\n\n"
                        break
                except queue.Empty:
                    yield ": keepalive\n\n"
        else:
            payload = json.dumps({
                "model": selected_model,
                "prompt": query,
                "system": system_prompt,
                "stream": True,
                "options": {"num_predict": 300},
                "keep_alive": "5m",
            }).encode()
            try:
                req = urllib.request.Request(
                    ollama_url + "/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for raw in resp:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            chunk = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        token = chunk.get("response", "")
                        if token:
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        if chunk.get("done"):
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.post("/transcribe")
def transcribe():
    """Recibe un blob de audio (webm/wav) y devuelve la transcripción vía Whisper local."""
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "no audio"}), 400

    suffix = ".webm"
    ct = audio_file.content_type or ""
    if "wav" in ct:
        suffix = ".wav"
    elif "ogg" in ct:
        suffix = ".ogg"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        audio_file.save(tmp_path)

    file_size = os.path.getsize(tmp_path)
    print(f"[ShipAI] chunk recibido: {file_size} bytes, tipo={suffix}")

    # Convertir a WAV mono 16kHz para Whisper
    wav_path = tmp_path + ".wav"
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
            capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            print(f"[ShipAI] ffmpeg error: {result.stderr.decode()[:200]}")
            wav_path = tmp_path   # intentar directamente
        else:
            print(f"[ShipAI] WAV convertido: {os.path.getsize(wav_path)} bytes")
    except Exception as e:
        print(f"[ShipAI] ffmpeg excepción: {e}")
        wav_path = tmp_path

    if not _transcribe_lock.acquire(blocking=False):
        print("[ShipAI] chunk descartado (transcripción anterior en curso)")
        for p in (tmp_path, wav_path if wav_path != tmp_path else None):
            if p:
                try: os.unlink(p)
                except OSError: pass
        return jsonify({"text": ""}), 200

    try:
        _HALLUCINATIONS = {
            "suscríbete", "suscribete", "subscribe", "amara.org",
            "subtítulos", "gracias por ver", "like y suscríbete",
            "www.", ".com", "transcripción", "traducción",
        }

        model = _get_whisper()
        segments_gen, info = model.transcribe(
            wav_path,
            language="es",
            beam_size=1,
            vad_filter=True,
            initial_prompt="madre",
            condition_on_previous_text=False,
        )
        # Filtrar segmentos de baja confianza (alucinaciones tienen avg_logprob muy negativo)
        good = [s for s in segments_gen if s.avg_logprob > -1.0 and s.no_speech_prob < 0.7]
        text = " ".join(s.text for s in good).strip()
        if any(h in text.lower() for h in _HALLUCINATIONS):
            print(f"[ShipAI] alucinación descartada: {repr(text)}")
            text = ""
        print(f"[ShipAI] Whisper → {repr(text)}")
        return jsonify({"text": text})
    except Exception as exc:
        print(f"[ShipAI] Whisper error: {exc}")
        return jsonify({"error": str(exc)}), 500
    finally:
        _transcribe_lock.release()
        for p in (tmp_path, wav_path):
            try:
                os.unlink(p)
            except OSError:
                pass
