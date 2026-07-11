from sqlalchemy import inspect, text

from extensions import db
from database.models.character import Character
from database.models.game_state import GameState


def _migrate_columns(app):
    """Add new columns to existing tables without dropping data (SQLite workaround)."""
    with app.app_context():
        inspector = inspect(db.engine)
        existing = [c["name"] for c in inspector.get_columns("characters")]
        with db.engine.connect() as conn:
            if "stress" not in existing:
                conn.execute(text("ALTER TABLE characters ADD COLUMN stress INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
            if "max_stress" not in existing:
                conn.execute(text("ALTER TABLE characters ADD COLUMN max_stress INTEGER NOT NULL DEFAULT 0"))
                conn.commit()


def seed_db(app):
    """
    Initialize the database with default seed data.
    Creates all database tables and populates them with initial data if they don't exist.
    Args:
        app: The Flask application instance used to establish the application context required for database operations.
    Returns:
        None
    Side Effects:
        - Creates all database tables defined in the SQLAlchemy models
        - Adds a GameState record with initial turn 0 and round 1 if none exists
        - Adds a default Character record (Goruk el Feroz) if none exists
        - Commits all changes to the database
    """
    with app.app_context():
        db.create_all()
        _migrate_columns(app)

        if GameState.query.first() is None:
            db.session.add(GameState(current_turn=0, round_number=1))

        if Character.query.first() is None:
            db.session.add(
                Character(
                    name="Goruk el Feroz",
                    initiative=12,
                    health_points=35,
                    max_health_points=35,
                    type_character="player",
                    is_active=True,
                    monster_slug=None,
                )
            )

        db.session.commit()