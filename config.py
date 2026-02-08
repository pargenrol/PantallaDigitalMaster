import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

class Config:
    SECRET_KEY = 'rpg-master-secret'
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


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False