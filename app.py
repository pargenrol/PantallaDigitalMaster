import os
from flask import Flask

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

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
from routes.api_generators import bp as api_generators_bp
from routes.api_pnj_categorias import bp as api_pnj_categorias_bp
from routes.api_equipo import bp as api_equipo_bp
from routes.api_pnj_roster import bp as api_pnj_roster_bp
from routes.api_rag import bp as api_rag_bp


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
    app.register_blueprint(api_generators_bp)
    app.register_blueprint(api_pnj_categorias_bp)
    app.register_blueprint(api_equipo_bp)
    app.register_blueprint(api_pnj_roster_bp)
    app.register_blueprint(api_rag_bp)

    db.init_app(app)
    return app


def main():
    """
    Run the Flask application.
    This function creates a Flask app instance, seeds the database with initial data, and starts the development server. 
    The host and port can be configured via environment variables (HOST and PORT), defaulting to 0.0.0.0:5001.
    Environment Variables:
        HOST (str): The host address to bind the server to. Defaults to "0.0.0.0".
        PORT (str): The port number to bind the server to. Defaults to "5001".
    Returns:
        None: Starts the Flask development server (blocking call).
    """
    app = create_app()
    seed_db(app)

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5001"))
    print(f"🚀 Servidor RPG Master iniciado en http://0.0.0.0:{port}")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
