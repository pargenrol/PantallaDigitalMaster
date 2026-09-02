import json
import os
import re

import frontmatter as fm
from sqlalchemy import inspect, text

from extensions import db
from database.models.character import Character
from database.models.game_state import GameState
from database.models.generator import GeneratorTable, GeneratorEntry
from database.models.pnj_categoria import PnjCategoria
from database.models.equipo_item import EquipoItem, PnjCategoriaEquipo
from database.models.pnj_roster import PnjRosterEntry
from database.models.campaign_folder import CampaignFolder
from database.models.screen_config import PantallaConfig


def _migrate_columns(app):
    """Add new columns to existing tables without dropping data (SQLite workaround)."""
    with app.app_context():
        inspector = inspect(db.engine)
        existing = [c["name"] for c in inspector.get_columns("characters")]
        with db.engine.connect() as conn:
            if "stress" not in existing:
                conn.execute(text("ALTER TABLE characters ADD COLUMN stress INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
            if "max_stress" not in existing:
                conn.execute(text("ALTER TABLE characters ADD COLUMN max_stress INTEGER NOT NULL DEFAULT 0"))
                conn.commit()

        if "equipo_items" in inspector.get_table_names():
            existing_equipo = [c["name"] for c in inspector.get_columns("equipo_items")]
            if "categoria" not in existing_equipo:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE equipo_items ADD COLUMN categoria VARCHAR(50)"))
                    conn.commit()


def _migrate_equipo_items_unique_por_sistema(app):
    """
    Migración de reparación: `equipo_items.nombre` tenía UNIQUE global, lo que
    impediría crear el mismo objeto (p.ej. "Espada corta") en dos ajustes
    distintos (AD&D2e, Dark Sun...). Se cambia a UNIQUE compuesto
    (nombre, sistema). SQLite no permite alterar un UNIQUE existente con
    ALTER TABLE, así que se reconstruye la tabla preservando los datos e IDs
    (las FK de PnjCategoriaEquipo siguen apuntando a los mismos ids).
    Idempotente: no hace nada si la tabla ya no tiene el UNIQUE viejo.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        if "equipo_items" not in inspector.get_table_names():
            return
        tiene_unique_viejo = any(
            uc.get("column_names") == ["nombre"]
            for uc in inspector.get_unique_constraints("equipo_items")
        )
        if not tiene_unique_viejo:
            return

        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE equipo_items RENAME TO equipo_items_old"))
            conn.commit()

        db.create_all()  # recrea equipo_items ya con el UNIQUE(nombre, sistema) del modelo actual

        with db.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO equipo_items (id, nombre, descripcion, precio, sistema, time_created)
                SELECT id, nombre, descripcion, precio, sistema, time_created FROM equipo_items_old
            """))
            conn.execute(text("DROP TABLE equipo_items_old"))
            conn.commit()
        print("[migrate] equipo_items: UNIQUE cambiado de (nombre) a (nombre, sistema)")


def _parse_markdown_table_second_column(markdown_body: str) -> list[str]:
    """
    Extrae la segunda columna de una tabla markdown "| rango | texto |"
    (se descarta la primera columna, que es el rango de dado). Ignora la
    fila de cabecera y la de separadores (---).
    """
    filas = []
    for linea in markdown_body.splitlines():
        linea = linea.strip()
        if not linea.startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if len(celdas) < 2:
            continue
        if re.match(r"^:?-+:?$", celdas[0]):  # fila separadora tipo |---|---|
            continue
        if celdas[0].lower() in ("d30", "d20", "d12", "d10", "d8", "d6", "d4", "rango", "resultado"):
            continue  # cabecera
        filas.append(celdas[1])
    return filas


