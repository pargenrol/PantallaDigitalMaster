from extensions import db

class GameState(db.Model):
    """
    GameState database model for managing game state information.
    Attributes:
        id (int): Primary key identifier for the game state record.
        current_turn (int): The current turn number in the game, defaults to 0.
        round_number (int): The current round number in the game, defaults to 1.
        last_updated (datetime): Timestamp of when the record was last modified, automatically set to current time on creation and update.
    """
    __tablename__ = "game_states"

    id = db.Column(db.Integer, primary_key=True)
    current_turn = db.Column(db.Integer, default=0, nullable=False)
    round_number = db.Column(db.Integer, default=1, nullable=False)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)