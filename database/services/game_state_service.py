from extensions import db
from database.models.game_state import GameState
from database.models.character import Character


def get_game_state() -> GameState:
    """
    Retrieve the current game state from the database.
    
    If no game state exists, creates a new one with default values:
        - id: 1
        - current_turn: 0
        - round_number: 1
    
    Returns:
        GameState: The current game state object with id=1, or a newly created
                   default game state if none existed in the database.
    """
    state = GameState.query.get(1)
    if state is None:
        state = GameState(id=1, current_turn=0, round_number=1)
        db.session.add(state)
        db.session.commit()
    
    return state


def count_active_characters() -> int:
    """
    Counts the number of active characters in the database.

    Returns:
        int: The total number of characters where 'is_active' is True.
    """
    return Character.query.filter_by(is_active=True).count()


def next_turn() -> bool:
    """
    Advances the game state to the next turn.
    Retrieves the current game state and increments the turn counter. If the turn counter wraps around to zero, the round number is incremented. Commits the updated state to the database.
    Returns:
        bool: True if the turn was successfully advanced, False if there are no active characters.
    """
    state = get_game_state()
    total = count_active_characters()
    if total != 0:
        new_turn = (state.current_turn + 1) % total
        if new_turn == 0:
           state.round_number += 1
        state.current_turn = new_turn
        
        db.session.commit()
        change_made = True
    else:
        change_made = False
    
    return change_made


def prev_turn() -> bool:
    """
    Moves the game state to the previous character's turn.
    If the current turn is the first character and the round number is greater than one,
    the round number is decremented. The function updates the current turn accordingly,
    commits the change to the database, and returns True if successful. Returns False if
    there are no active characters.
    Returns:
        bool: True if the turn was successfully moved to the previous character, False otherwise.
    """
    state = get_game_state()
    total = count_active_characters()
    if total != 0:
        new_turn = (state.current_turn - 1 + total) % total

        if state.current_turn == 0 and new_turn == (total - 1) and state.round_number > 1:
            state.round_number -= 1

        state.current_turn = new_turn
        db.session.commit()
        change_made = True
    else:
        change_made = False
    
    return change_made


def reset_game() -> None:
    """
    Resets the game state to its initial values.

    This function deactivates all characters by setting their `is_active` attribute to False,
    resets the current turn to 0, and sets the round number to 1. All changes are committed
    to the database.
    """
    Character.query.update({Character.is_active: False})
    state = get_game_state()
    state.current_turn = 0
    state.round_number = 1
    db.session.commit()