def _seed_generators_from_markdown(app):
    """
    Migración única: importa las tablas de los ficheros
    resources/<sistema>/rules/generador_*.md de los 5 sistemas de la familia
    AD&D2e a la base de datos (GeneratorTable + GeneratorEntry), para que
    queden editables/seleccionables desde la app. No hace nada si la tabla ya
    tiene entradas (evita duplicar en reinicios). El campo "sistema" de cada
    GeneratorTable se toma de la carpeta en la que vive el fichero, no de un
    valor fijo, para que el mecanismo sirva para cualquiera de los 5 sistemas
    y no solo para el ajuste base.
    """
    with app.app_context():
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        for sistema in _SISTEMAS_ADND2E_TODOS:
            rules_dir = os.path.join(base_dir, "resources", sistema, "rules")
            if not os.path.isdir(rules_dir):
                continue

            for filename in os.listdir(rules_dir):
                if not filename.startswith("generador_") or not filename.endswith(".md"):
                    continue
                filepath = os.path.join(rules_dir, filename)
                try:
                    post = fm.load(filepath)
                except Exception as e:
                    print(f"[seed_generators] Error leyendo {sistema}/{filename}: {e}")
                    continue

                slug = post.metadata.get("slug") or filename.replace(".md", "")
                nombre = post.metadata.get("nombre") or slug
                dado = int(post.metadata.get("dado") or 30)

                tabla = GeneratorTable.query.filter_by(slug=slug).first()
                if tabla is None:
                    tabla = GeneratorTable(slug=slug, nombre=nombre, sistema=sistema, dado=dado)
                    db.session.add(tabla)
                    db.session.commit()

                if GeneratorEntry.query.filter_by(table_id=tabla.id).count() > 0:
                    continue  # ya migrada, no duplicar

                textos = _parse_markdown_table_second_column(post.content)
                for i, texto in enumerate(textos, start=1):
                    db.session.add(GeneratorEntry(table_id=tabla.id, texto=texto, orden=i, usado=False))
                db.session.commit()
                print(f"[seed_generators] {sistema}/{slug}: {len(textos)} entradas importadas")


def _seed_pnj_categorias(app):
    """
    Migración única: crea categorías de PNJ de ejemplo (Tabernero, Guardia,
    Mercader, Bandido) con estadísticas escaladas por Dados de Golpe y equipo
    básico, para que el generador de PNJ Rápido tenga algo con lo que
    funcionar desde el primer uso. No hace nada si ya hay categorías creadas
    (para no pisar ediciones del usuario en reinicios).
    """
    with app.app_context():
        if PnjCategoria.query.first() is not None:
            return

        categorias = [
            {
                "nombre": "Tabernero",
                "stats_config": {
                    "fue": {"base": 9, "bonus_dg": 0, "tope": 12},
                    "des": {"base": 9, "bonus_dg": 0, "tope": 12},
                    "con": {"base": 10, "bonus_dg": 0.5, "tope": 14},
                    "int": {"base": 10, "bonus_dg": 0, "tope": 13},
                    "sab": {"base": 11, "bonus_dg": 0, "tope": 14},
                    "car": {"base": 12, "bonus_dg": 0, "tope": 15},
                },
                # (nombre del objeto, nivel_minimo de DG al que aparece)
                "equipo": [
                    ("Cuchillo de cocina", 1),
                    ("Delantal", 1),
                    ("Llaves del local", 1),
                    ("Una moneda de propina guardada aparte", 1),
                    ("Porra bajo la barra", 2),
                ],
            },
            {
                "nombre": "Guardia",
                "stats_config": {
                    "fue": {"base": 12, "bonus_dg": 1, "tope": 17},
                    "des": {"base": 11, "bonus_dg": 0.5, "tope": 15},
                    "con": {"base": 12, "bonus_dg": 1, "tope": 16},
                    "int": {"base": 9, "bonus_dg": 0, "tope": 11},
                    "sab": {"base": 10, "bonus_dg": 0, "tope": 13},
                    "car": {"base": 9, "bonus_dg": 0, "tope": 11},
                },
                "equipo": [
                    ("Espada corta", 1),
                    ("Armadura de cuero", 1),
                    ("Escudo pequeño", 1),
                    ("Silbato de alarma", 1),
                    ("Cota de malla", 3),
                    ("Ballesta ligera", 4),
                ],
            },
            {
                "nombre": "Mercader",
                "stats_config": {
                    "fue": {"base": 9, "bonus_dg": 0, "tope": 11},
                    "des": {"base": 10, "bonus_dg": 0, "tope": 13},
                    "con": {"base": 10, "bonus_dg": 0, "tope": 13},
                    "int": {"base": 12, "bonus_dg": 0.5, "tope": 16},
                    "sab": {"base": 11, "bonus_dg": 0, "tope": 14},
                    "car": {"base": 13, "bonus_dg": 0.5, "tope": 17},
                },
                "equipo": [
                    ("Libro de cuentas", 1),
                    ("Bolsa de monedas", 1),
                    ("Daga oculta", 1),
                    ("Muestras de mercancía", 1),
                    ("Guardaespaldas de confianza (contacto, no PNJ)", 3),
                ],
            },
            {
                "nombre": "Bandido / Mercenario",
                "stats_config": {
                    "fue": {"base": 12, "bonus_dg": 1, "tope": 18},
                    "des": {"base": 13, "bonus_dg": 1, "tope": 18},
                    "con": {"base": 11, "bonus_dg": 1, "tope": 16},
                    "int": {"base": 9, "bonus_dg": 0, "tope": 11},
                    "sab": {"base": 9, "bonus_dg": 0, "tope": 12},
                    "car": {"base": 9, "bonus_dg": 0, "tope": 12},
                },
                "equipo": [
                    ("Espada corta o hacha de mano", 1),
                    ("Cuero endurecido", 1),
                    ("Cuerda (15m)", 1),
                    ("Un botín reciente sin identificar", 1),
                    ("Ballesta ligera", 2),
                    ("Cota de malla", 4),
                ],
            },
        ]

        for c in categorias:
            cat = PnjCategoria(
                nombre=c["nombre"],
                sistema="adnd2e",
                stats_config=json.dumps(c["stats_config"], ensure_ascii=False),
                equipo_basico="",  # legado, ya no se usa: el equipo va en el catálogo estructurado
            )
            db.session.add(cat)
            db.session.commit()  # necesitamos cat.id para las asignaciones de equipo

            for nombre_objeto, nivel_min in c["equipo"]:
                item = EquipoItem.query.filter_by(nombre=nombre_objeto, sistema="adnd2e").first()
                if item is None:
                    item = EquipoItem(nombre=nombre_objeto, sistema="adnd2e")
                    db.session.add(item)
                    db.session.commit()
                db.session.add(PnjCategoriaEquipo(categoria_id=cat.id, equipo_id=item.id, nivel_minimo=nivel_min))
            db.session.commit()

        print(f"[seed_pnj_categorias] {len(categorias)} categorías de PNJ creadas (6 características + equipo por nivel)")


