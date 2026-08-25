from extensions import db


class GeneratorTable(db.Model):
    """
    Tabla de un generador aleatorio editable (rumores, ganchos, encuentros...).
    El campo `slug` enlaza con el fichero markdown de la regla correspondiente
    en resources/<sistema>/rules/ (mismo slug, category: Generador), que sigue
    siendo la entrada de navegación/búsqueda en el Grimorio.
    """
    __tablename__ = "generator_tables"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    sistema = db.Column(db.String(50), nullable=False, default="adnd2e")
    dado = db.Column(db.Integer, nullable=False, default=30)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    entries = db.relationship(
        "GeneratorEntry",
        backref="tabla",
        order_by="GeneratorEntry.orden",
        cascade="all, delete-orphan",
    )


class GeneratorEntry(db.Model):
    """
    Una entrada (fila) de una GeneratorTable. `orden` determina la posición en
    la lista y también qué resultado de dado le corresponde en la tirada
    automática. `usado` permite marcar una entrada como ya utilizada en mesa
    (selección manual o automática al tirar), sin borrarla.
    """
    __tablename__ = "generator_entries"

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("generator_tables.id"), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, nullable=False, default=0)
    usado = db.Column(db.Boolean, default=False, nullable=False)
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
