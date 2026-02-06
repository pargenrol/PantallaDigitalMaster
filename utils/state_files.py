import json
from datetime import datetime


def save_screen_command(command_file: str, command_type: str, data=None) -> dict:
    command = {"type": command_type, "data": data, "timestamp": datetime.now().isoformat()}
    with open(command_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(command) + "\n")
    return command


def load_screen_command(command_file: str, default_type: str = "initiative") -> dict:
    try:
        with open(command_file, "r", encoding="utf-8") as f:
            return json.loads(f.readlines()[-1])
    except Exception:
        return {"type": default_type}


def save_whiteboard_state(state_file: str, state_data) -> dict:
    state = {"state": state_data, "timestamp": datetime.now().isoformat()}
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return state


def load_whiteboard_state(state_file: str) -> dict:
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"state": None}
