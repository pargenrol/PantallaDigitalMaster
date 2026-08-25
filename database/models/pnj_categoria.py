import json

from extensions import db


class PnjCategoria(db.Model):
    """
    Categoría de PNJ rápido (Tabernero, Guardia, Mercader...) usada por el
    generador de PNJ Rápido para calcular características y equipo básico en
    función de los Dados de Golpe (DG) que se le asignen al PNJ concreto.

    `stats_config` guarda un JSON por atributo:
        {"fue": {"base": 10, "bonus_dg": 1, "tope": 18}, "des": {...}, ...}
    El valor final de un atributo = min(base + bonus_dg * DG, tope).
    Cualquier atributo ausente del JSON simplemente no se calcula/muestra.

    `equipo_basico` es texto libre, un objeto por línea.
    """
    __tablename__ = "pnj_categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    sistema = db.Column(db.String(50), nullable=False, default="adnd2e")
    stats_config = db.Column(db.Text, nullable=False, default="{}")
    equipo_basico = db.Column(db.Text, nullable=True, default="")
    time_created = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def stats_dict(self) -> dict:
        try:
            return json.loads(self.stats_config or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def calcular_stats(self, dg: int) -> dict:
        resultado = {}
        for attr, cfg in self.stats_dict().items():
            base = cfg.get("base", 0)
            bonus_dg = cfg.get("bonus_dg", 0)
            tope = cfg.get("tope")
            valor = base + bonus_dg * dg
            if tope is not None:
                valor = min(valor, tope)
            resultado[attr] = valor
        return resultado

    def equipo_lista(self) -> list[str]:
        """Legado: equipo como texto libre (una línea por objeto). Se mantiene
        por compatibilidad, pero el generador ya usa equipo_por_dg()."""
        if not self.equipo_basico:
            return []
        return [linea.strip() for linea in self.equipo_basico.splitlines() if linea.strip()]

    def equipo_por_dg(self, dg: int) -> list[str]:
        """Objetos del catálogo (EquipoItem) asignados a esta categoría cuyo
        nivel_minimo sea <= dg, ordenados por nivel_minimo."""
        from database.models.equipo_item import PnjCategoriaEquipo
        asignaciones = (
            PnjCategoriaEquipo.query
            .filter(PnjCategoriaEquipo.categoria_id == self.id, PnjCategoriaEquipo.nivel_minimo <= dg)
            .join(PnjCategoriaEquipo.equipo)
            .order_by(PnjCategoriaEquipo.nivel_minimo.asc())
            .all()
        )
        return [a.equipo.nombre for a in asignaciones]
