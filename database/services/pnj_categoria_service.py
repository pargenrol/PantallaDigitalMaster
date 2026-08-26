import json
import random

from extensions import db
from database.models.pnj_categoria import PnjCategoria


def list_categorias(sistema: str = "adnd2e") -> list[PnjCategoria]:
    return PnjCategoria.query.filter_by(sistema=sistema).order_by(PnjCategoria.nombre.asc()).all()


def get_categoria(categoria_id: int) -> PnjCategoria | None:
    return PnjCategoria.query.get(categoria_id)


def add_categoria(nombre: str, stats_config: dict, equipo_basico: str, sistema: str = "adnd2e") -> PnjCategoria:
    cat = PnjCategoria(
        nombre=nombre.strip(),
        sistema=sistema,
        stats_config=json.dumps(stats_config, ensure_ascii=False),
        equipo_basico=equipo_basico or "",
    )
    db.session.add(cat)
    db.session.commit()
    return cat


def update_categoria(categoria_id: int, nombre: str | None = None, stats_config: dict | None = None,
                      equipo_basico: str | None = None) -> PnjCategoria | None:
    cat = PnjCategoria.query.get(categoria_id)
    if not cat:
        return None
    if nombre is not None:
        cat.nombre = nombre.strip()
    if stats_config is not None:
        cat.stats_config = json.dumps(stats_config, ensure_ascii=False)
    if equipo_basico is not None:
        cat.equipo_basico = equipo_basico
    db.session.commit()
    return cat


def delete_categoria(categoria_id: int) -> bool:
    cat = PnjCategoria.query.get(categoria_id)
    if not cat:
        return False
    db.session.delete(cat)
    db.session.commit()
    return True


def categoria_al_azar(sistema: str = "adnd2e") -> PnjCategoria | None:
    cats = list_categorias(sistema)
    return random.choice(cats) if cats else None


def generar_pnj(categoria_id: int, dg: int) -> dict | None:
    cat = PnjCategoria.query.get(categoria_id)
    if not cat:
        return None
    return {
        "categoria": cat.nombre,
        "dg": dg,
        "stats": cat.calcular_stats(dg),
        "equipo": cat.equipo_por_dg(dg),
    }


def descripcion_plantilla(nombre: str, categoria: str, rasgos: list[dict]) -> str:
    """Compone una descripción simple (sin IA) a partir de las frases de los
    rasgos seleccionados."""
    if not rasgos:
        return f"{nombre} es {categoria.lower()}. No se ha marcado ningún rasgo distintivo."
    frases = [r["frase"] for r in rasgos]
    if len(frases) == 1:
        cuerpo = frases[0]
    else:
        cuerpo = ", ".join(frases[:-1]) + " y " + frases[-1]
    return f"{nombre} es {categoria.lower()}: {cuerpo}."
