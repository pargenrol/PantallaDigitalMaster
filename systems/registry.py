import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SYSTEMS = {
    "dnd5e": {
        "id": "dnd5e",
        "name": "Dungeons & Dragons 5e",
        "short_name": "D&D 5e",
        "description": "El clásico juego de rol de fantasía épica.",
        "theme": "dnd5e",
        "icon": "🐉",
        "resources": {
            "monsters": os.path.join(BASE_DIR, "resources", "dnd5e", "monsters"),
            "spells":   os.path.join(BASE_DIR, "resources", "dnd5e", "spells"),
            "rules":    os.path.join(BASE_DIR, "resources", "dnd5e", "rules"),
        },
        "tab_labels": {
            "monsters": "Bestiario",
            "spells":   "Conjuros",
            "rules":    "Reglas",
        },
        "initiative_label": "Ini",
        "hp_label": "PV",
        "has_stress": False,
        "stress_label": "Estrés",
        "header_title": "DM Control Center",
        "character_types": ["player", "monster"],
    },
    "mothership": {
        "id": "mothership",
        "name": "Mothership RPG",
        "short_name": "Mothership",
        "description": "Supervivencia en el espacio exterior. Horror y ciencia ficción.",
        "theme": "mothership",
        "icon": "🛸",
        "resources": {
            "monsters": os.path.join(BASE_DIR, "resources", "mothership", "npcs"),
            "spells":   os.path.join(BASE_DIR, "resources", "mothership", "equipment"),
            "rules":    os.path.join(BASE_DIR, "resources", "mothership", "rules"),
        },
        "tab_labels": {
            "monsters": "NPCs",
            "spells":   "Equipo",
            "rules":    "Reglas",
        },
        "initiative_label": "VEL",
        "hp_label": "PV",
        "has_stress": True,
        "stress_label": "Estrés",
        "header_title": "MOTHERSHIP // WARDEN CONSOLE",
        "character_types": ["marine", "camionero", "cientifico", "androide", "criatura"],
    },
    "agnostico": {
        "id": "agnostico",
        "name": "Sistema Agnóstico",
        "short_name": "Agnóstico",
        "description": "Pantalla genérica para cualquier sistema de rol.",
        "theme": "agnostico",
        "icon": "🎲",
        "resources": {
            "monsters": os.path.join(BASE_DIR, "resources", "agnostico", "creatures"),
            "spells":   os.path.join(BASE_DIR, "resources", "agnostico", "skills"),
            "rules":    os.path.join(BASE_DIR, "resources", "agnostico", "rules"),
        },
        "tab_labels": {
            "monsters": "Criaturas",
            "spells":   "Habilidades",
            "rules":    "Reglas",
        },
        "initiative_label": "Ini",
        "hp_label": "PV",
        "has_stress": False,
        "stress_label": "Estrés",
        "header_title": "RPG Master Control",
        "character_types": ["jugador", "enemigo", "aliado"],
    },
}

DEFAULT_SYSTEM = "dnd5e"


def get_system(system_id: str) -> dict:
    return SYSTEMS.get(system_id, SYSTEMS[DEFAULT_SYSTEM])


def get_all_systems() -> list[dict]:
    return list(SYSTEMS.values())
