import os
from flask import Flask

from extensions import db
from database.seed import seed_db
from routes.views import bp as views_bp
from routes.api_characters import bp as api_characters_bp
from routes.api_game import bp as api_game_bp
from routes.api_media import bp as api_media_bp
from routes.api_screen import bp as api_screen_bp
from routes.api_whiteboard import bp as api_whiteboard_bp
from routes.api_assistant import bp as api_assistant_bp
from routes.api_encounter import bp as api_encounter_bp
from routes.api_players import bp as api_players_bp
from routes.api_campaigns import bp as api_campaigns_bp
from routes.api_ship_ai import bp as api_ship_ai_bp


def create_app():
    """
    Initialize and configure the Flask application. Creates a Flask app instance with the following setup:
        - Loads configuration from config.Config
        - Registers multiple API blueprints for views, characters, game, media, screen, and whiteboard
        - Initializes the database with the app instance
    Returns:
        Flask: Configured Flask application instance ready to run.
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")
    app.jinja_env.auto_reload = True

    app.register_blueprint(views_bp)
    app.register_blueprint(api_characters_bp)
    app.register_blueprint(api_game_bp)
    app.register_blueprint(api_media_bp)
    app.register_blueprint(api_screen_bp)
    app.register_blueprint(api_whiteboard_bp)
    app.register_blueprint(api_assistant_bp)
    app.register_blueprint(api_encounter_bp)
    app.register_blueprint(api_players_bp)
    app.register_blueprint(api_campaigns_bp)
    app.register_blueprint(api_ship_ai_bp)

    db.init_app(app)
    return app


def main():
    """
    Run the Flask application.
    This function creates a Flask app instance, seeds the database with initial data, and starts the development server. 
    The host and port can be configured via environment variables (HOST and PORT), defaulting to 127.0.0.1:5000.
    Environment Variables:
        HOST (str): The host address to bind the server to. Defaults to "127.0.0.1".
        PORT (str): The port number to bind the server to. Defaults to "5000".
    Returns:
        None: Starts the Flask development server (blocking call).
    """
    app = create_app()
    seed_db(app)

    # Precalentar Ollama en background para evitar cold start en la primera consulta
    def _warmup_ollama():
        import urllib.request, json as _json
        try:
            payload = _json.dumps({
                "model": app.config.get("OLLAMA_CHAT_MODEL", "qwen2.5:7b-instruct-q4_K_M"),
                "prompt": "",
                "keep_alive": -1,
            }).encode()
            req = urllib.request.Request(
                app.config.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate",
                data=payload, headers={"Content-Type": "application/json"}, method="POST",
            )
            urllib.request.urlopen(req, timeout=60).read()
            print("[Ollama] Modelo precalentado y en memoria.")
        except Exception as e:
            print(f"[Ollama] Aviso: no se pudo precalentar el modelo: {e}")

    import threading
    threading.Thread(target=_warmup_ollama, daemon=True).start()

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    print("🚀 Servidor RPG Master iniciado en http://127.0.0.1:5000")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
