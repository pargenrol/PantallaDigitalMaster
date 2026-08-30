#!/usr/bin/env python3
"""
Extrae imágenes del Manual de Monstruos de D&D 5e y las asocia
al monstruo de cada página por el texto en mayúsculas del inicio.

Uso:
    venv/bin/python3 utils/extract_monster_images.py
    venv/bin/python3 utils/extract_monster_images.py --pdf "ruta/al/otro.pdf" --out "static/img/monsters/5e"
    venv/bin/python3 utils/extract_monster_images.py --dry-run   # solo muestra qué haría
"""

import fitz  # PyMuPDF
import re
import argparse
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PDF = str(
    BASE_DIR.parent / "rol-biblioteca" / "biblioteca" /
    "Dungeons & Dragons/D&D 5ª edición/Core y Suplementos/"
    "D&D - 5.0 - Edge - Manual de Monstruos.pdf"
)
DEFAULT_OUT = str(BASE_DIR / "static" / "img" / "monsters" / "dnd5e")

MIN_IMAGE_SIZE = 10_000  # bytes — filtra iconos y decoraciones pequeñas
MIN_IMAGE_WIDTH = 100    # píxeles

# Páginas a ignorar (intro, índice, reglas) — texto en mayúsculas que no es monstruo
SKIP_PATTERNS = re.compile(
    r"^(INDICE|ÍNDICE|INTRODUCCION|INTRODUCCIÓN|APENDICE|APÉNDICE|"
    r"CLASE DE ARMADURA|DESAFIO|DESAFÍO|LANZAMIENTO|REGLAS|"
    r"BONIFICADOR|80NIFICADOR|QUE MONSTRUOS|QUÉ MONSTRUOS|"
    r"LA NATURALEZA|S SON MONTURAS).*",
    re.IGNORECASE,
)

# Texto decorativo / citas (empieza con puntuación o tiene muchas palabras)
QUOTE_PATTERN = re.compile(r"^[^A-ZÁÉÍÓÚÜÑ]|.{51,}")


def slugify(text: str) -> str:
    """Convierte 'AZOTAMENTES' → 'azotamentes', 'DRAGÓN ROJO' → 'dragon_rojo'"""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text


def extract_monster_name(page) -> str | None:
    """
    Intenta detectar el nombre del monstruo en la página.
    Busca el bloque de texto más largo en mayúsculas cerca del inicio de la página.
    """
    blocks = page.get_text("blocks")  # [(x0,y0,x1,y1,text,block_no,block_type)]
    page_height = page.rect.height

    candidates = []
    for block in blocks:
        text = block[4].strip()
        # Solo bloques en el tercio superior de la página
        if block[1] > page_height * 0.5:
            continue
        # Líneas en mayúsculas (nombre de monstruo) de longitud razonable
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for line in lines:
            if (
                line.isupper()
                and 3 <= len(line) <= 50
                and not re.match(r"^[0-9\W]+$", line)
            ):
                candidates.append((block[1], line))  # (y_pos, text)

    if not candidates:
        return None
    # El más alto en la página
    candidates.sort(key=lambda x: x[0])
    name = candidates[0][1]

    # Filtrar páginas de reglas / intro
    if SKIP_PATTERNS.match(name) or QUOTE_PATTERN.match(name):
        return None

    return name


def extract_best_image(page, doc) -> bytes | None:
    """Extrae la imagen más grande de la página (en bytes PNG)."""
    images = page.get_images(full=True)
    best = None
    best_size = 0

    for img_info in images:
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            data = base_image["image"]
            w = base_image.get("width", 0)
            if len(data) > best_size and len(data) >= MIN_IMAGE_SIZE and w >= MIN_IMAGE_WIDTH:
                best_size = len(data)
                best = (data, base_image["ext"])
        except Exception:
            continue

    return best


def run(pdf_path: str, out_dir: str, dry_run: bool = False):
    out = Path(out_dir)
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = len(doc)
    saved = 0
    skipped_no_name = 0
    skipped_no_img = 0
    skipped_small = 0

    print(f"PDF: {Path(pdf_path).name}  ({total} páginas)")
    print(f"Destino: {out}\n")

    for page_num in range(total):
        page = doc[page_num]
        name = extract_monster_name(page)

        if not name:
            skipped_no_name += 1
            continue

        slug = slugify(name)
        result = extract_best_image(page, doc)

        if result is None:
            skipped_no_img += 1
            continue

        data, ext = result
        filename = out / f"{slug}.{ext}"

        # No sobreescribir si ya existe
        if filename.exists():
            print(f"  [EXISTE]  p{page_num+1:03d}  {name} → {filename.name}")
            continue

        if dry_run:
            print(f"  [DRY-RUN] p{page_num+1:03d}  {name} → {filename.name}  ({len(data)//1024}KB)")
        else:
            filename.write_bytes(data)
            print(f"  [OK]      p{page_num+1:03d}  {name} → {filename.name}  ({len(data)//1024}KB)")

        saved += 1

    print(f"\nResumen:")
    print(f"  Guardadas:        {saved}")
    print(f"  Sin nombre:       {skipped_no_name}")
    print(f"  Sin imagen válida:{skipped_no_img}")


def main():
    parser = argparse.ArgumentParser(description="Extrae imágenes de monstruos de PDFs D&D 5e")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Ruta al PDF")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Carpeta de salida")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra, no escribe")
    args = parser.parse_args()

    run(args.pdf, args.out, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
