#!/usr/bin/env python3
"""
Genera fichas de monstruos en markdown a partir del Manual de Monstruos 5e.
Por cada página que contenga un monstruo:
  1. Extrae el texto con PyMuPDF
  2. Envía el texto a qwen2.5 para que genere la ficha estructurada
  3. Guarda el resultado en resources/dnd5e/monsters/{slug}.md
  4. Enlaza la imagen si existe en static/img/monsters/dnd5e/{slug}.*

Solo procesa monstruos que no tengan ya su .md (incremental).

Uso:
    venv/bin/python3 utils/generate_monster_md.py
    venv/bin/python3 utils/generate_monster_md.py --dry-run
    venv/bin/python3 utils/generate_monster_md.py --pdf "ruta/otro.pdf" --system adnd2e
"""

import fitz
import re
import argparse
import unicodedata
import requests
import json
import time
from pathlib import Path

DEFAULT_PDF = (
    "/home/israel/rol-biblioteca/biblioteca/"
    "Dungeons & Dragons/D&D 5ª edición/Core y Suplementos/"
    "D&D - 5.0 - Edge - Manual de Monstruos.pdf"
)
DEFAULT_RESOURCES = "/home/israel/Pantallasistemas/resources/dnd5e/monsters"
DEFAULT_IMAGES = "/home/israel/Pantallasistemas/static/img/monsters/dnd5e"
IMAGE_URL_PREFIX = "/static/img/monsters/dnd5e"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct-q4_K_M"

MIN_TEXT_LENGTH = 200  # caracteres mínimos para considerar que hay ficha

# Páginas a ignorar (secciones que no son monstruos)
SKIP_PATTERNS = re.compile(
    r"^(INDICE|ÍNDICE|INTRODUCCION|INTRODUCCIÓN|APENDICE|APÉNDICE|"
    r"CLASE DE ARMADURA|DESAFIO|DESAFÍO|LANZAMIENTO|REGLAS|"
    r"BONIFICADOR|80NIFICADOR|QUE MONSTRUOS|QUÉ MONSTRUOS|"
    r"LA NATURALEZA|S SON MONTURAS|ACCIONES EN GUARIDA|"
    r"EFECTOS REGIONALES|VARIANTE)",
    re.IGNORECASE,
)
QUOTE_PATTERN = re.compile(r"^[^A-ZÁÉÍÓÚÜÑ]")


SYSTEM_PROMPT = """Eres un asistente que convierte texto extraído de un PDF de D&D 5e al formato markdown de ficha de monstruo.

Genera ÚNICAMENTE el markdown con este formato exacto, sin texto adicional antes ni después:

---
title: [Nombre del monstruo en español]
type: [Tipo: Bestia/No-muerto/Humanoide/Monstruosidad/Aberración/Celestial/Constructo/Dragón/Elemental/Hada/Infernal/Gigante/Planta/Limo/Celestial]
size: [Tamaño: Diminuto/Pequeño/Mediano/Grande/Enorme/Gargantuesco]
alignment: [Alineamiento en español]
hp: [número solo]
hp_roll: [ej: 7d8+14]
ac: [número solo]
challenge: [ej: 1/4 o 5]
xp: [número solo, sin puntos ni comas]
passive_perception: [número]
speed: [ej: 30 pies, volar 60 pies]
portrait_path: [IMAGEN_PATH]
---

### **Características**

| FUE | DES | CON | INT | SAB | CAR |
|:---:|:---:|:---:|:---:|:---:|:---:|
| X | X | X | X | X | X |
|(±X)|(±X)|(±X)|(±X)|(±X)|(±X)|

### **Sentidos, Idiomas y Resistencia**

[resistencias, inmunidades, sentidos, idiomas, bonificador de competencia]

[rasgos especiales si los hay, en formato: - ***Nombre rasgo.*** Descripción]

### **Acciones**

[acciones en formato: - **Nombre.** *Tipo de ataque*: descripción]

REGLAS IMPORTANTES para el YAML (entre --- y ---):
- Los valores de texto con caracteres especiales van entre comillas dobles: title: "Dragón Rojo"
- Los números van sin comillas: hp: 200
- Los guiones medios literales van entre comillas: challenge: "1/4"
- Nunca pongas paréntesis ni texto extra en valores YAML
- Si un campo se desconoce, usa: -----
"""


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def extract_monster_name(page) -> str | None:
    blocks = page.get_text("blocks")
    page_height = page.rect.height
    candidates = []
    for block in blocks:
        text = block[4].strip()
        if block[1] > page_height * 0.5:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.isupper() and 3 <= len(line) <= 50 and not re.match(r"^[0-9\W]+$", line):
                candidates.append((block[1], line))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    name = candidates[0][1]
    if SKIP_PATTERNS.match(name) or QUOTE_PATTERN.match(name):
        return None
    return name


