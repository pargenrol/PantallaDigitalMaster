#!/usr/bin/env python3
"""
Genera fichas de monstruos AD&D 2ª edición en markdown a partir del Manual Monstruoso
(PDF escaneado sin capa de texto -> requiere OCR).

Por cada página con bloque de estadísticas detectado:
  1. OCR con tesseract (cacheado en instance/ocr_cache/ para no repetir)
  2. Envía el texto a qwen2.5 para generar la ficha estructurada (formato AD&D2e:
     ca/dg/thac0/ataques/daño/movimiento/px/alineamiento/tamaño + prosa)
  3. Guarda el resultado en resources/{system}/monsters/{slug}.md

Solo procesa monstruos que no tengan ya su .md (incremental).

Uso:
    venv/bin/python3 utils/generate_monster_md_adnd2e.py --dry-run
    venv/bin/python3 utils/generate_monster_md_adnd2e.py
    venv/bin/python3 utils/generate_monster_md_adnd2e.py --out resources/greyhawk/monsters
"""

import re
import argparse
import unicodedata
import requests
import time
import hashlib
from pathlib import Path

from pdf2image import convert_from_path
import pytesseract

DEFAULT_PDF = (
    "/home/israel/rol-biblioteca/biblioteca/"
    "Dungeons & Dragons/AD&D 2ª edición/Core y Suplementos/"
    "AD&D 2.2 - Manual Monstruoso Volumen I [Martinez Roca].pdf"
)
DEFAULT_RESOURCES = "/home/israel/Pantallasistemas/resources/adnd2e/monsters"
OCR_CACHE_DIR = "/home/israel/Pantallasistemas/instance/ocr_cache"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct-q4_K_M"

MIN_TEXT_LENGTH = 200

# Etiquetas del bloque de estadísticas (tolerante a errores de OCR), por idioma de origen.
STAT_LABELS_ES = re.compile(
    r"(CLIMA\s*/\s*TERREN|FRECUENCIA|ORGANIZACI[OÓ]N|CICLO ACTIVO|DIETA|"
    r"INTELIGENCIA|TESORO|ALINEAMIENTO|CLASE.{0,4}ARMADURA|MOVIMIENTO|"
    r"DADOS.{0,4}DE.{0,4}GOLPE|DADOS DEGOLPE|TACO\b|THAC0|"
    r"NO\.?\s*DE ATAQUES|DA[ÑN]O\s*/\s*ATAQUE|AT\.?\s*ESPECIALES|"
    r"DE[FR]\.?\s*ESPECIALES|RESIST\.?\s*M[AÁ]GICA|TAMA[ÑN]O|MORAL|"
    r"VALOR EN P[EX])",
    re.IGNORECASE,
)

SKIP_PATTERNS_ES = re.compile(
    r"^(INDICE|ÍNDICE|INTRODUCCION|INTRODUCCIÓN|APENDICE|APÉNDICE|"
    r"COMO USAR|CÓMO USAR|PREFACIO|CR[EÉ]DITOS|GLOSARIO|CONTENIDO|"
    r"MANUAL MONSTRUOSO|TABLA)",
    re.IGNORECASE,
)

ANCHOR_LABEL_ES = re.compile(r"^(CLIMA\s*/\s*TERREN|FRECUENCIA)", re.IGNORECASE)

# Formato clásico de los cuadernillos Monstrous Compendium/Annual en inglés
STAT_LABELS_EN = re.compile(
    r"(CLIMATE\s*/\s*TERRAIN|FREQUENCY|ORGANIZATION|ACTIVITY CYCLE|DIET|"
    r"INTELLIGENCE|TREASURE|ALIGNMENT|NO\.?\s*APPEARING|ARMOR CLASS|"
    r"MOVEMENT|HIT DICE|THAC0|NO\.?\s*OF ATTACKS|DAMAGE\s*/\s*ATTACK|"
    r"SPECIAL ATTACKS?|SPECIAL DEFENSES?|MAGIC RESISTANCE|SIZE|MORALE|"
    r"XP VALUE)",
    re.IGNORECASE,
)

SKIP_PATTERNS_EN = re.compile(
    r"^(INDEX|INTRODUCTION|APPENDIX|HOW TO USE|PREFACE|CREDITS|GLOSSARY|"
    r"CONTENTS|MONSTROUS COMPENDIUM|TABLE)",
    re.IGNORECASE,
)

ANCHOR_LABEL_EN = re.compile(r"^(CLIMATE\s*/\s*TERRAIN|FREQUENCY)", re.IGNORECASE)

