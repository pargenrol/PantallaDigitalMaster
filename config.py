import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = 'rpg-master-secret'
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = False
    TESTING = False

    UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
    MONSTERS_DIR = os.path.join(BASE_DIR, "resources", "monsters")
    SPELLS_DIR = os.path.join(BASE_DIR, "resources", "spells")
    RULES_DIR = os.path.join(BASE_DIR, "resources", "rules")

    WHITEBOARD_STATE_FILE = os.path.join(BASE_DIR, "instance", "whiteboard_state.json")
    SCREEN_COMMAND_FILE = os.path.join(BASE_DIR, "instance", "screen_command.json")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False