_PNJ_CATEGORIAS_REFERENCIA_6_ATRIBUTOS = {
    "Tabernero": {
        "fue": {"base": 9, "bonus_dg": 0, "tope": 12},
        "des": {"base": 9, "bonus_dg": 0, "tope": 12},
        "con": {"base": 10, "bonus_dg": 0.5, "tope": 14},
        "int": {"base": 10, "bonus_dg": 0, "tope": 13},
        "sab": {"base": 11, "bonus_dg": 0, "tope": 14},
        "car": {"base": 12, "bonus_dg": 0, "tope": 15},
    },
    "Guardia": {
        "fue": {"base": 12, "bonus_dg": 1, "tope": 17},
        "des": {"base": 11, "bonus_dg": 0.5, "tope": 15},
        "con": {"base": 12, "bonus_dg": 1, "tope": 16},
        "int": {"base": 9, "bonus_dg": 0, "tope": 11},
        "sab": {"base": 10, "bonus_dg": 0, "tope": 13},
        "car": {"base": 9, "bonus_dg": 0, "tope": 11},
    },
    "Mercader": {
        "fue": {"base": 9, "bonus_dg": 0, "tope": 11},
        "des": {"base": 10, "bonus_dg": 0, "tope": 13},
        "con": {"base": 10, "bonus_dg": 0, "tope": 13},
        "int": {"base": 12, "bonus_dg": 0.5, "tope": 16},
        "sab": {"base": 11, "bonus_dg": 0, "tope": 14},
        "car": {"base": 13, "bonus_dg": 0.5, "tope": 17},
    },
    "Bandido / Mercenario": {
        "fue": {"base": 12, "bonus_dg": 1, "tope": 18},
        "des": {"base": 13, "bonus_dg": 1, "tope": 18},
        "con": {"base": 11, "bonus_dg": 1, "tope": 16},
        "int": {"base": 9, "bonus_dg": 0, "tope": 11},
        "sab": {"base": 9, "bonus_dg": 0, "tope": 12},
        "car": {"base": 9, "bonus_dg": 0, "tope": 12},
    },
}


def _fix_pnj_categorias_stats_faltantes(app):
    """
    Migración de reparación: categorías de PNJ creadas antes de ampliar a 6
    características (FUE/DES/CON/INT/SAB/CAR) se quedaron con solo 3 en la
    base de datos, porque el seed original solo se ejecutaba si no había
    ninguna categoría todavía. Aquí se completan los atributos que falten
    en las 4 categorías de ejemplo conocidas, sin tocar los que el usuario
    ya haya podido personalizar. Idempotente: si ya están las 6, no hace nada.
    """
    with app.app_context():
        cambios = 0
        for cat in PnjCategoria.query.all():
            referencia = _PNJ_CATEGORIAS_REFERENCIA_6_ATRIBUTOS.get(cat.nombre)
            if not referencia:
                continue
            actuales = cat.stats_dict()
            faltantes = {k: v for k, v in referencia.items() if k not in actuales}
            if not faltantes:
                continue
            actuales.update(faltantes)
            cat.stats_config = json.dumps(actuales, ensure_ascii=False)
            cambios += 1
        if cambios:
            db.session.commit()
            print(f"[fix_pnj_categorias] {cambios} categoría(s) completadas a 6 características")


