from extensions import db


class EquipoItem(db.Model):
    """
    Catálogo reutilizable de objetos de equipo (independiente de categoría de
    PNJ). Se puede asignar a varias categorías de PNJ con un nivel mínimo
    distinto en cada una (ver PnjCategoriaEquipo).

    `precio` se deja preparado para una futura lista de precios (no se usa
    todavía en el generador de PNJ, pero así no hace falta migrar el esquema
    cuando se active).
    """
    __tablename__ = "equipo_items"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    descripcion = db.Column(db.String(300), nullable=True)
    precio = db.Column(db.Float, nullable=True)
    sistema = db.Column(db.String(50), nullable=False, default="adnd2e")
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class PnjCategoriaEquipo(db.Model):
    """
    Asignación de un EquipoItem a una PnjCategoria, con el nivel (Dados de
    Golpe) mínimo a partir del cual ese objeto aparece en el equipo generado
    para un PNJ de esa categoría.
    """
    __tablename__ = "pnj_categoria_equipo"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("pnj_categorias.id"), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipo_items.id"), nullable=False)
    nivel_minimo = db.Column(db.Integer, nullable=False, default=1)

    equipo = db.relationship("EquipoItem")

    __table_args__ = (
        db.UniqueConstraint("categoria_id", "equipo_id", name="uq_categoria_equipo"),
    )
