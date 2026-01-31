from extensions import db

class Character(db.Model):
    """
    Character model representing a character entity in the database.
    This class defines the structure for storing character information including
    their identity, combat statistics, type classification, and metadata.
    Attributes:
        id (int): Primary key identifier for the character.
        name (str): The name of the character (required, max 100 characters).
        initiative (int): Initiative value for turn order (defaults to 0).
        health_points (int): Current health points of the character (defaults to 0).
        max_health_points (int): Maximum health points the character can have (defaults to 0).
        type_character (str): Type of character, typically "player" or "monster" (defaults to "player", max 50 characters).
        is_active (bool): Flag indicating if the character is active in combat (defaults to True).
        monster_slug (str): Slug identifier for monster types, if applicable (optional, max 100 characters).
        time_created (datetime): Timestamp when the character was created (automatically set to current time).
    """
    __tablename__ = "characters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    initiative = db.Column(db.Integer, default=0)
    health_points = db.Column(db.Integer, default=0, nullable=False)
    max_health_points = db.Column(db.Integer, default=0, nullable=False)
    type_character = db.Column(db.String(50), default="player", nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    monster_slug = db.Column(db.String(100), nullable=True)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)