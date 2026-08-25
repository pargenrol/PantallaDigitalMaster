"""
Generador programático de nombres para PNJs de Aethelgard/Corona de Sal.
Combina sílabas inventadas (no tomadas de ningún libro ni lista publicada)
pensadas para sonar coherentes con los nombres ya existentes en la campaña
(Krov, Silas, Verna, Fergus, Liselotte, Drathamar, Volder...): un registro
arcaico, algo duro, sin idioma real concreto detrás.

Los epítetos opcionales ("el Rompeolas", "la Penitente"...) siguen el mismo
estilo que ya usan los PJs de la campaña.
"""
import random

_PREFIJOS_M = [
    "Bor", "Gar", "Hal", "Kel", "Mor", "Old", "Ren", "Tor", "Ulf", "Vor",
    "Dren", "Fal", "Grim", "Hask", "Kor", "Ost", "Rald", "Sten", "Ther", "Wulf",
]
_SUFIJOS_M = [
    "gan", "rik", "dor", "mund", "vek", "than", "gard", "rus", "eld", "wyn",
    "mar", "vald", "ric", "gorn", "helm", "stan", "vir", "dric", "mok", "sen",
]

_PREFIJOS_F = [
    "Ana", "Bri", "Els", "Fen", "Hil", "Isa", "Lys", "Mira", "Sera", "Vel",
    "Adra", "Corin", "Freya", "Halda", "Ines", "Kira", "Nara", "Sela", "Tessa", "Verna",
]
_SUFIJOS_F = [
    "wen", "dra", "lys", "eth", "ara", "ith", "sia", "ora", "elle", "wyn",
    "line", "hild", "mira", "sira", "nel", "vel", "resa", "lena", "wynn", "iel",
]

_EPITETOS = [
    "el Callado", "la Penitente", "el Rompeolas", "la Marcada", "el Deudor",
    "la de las Manos Frías", "el Superviviente", "la del Pozo Seco", "el Recaudador",
    "la Tuerta", "el de la Cicatriz", "la Silenciosa", "el Errante", "la Cristalina",
    "el Manchado", "la del Barril", "el Cauto", "la Desterrada", "el Sordo",
    "la de Saloburgo", "el del Sudario", "la Descreída", "el Sin Nombre",
]


def generar_nombre(genero: str = "aleatorio", con_epiteto: float = 0.35) -> str:
    """
    Genera un nombre combinando prefijo+sufijo del género indicado
    ("m"/"masculino", "f"/"femenino", o "aleatorio"), con probabilidad
    `con_epiteto` (0-1) de añadir un epíteto al estilo de los PJs de la
    campaña (ej. "Borgan el Callado").
    """
    genero = (genero or "aleatorio").strip().lower()
    if genero in ("m", "masculino"):
        elegido = "m"
    elif genero in ("f", "femenino"):
        elegido = "f"
    else:
        elegido = random.choice(["m", "f"])

    if elegido == "m":
        nombre = random.choice(_PREFIJOS_M) + random.choice(_SUFIJOS_M).lower()
    else:
        nombre = random.choice(_PREFIJOS_F) + random.choice(_SUFIJOS_F).lower()

    if random.random() < con_epiteto:
        nombre = f"{nombre} {random.choice(_EPITETOS)}"

    return nombre