def find_image_path(slug: str, images_dir: str) -> str:
    for ext in ("jpeg", "jpg", "png", "webp"):
        p = Path(images_dir) / f"{slug}.{ext}"
        if p.exists():
            return f"{IMAGE_URL_PREFIX}/{slug}.{ext}"
    return "-----"


def call_ollama(page_text: str, monster_name: str, image_path: str) -> str | None:
    prompt = (
        f"Genera la ficha de monstruo para '{monster_name}'.\n"
        f"Usa IMAGEN_PATH = {image_path}\n\n"
        f"Texto extraído del PDF:\n{page_text[:3000]}"
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


def run(pdf_path: str, resources_dir: str, images_dir: str, dry_run: bool = False):
    out = Path(resources_dir)
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = len(doc)
    generated = 0
    skipped_exists = 0
    skipped_no_name = 0
    skipped_short = 0
    errors = 0

    print(f"PDF: {Path(pdf_path).name}  ({total} páginas)")
    print(f"Destino: {out}\n")

    for page_num in range(total):
        page = doc[page_num]
        name = extract_monster_name(page)

        if not name:
            skipped_no_name += 1
            continue

        slug = slugify(name)
        md_path = out / f"{slug}.md"

        if md_path.exists():
            print(f"  [EXISTE]  p{page_num+1:03d}  {name}")
            skipped_exists += 1
            continue

        page_text = page.get_text()
        if len(page_text.strip()) < MIN_TEXT_LENGTH:
            print(f"  [CORTO]   p{page_num+1:03d}  {name} — texto insuficiente ({len(page_text)} chars)")
            skipped_short += 1
            continue

        image_path = find_image_path(slug, images_dir)

        if dry_run:
            print(f"  [DRY-RUN] p{page_num+1:03d}  {name} → {slug}.md  [img: {image_path}]")
            generated += 1
            continue

        print(f"  [GEN]     p{page_num+1:03d}  {name} → {slug}.md ...", end="", flush=True)
        t0 = time.time()
        result = call_ollama(page_text, name, image_path)
        elapsed = time.time() - t0

        if not result:
            print(f" ERROR ({elapsed:.0f}s)")
            errors += 1
            continue

        # Validar que tiene el frontmatter mínimo
        if "---" not in result or "title:" not in result:
            print(f" FORMATO INVÁLIDO ({elapsed:.0f}s)")
            # Guardar igualmente para revisión manual
            (out / f"_revisar_{slug}.md").write_text(result, encoding="utf-8")
            errors += 1
            continue

        md_path.write_text(result, encoding="utf-8")
        print(f" OK ({elapsed:.0f}s)")
        generated += 1

    print(f"\nResumen:")
    print(f"  Generados:     {generated}")
    print(f"  Ya existían:   {skipped_exists}")
    print(f"  Sin nombre:    {skipped_no_name}")
    print(f"  Texto corto:   {skipped_short}")
    print(f"  Errores:       {errors}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=DEFAULT_PDF)
    parser.add_argument("--out", default=DEFAULT_RESOURCES)
    parser.add_argument("--images", default=DEFAULT_IMAGES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.pdf, args.out, args.images, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
