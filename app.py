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

    app.register_blueprint(views_bp)
    app.register_blueprint(api_characters_bp)
    app.register_blueprint(api_game_bp)
    app.register_blueprint(api_media_bp)
    app.register_blueprint(api_screen_bp)
    app.register_blueprint(api_whiteboard_bp)

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

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print("🚀 Servidor RPG Master iniciado en http://127.0.0.1:5000")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
