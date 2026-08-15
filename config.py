import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

class Config:
    SECRET_KEY = 'rpg-master-secret-2024'
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(INSTANCE_DIR, "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = False
    TESTING = False

    UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
    MONSTERS_DIR = os.path.join(BASE_DIR, "resources", "monsters")
    SPELLS_DIR = os.path.join(BASE_DIR, "resources", "spells")
    RULES_DIR = os.path.join(BASE_DIR, "resources", "rules")

    WHITEBOARD_STATE_FILE = os.path.join(INSTANCE_DIR, "whiteboard_state.json")
    SCREEN_COMMAND_FILE = os.path.join(INSTANCE_DIR, "screen_command.json")

    # RAG / Asistente IA
    CHROMA_DIR          = os.path.join(INSTANCE_DIR, "chroma_db")
    BIBLIOTECA_PATH     = "/home/israel/rol-biblioteca/biblioteca"
    BIBLIOTECA_URL      = os.environ.get("BIBLIOTECA_URL", "http://localhost:8765")
    OLLAMA_URL          = "http://localhost:11434"
    OLLAMA_CHAT_MODEL   = "qwen2.5:7b-instruct-q4_K_M"
    OLLAMA_EMBED_MODEL  = "nomic-embed-text"
    RAG_K               = 2
    RAG_CHUNK_SIZE      = 600
    RAG_CHUNK_OVERLAP   = 60

    # Carpetas de la biblioteca a indexar (relativas a BIBLIOTECA_PATH)
    RAG_INDEX_FOLDERS = [
        "Dungeons & Dragons/D&D 5ª edición/Core y Suplementos",
        "Dungeons & Dragons/D&D 5ª edición/Forgotten Realms",
        "Dungeons & Dragons/D&D 5ª edición/Ravenloft",
        "Dungeons & Dragons/AD&D 2ª edición/Core y Suplementos",
        "Dungeons & Dragons/AD&D 2ª edición/Greyhawk",
        "Dungeons & Dragons/AD&D 2ª edición/Dark Sun",
        "Dungeons & Dragons/AD&D 2ª edición/Dark Sun/Sol Oscuro - Extraído",
        "Dungeons & Dragons/AD&D 2ª edición/Forgotten Realms",
        "Dungeons & Dragons/AD&D 2ª edición/Ravenloft",
        "Otros/Mothership",
    ]


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False