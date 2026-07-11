#!/usr/bin/env python3
"""
Vincula imágenes de monstruos a sus fichas markdown de D&D 5e.

Acciones:
1. Limpia comillas innecesarias en portrait_path existentes
2. Añade portrait_path a fichas que no tienen imagen asignada
   si existe una imagen con el mismo slug (nombre del fichero .md)

Uso:
    python3 utils/link_monster_portraits.py [--dry-run]
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
MONSTERS_DIR = os.path.join(PROJECT_DIR, "resources", "dnd5e", "monsters")
IMG_DIR = os.path.join(PROJECT_DIR, "static", "img", "monsters", "dnd5e")
IMG_URL_BASE = "/static/img/monsters/dnd5e"


def get_portrait_path(slug):
    img_path = os.path.join(IMG_DIR, f"{slug}.jpeg")
    if os.path.exists(img_path):
        return f"{IMG_URL_BASE}/{slug}.jpeg"
    return None


def fix_frontmatter(content, slug, dry_run=False):
    """Devuelve (nuevo_contenido, acción) o (content, None) si no hay cambios."""

    # Buscar portrait_path existente (con o sin comillas)
    m = re.search(r'^(portrait_path:\s*)(.+)$', content, re.MULTILINE)

    if m:
        raw_value = m.group(2).strip()
        clean_value = raw_value.strip('"').strip("'")

        if raw_value == clean_value:
            return content, None  # ya está limpio

        new_line = f"portrait_path: {clean_value}"
        new_content = content[:m.start()] + new_line + content[m.end():]
        return new_content, f"limpiado comillas → {clean_value}"

    # No tiene portrait_path — intentar asignar por slug
    portrait = get_portrait_path(slug)
    if not portrait:
        return content, None  # no hay imagen para este slug

    # Insertar portrait_path al final del bloque frontmatter (antes del segundo ---)
    # El frontmatter empieza en línea 1 con --- y termina con el siguiente ---
    fm_end = re.search(r'^---\s*$', content[3:], re.MULTILINE)
    if not fm_end:
        return content, None

    insert_pos = 3 + fm_end.start()  # posición del segundo ---
    new_content = content[:insert_pos] + f"portrait_path: {portrait}\n" + content[insert_pos:]
    return new_content, f"añadido → {portrait}"


def main():
    parser = argparse.ArgumentParser(description="Vincula imágenes de monstruos 5e a sus fichas md")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin escribir")
    args = parser.parse_args()

    files = sorted(f for f in os.listdir(MONSTERS_DIR) if f.endswith(".md"))
    cleaned = 0
    added = 0
    skipped = 0

    for fname in files:
        slug = fname[:-3]
        path = os.path.join(MONSTERS_DIR, fname)

        with open(path, encoding="utf-8") as f:
            content = f.read()

        new_content, action = fix_frontmatter(content, slug)

        if action is None:
            skipped += 1
            continue

        if "limpiado" in action:
            cleaned += 1
        else:
            added += 1

        print(f"  {fname}: {action}")

        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

    print(f"\nResumen{'  [DRY RUN]' if args.dry_run else ''}:")
    print(f"  Comillas limpiadas: {cleaned}")
    print(f"  portrait_path añadidos: {added}")
    print(f"  Sin cambios: {skipped}")
    print(f"  Total fichas: {len(files)}")


if __name__ == "__main__":
    main()
