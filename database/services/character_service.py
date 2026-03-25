from extensions import db
from database.models.character import Character


def get_active_characters():
    """
    Retrieve all active characters ordered by initiative and name.
    
    Returns:
        list[Character]: A sorted list of active Character objects.
    """
    return (
        Character.query
        .filter_by(is_active=True)
        .order_by(Character.initiative.desc(), Character.name.asc())
        .all()
    )


def add_character(data: dict) -> Character:
    """
    Create and persist a new character to the database.

    Args:
        data (dict): A dictionary containing character attributes. Supported keys:
            - name (str): Character name (required)
            - initiative (int, optional): Initiative value. Defaults to 0.
            - hp or health_points (int, optional): Current health points. Defaults to 0.
            - max_hp or max_health_points (int, optional): Maximum health points. Defaults to 0.
            - type or type_character (str, optional): Character type. Defaults to "player".
            - slug or monster_slug (str, optional): Monster identifier/slug. Defaults to None.

    Returns:
        Character: The newly created and persisted Character instance.
    """
    try:
        if not data or "name" not in data:
            raise KeyError("Required 'name' key missing from data dictionary")
        
        ch = Character(
            name=data["name"],
            initiative=int(data.get("initiative", 0)),
            health_points=int(data.get("hp", data.get("health_points", 0)) or 0),
            max_health_points=int(data.get("max_hp", data.get("max_health_points", 0)) or 0),
            type_character=data.get("type", data.get("type_character", "player")),
            monster_slug=data.get("slug", data.get("monster_slug")),
            is_active=True,
        )
        db.session.add(ch)
        db.session.commit()
        return ch

    except ValueError as e:
        db.session.rollback()
        raise ValueError(f"Invalid numeric value: {str(e)}")
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Database operation failed: {str(e)}")


def soft_delete_character(char_id: int) -> bool:
    """
    Soft delete a character by marking it as inactive.

    Args:
        char_id (int): The ID of the character to soft delete.

    Returns:
        bool: True if the character was successfully soft deleted, False if the character was not found.
    """
    ch = Character.query.get(char_id)
    if ch:
        ch.is_active = False
        db.session.commit()
        marker_inactive = True
    else:
        marker_inactive = False

    return marker_inactive


def update_hp(char_id: int, hp: int) -> bool:
    """
    Update the health points of a character.
    Args:
        char_id (int): The unique identifier of the character to update.
        hp (int): The new health points value to set for the character.
    Returns:
        bool: True if the character was found and health points were updated successfully,
              False if the character with the given char_id does not exist.
    """
    ch = Character.query.get(char_id)
    if ch:
        ch.health_points = int(hp)
        db.session.commit()
        updated_hp = True
    else:
        updated_hp = False
    
    return updated_hp