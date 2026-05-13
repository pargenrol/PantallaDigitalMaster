# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About the Project

**DM Command Center (Pantalla de Máster Digital)** is a Flask web app for tabletop RPG Game Masters. It provides a dual-screen setup: a private master control panel and a player-facing display projected on a second monitor/TV.

Key capabilities:
- Initiative tracker with turn/HP management
- Grimoire: loads monsters, spells, and rules from local `.md` files
- Interactive whiteboard (Fabric.js-based)
- Player screen commands (show image, video, YouTube, cards, blackout, grid)

## Setup and Running

```bash
# Install (creates venv and installs dependencies)
./install.sh

# Run the app (starts Flask + opens browser at /master)
./run.sh

# Or run directly after activating venv
source venv/bin/activate
python app.py
```

App runs at `http://127.0.0.1:5000`. Main views:
- `/master` — GM control panel
- `/player` — Player display (for second screen)
- `/player/screen` — Fullscreen player view

## Architecture

### Request Flow

The master view communicates with the player view via a **file-based command system** (`instance/screen_command.json`). The master POSTs to `/api/screen/*` endpoints which write JSON commands to that file. The player polls `/api/screen/command` (GET) and reacts to the latest command type.

### Blueprints (`routes/`)

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `views.py` | — | HTML views: master, player, content detail |
| `api_characters.py` | `/api/characters` | CRUD for initiative tracker characters |
| `api_game.py` | `/api/game` | Turn management (next/prev/reset) |
| `api_media.py` | `/api/media` | File uploads |
| `api_screen.py` | `/api/screen` | Commands sent to the player screen |
| `api_whiteboard.py` | `/api/whiteboard` | Whiteboard state persistence |

### Database (`database/`)

SQLite via Flask-SQLAlchemy. Database stored at `instance/app.db`.

- **`Character`**: Combat participants (players and monsters). Fields: `name`, `initiative`, `health_points`, `max_health_points`, `type_character` (`"player"` or `"monster"`), `is_active`, `monster_slug`.
- **`GameState`**: Singleton row tracking `current_turn` (index into initiative order) and `round_number`.

`database/seed.py` runs on startup via `seed_db(app)` — creates tables and inserts a default GameState and one example character if empty.

Services in `database/services/` handle all DB queries; routes never import models directly.

### Grimoire Content (`resources/`)

Markdown files in `resources/monsters/`, `resources/spells/`, and `resources/rules/` are loaded at request time via `utils/markdown_content.py`. Files use YAML frontmatter for metadata (loaded with `python-frontmatter`). The `slug` is the filename without `.md`.

See `contributing.md` for the exact frontmatter schema required for monster files. Key fields: `title`, `nombre`, `tipo`, `tamaño`, `ac`, `hp`, `hp_roll`, `desafio`, `px`, `per`, `velocidad`, `portrait_path`.

### Configuration (`config.py`)

- `Config` — base config, `DEBUG=False`
- `DevelopmentConfig` — `DEBUG=True`
- `TestingConfig` — in-memory SQLite (`sqlite:///:memory:`)

The app always loads `config.Config`. To use a different config, change `app.config.from_object(...)` in `app.py`.

Key config paths: `UPLOAD_DIR`, `MONSTERS_DIR`, `SPELLS_DIR`, `RULES_DIR`, `WHITEBOARD_STATE_FILE`, `SCREEN_COMMAND_FILE` (all under `BASE_DIR` or `instance/`).

### State Files (`utils/state_files.py`)

`screen_command.json` is an **append-only log** — each command is a new JSON line. `load_screen_command` reads only the last line. `whiteboard_state.json` is overwritten on each save.