_SISTEMAS_HERMANOS_ADND2E = ["darksun", "ravenloft_adnd", "greyhawk", "forgotten_realms"]
_SISTEMAS_ADND2E_TODOS = ["adnd2e"] + _SISTEMAS_HERMANOS_ADND2E
_CLIMA_ZONAS_BASE = ["desierto", "costa", "bosque", "cordillera", "llanuras"]


def _seed_generadores_familia_adnd2e(app):
    """
    Migración única: crea el mecanismo de "PNJ Rápido" y "Clima" (vacío, sin
    contenido) para los ajustes que comparten reglas de AD&D2e con el ajuste
    base (Dark Sun, Ravenloft AD&D, Greyhawk, Reinos Olvidados). Las tablas
    narrativas de Corona de Sal (Rumores, Encuentros, Ganchos, Detalle de
    Mazmorra) son propias de la campaña del ajuste base y no se replican.
    Cada ajuste tiene su propia GeneratorTable independiente (slug con
    sufijo de sistema) para no compartir ni mezclar contenido entre
    ambientaciones. Idempotente: no crea nada que ya exista.
    """
    with app.app_context():
        creadas = 0
        for sistema in _SISTEMAS_HERMANOS_ADND2E:
            slug_pnj = f"generador_pnj_rapido_{sistema}"
            if GeneratorTable.query.filter_by(slug=slug_pnj).first() is None:
                db.session.add(GeneratorTable(slug=slug_pnj, nombre="PNJ Rápido — Rasgo y Gancho", sistema=sistema, dado=30))
                creadas += 1
            for zona in _CLIMA_ZONAS_BASE:
                slug_zona = f"generador_clima_{sistema}_{zona}"
                if GeneratorTable.query.filter_by(slug=slug_zona).first() is None:
                    db.session.add(GeneratorTable(slug=slug_zona, nombre=f"Clima — {zona.capitalize()}", sistema=sistema, dado=30))
                    creadas += 1
        if creadas:
            db.session.commit()
            print(f"[seed_generadores_familia] {creadas} tabla(s) vacía(s) creadas para {', '.join(_SISTEMAS_HERMANOS_ADND2E)}")


def _seed_generadores_tesoro_trampas(app):
    """
    Migración única: crea (vacías) las GeneratorTable de Tesoro y Trampas
    para los 5 sistemas de la familia AD&D2e. A diferencia de PNJ Rápido y
    Clima, estos generadores son nuevos para todos los sistemas a la vez
    (adnd2e no tenía contenido previo de tesoro/trampas), así que usan un
    slug consistente desde el principio: generador_<tipo>_<sistema>.
    Idempotente.
    """
    with app.app_context():
        creadas = 0
        for sistema in _SISTEMAS_ADND2E_TODOS:
            for tipo, nombre, dado in (("tesoro", "Tesoro", 100), ("trampas", "Trampas", 30)):
                slug = f"generador_{tipo}_{sistema}"
                if GeneratorTable.query.filter_by(slug=slug).first() is None:
                    db.session.add(GeneratorTable(slug=slug, nombre=nombre, sistema=sistema, dado=dado))
                    creadas += 1
        if creadas:
            db.session.commit()
            print(f"[seed_tesoro_trampas] {creadas} tabla(s) vacía(s) creadas para {', '.join(_SISTEMAS_ADND2E_TODOS)}")


def seed_db(app):
    """
    Initialize the database with default seed data.
    Creates all database tables and populates them with initial data if they don't exist.
    Args:
        app: The Flask application instance used to establish the application context required for database operations.
    Returns:
        None
    Side Effects:
        - Creates all database tables defined in the SQLAlchemy models
        - Adds a GameState record with initial turn 0 and round 1 if none exists
        - Adds a default Character record (Goruk el Feroz) if none exists
        - Importa las tablas de generadores originales desde markdown a la base de datos
        - Commits all changes to the database
    """
    with app.app_context():
        db.create_all()
        _migrate_columns(app)
        _migrate_equipo_items_unique_por_sistema(app)

        if GameState.query.first() is None:
            db.session.add(GameState(current_turn=0, round_number=1))

        if Character.query.first() is None:
            db.session.add(
                Character(
                    name="Goruk el Feroz",
                    initiative=12,
                    health_points=35,
                    max_health_points=35,
                    type_character="player",
                    is_active=True,
                    monster_slug=None,
                )
            )

        db.session.commit()

    _seed_generators_from_markdown(app)
    _seed_pnj_categorias(app)
    _fix_pnj_categorias_stats_faltantes(app)
    _seed_generadores_familia_adnd2e(app)
    _seed_generadores_tesoro_trampas(app)