LANG_PATTERNS = {
    "es": {
        "stat_labels": STAT_LABELS_ES,
        "skip_patterns": SKIP_PATTERNS_ES,
        "anchor_label": ANCHOR_LABEL_ES,
        "ocr_lang": "spa+eng",
    },
    "en": {
        "stat_labels": STAT_LABELS_EN,
        "skip_patterns": SKIP_PATTERNS_EN,
        "anchor_label": ANCHOR_LABEL_EN,
        "ocr_lang": "eng",
    },
}


SYSTEM_PROMPT = """Eres un asistente que convierte texto OCR (con posibles errores) extraído del Manual Monstruoso de AD&D 2ª Edición al formato markdown de ficha de monstruo usado en esta aplicación.

Genera ÚNICAMENTE el markdown con este formato exacto, sin texto adicional antes ni después:

---
nombre: [Nombre del monstruo en español]
ca: [Clase de Armadura, número solo, puede ser negativo]
dg: "[Dados de Golpe, ej: 4+1]"
thac0: [número solo]
ataques: [número de ataques]
daño: "[daño por ataque, ej: 1d8 / 1d6 / 1d4]"
movimiento: [movimiento en metros, número solo]
px: [Puntos de Experiencia, número solo. Si hay varios valores usa el del ejemplar normal/base]
alineamiento: [Alineamiento en español]
tamaño: [P/M/G, una letra]
---

# [Nombre del monstruo]

[Uno o dos párrafos de descripción general/ambientación del monstruo]

## Descripción

[Aspecto físico, comportamiento]

## Ataques

[Descripción de cómo ataca, ataques especiales, defensas especiales, resistencia mágica si tiene]

## Hábitat

[Frecuencia, organización, clima/terreno, dieta, inteligencia, tesoro — resumidos en prosa]

REGLAS IMPORTANTES:
- El texto de entrada viene de OCR y puede tener errores tipográficos (letras confundidas, palabras cortadas). Corrígelos usando tu conocimiento del Manual Monstruoso de AD&D 2ª edición.
- dg y daño siempre van entre comillas dobles en el YAML
- Los valores de texto van sin comillas salvo que contengan caracteres especiales (barras, signos +)
- Si un campo se desconoce, usa: -----
"""


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def ocr_page(pdf_path: str, page_num_1based: int, cache_dir: Path, ocr_lang: str) -> str:
    """OCR de una página con caché en disco (clave = hash del pdf + idioma + nº página)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    pdf_hash = hashlib.md5(pdf_path.encode()).hexdigest()[:10]
    cache_file = cache_dir / f"{pdf_hash}_{ocr_lang}_p{page_num_1based:04d}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    images = convert_from_path(
        pdf_path, dpi=200,
        first_page=page_num_1based, last_page=page_num_1based,
    )
    if not images:
        return ""
    text = pytesseract.image_to_string(images[0], lang=ocr_lang)
    cache_file.write_text(text, encoding="utf-8")
    return text


def extract_monster_name(page_text: str, patterns: dict) -> str | None:
    """El nombre es la línea inmediatamente anterior a la primera etiqueta de
    estadísticas (CLIMA/TERRENO o FRECUENCIA / CLIMATE-TERRAIN o FREQUENCY).
    El diseño a dos columnas hace que las primeras líneas de la página sean a
    veces restos de la entrada anterior (columna izquierda), así que no basta
    con tomar la primera línea."""
    anchor_label = patterns["anchor_label"]
    skip_patterns = patterns["skip_patterns"]
    lines = [l.strip() for l in page_text.splitlines()]
    # Una fila real de estadísticas es corta ("CLIMA/TERRENO: Cualquiera"),
    # a diferencia de las frases largas de la página de introducción que
    # también mencionan estas etiquetas en prosa.
    anchor_idx = next(
        (i for i, l in enumerate(lines) if anchor_label.match(l) and len(l) <= 60),
        None,
    )
    if anchor_idx is None:
        return None

    name = None
    name_idx = None
    for i in range(anchor_idx - 1, -1, -1):
        line = lines[i]
        if not line:
            continue
        if len(line) < 3 or len(line) > 60:
            return None
        if re.match(r"^[0-9\W]+$", line):
            return None
        if skip_patterns.match(line):
            return None
        if len(line.split()) > 5:
            # Tabla con varias subespecies fusionadas en una sola línea de
            # cabecera (ej. "Pilosa Grande Enorme Gigante..."): no es un
            # nombre válido de una única entrada, requiere revisión manual.
            return None
        name, name_idx = line, i
        break

    if name is None:
        return None

    # Si el nombre encontrado es una sola palabra, puede ser un calificador
    # de la línea anterior (ej. "Basilisco" + "Menor" -> "Basilisco Menor").
    # Solo se combina en ese caso concreto; con nombres de varias palabras es
    # demasiado arriesgado (riesgo de fusionar dos monstruos distintos de una
    # tabla multiespecie), así que se deja el nombre tal cual.
    if len(name.split()) == 1:
        for i in range(name_idx - 1, -1, -1):
            prev = lines[i]
            if not prev:
                continue
            if prev.endswith("-") or not prev[0].isupper():
                break  # resto de frase de la columna anterior (fragmento en minúscula)
            if len(prev.split()) > 1 or len(prev) > 40:
                break  # no es un simple calificador de una palabra -> no combinar
            name = f"{prev} {name}"
            break

    return name


def has_stat_block(page_text: str, patterns: dict) -> bool:
    return len(set(m.upper() for m in patterns["stat_labels"].findall(page_text))) >= 5


def call_ollama(page_text: str, monster_name: str, lang: str) -> str | None:
    source_note = (
        "El texto OCR está en inglés (Monstrous Compendium/Annual original); tradúcelo al español conservando la terminología habitual de AD&D 2ª edición en español.\n\n"
        if lang == "en" else ""
    )
    prompt = (
        f"Genera la ficha de monstruo para '{monster_name}'.\n\n"
        f"{source_note}"
        f"Texto OCR extraído del PDF:\n{page_text[:3500]}"
    )
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 900},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"    ERROR Ollama: {e}")
        return None


def run(pdf_path: str, resources_dir: str, dry_run: bool = False,
        start_page: int = 1, end_page: int | None = None, lang: str = "es"):
    out = Path(resources_dir)
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(OCR_CACHE_DIR)
    patterns = LANG_PATTERNS[lang]
    ocr_lang = patterns["ocr_lang"]

    import fitz
    total = len(fitz.open(pdf_path))
    end_page = end_page or total

    generated = 0
    skipped_exists = 0
    skipped_no_name = 0
    skipped_no_statblock = 0
    skipped_short = 0
    errors = 0
    review_pages = []

    print(f"PDF: {Path(pdf_path).name}  ({total} páginas, procesando {start_page}-{end_page})")
    print(f"Destino: {out}\n")

    for page_num in range(start_page, end_page + 1):
        page_text = ocr_page(pdf_path, page_num, cache_dir, ocr_lang)

        if not has_stat_block(page_text, patterns):
            skipped_no_statblock += 1
            continue

        name = extract_monster_name(page_text, patterns)
        if not name:
            skipped_no_name += 1
            review_pages.append(page_num)
            continue

        slug = slugify(name)
        md_path = out / f"{slug}.md"

        if md_path.exists():
            print(f"  [EXISTE]  p{page_num:03d}  {name}")
            skipped_exists += 1
            continue

        if len(page_text.strip()) < MIN_TEXT_LENGTH:
            print(f"  [CORTO]   p{page_num:03d}  {name} — texto insuficiente ({len(page_text)} chars)")
            skipped_short += 1
            continue

        if dry_run:
            print(f"  [DRY-RUN] p{page_num:03d}  {name} → {slug}.md")
            generated += 1
            continue

        print(f"  [GEN]     p{page_num:03d}  {name} → {slug}.md ...", end="", flush=True)
        t0 = time.time()
        result = call_ollama(page_text, name, lang)
        elapsed = time.time() - t0

        if not result:
            print(f" ERROR ({elapsed:.0f}s)")
            errors += 1
            continue

        if "---" not in result or "nombre:" not in result:
            print(f" FORMATO INVÁLIDO ({elapsed:.0f}s)")
            (out / f"_revisar_{slug}.md").write_text(result, encoding="utf-8")
            errors += 1
            continue

        md_path.write_text(result, encoding="utf-8")
        print(f" OK ({elapsed:.0f}s)")
        generated += 1

    print(f"\nResumen:")
    print(f"  Generados:         {generated}")
    print(f"  Ya existían:       {skipped_exists}")
    print(f"  Sin nombre:        {skipped_no_name}")
    print(f"  Sin bloque stats:  {skipped_no_statblock}")
    print(f"  Texto corto:       {skipped_short}")
    print(f"  Errores:           {errors}")
    if review_pages:
        print(f"\n  Páginas con stat block pero sin nombre claro (revisar manualmente): {review_pages}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=DEFAULT_PDF)
    parser.add_argument("--out", default=DEFAULT_RESOURCES)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--lang", choices=["es", "en"], default="es")
    args = parser.parse_args()
    run(args.pdf, args.out, dry_run=args.dry_run, start_page=args.start_page,
        end_page=args.end_page, lang=args.lang)


if __name__ == "__main__":
    main()
