"""
Completado simple de texto (no streaming), sin RAG: dado un prompt de
sistema y de usuario, devuelve el texto generado o None si el modelo
falla o no está disponible (para que quien llame pueda caer a una
alternativa sin IA sin necesidad de capturar excepciones).

Soporta Ollama (local) y Claude (Anthropic API), con la misma detección
por prefijo del id de modelo ("claude...") que usa routes/api_assistant.py.
"""
import json
import os
import urllib.error
import urllib.request

from config import Config


def complete(system_prompt: str, user_prompt: str, model: str | None = None,
             num_predict: int = 300, temperature: float = 0.7) -> str | None:
    model = model or Config.OLLAMA_CHAT_MODEL
    if model.startswith("claude"):
        return _complete_claude(system_prompt, user_prompt, model, num_predict)
    return _complete_ollama(system_prompt, user_prompt, model, num_predict, temperature)


def _complete_claude(system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        texto = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        return texto.strip() or None
    except Exception as e:
        print(f"[llm] Error Claude: {e}")
        return None


def _complete_ollama(system_prompt: str, user_prompt: str, model: str,
                      num_predict: int, temperature: float) -> str | None:
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "keep_alive": "5m",
        "options": {"num_predict": num_predict, "temperature": temperature},
    }).encode()

    req = urllib.request.Request(
        f"{Config.OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        texto = data.get("message", {}).get("content", "")
        return texto.strip() or None
    except (urllib.error.URLError, Exception) as e:
        print(f"[llm] Error Ollama: {e}")
        return None
