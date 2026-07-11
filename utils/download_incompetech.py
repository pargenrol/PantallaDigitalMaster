#!/usr/bin/env python3
"""
Descarga música de Kevin MacLeod (incompetech.com) y la categoriza
automáticamente según nuestras ambientaciones de rol.

Uso:
    python3 utils/download_incompetech.py [--dry-run] [--limit N] [--cat CATEGORIA]

El script:
1. Descarga el catálogo JSON de incompetech.com/music/royalty-free/pieces.json (1442 pistas)
2. Mapea los "feels" de cada pista a nuestras categorías de rol
3. Descarga los mp3 a static/uploads/audio/
4. Actualiza static/uploads/audio/metadata.json

Categorías: combate, exploración, tensión, ciudad, mazmorra, descanso, sting, ambiente

La música de Kevin MacLeod está bajo licencia Creative Commons Attribution 4.0.
Atribución: "Music by Kevin MacLeod (incompetech.com) – CC BY 4.0"
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

# ── Rutas ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
AUDIO_DIR = os.path.join(PROJECT_DIR, "static", "uploads", "audio")
METADATA_PATH = os.path.join(AUDIO_DIR, "metadata.json")

# ── URLs de incompetech ───────────────────────────────────────────────────────
CATALOG_URL = "https://incompetech.com/music/royalty-free/pieces.json"
DOWNLOAD_BASE = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"

# ── Géneros por ID ────────────────────────────────────────────────────────────
GENRE_ID = {
    "2": "African", "3": "Blues", "4": "Classical", "5": "Contemporary",
    "6": "Disco", "7": "Electronica", "8": "Funk", "9": "Holiday",
    "10": "Horror", "11": "Jazz", "12": "Latin", "13": "Modern",
    "14": "Musical", "15": "Polka", "16": "Pop", "18": "Reggae",
    "19": "Rock", "20": "Silent Film Score", "21": "Ska", "22": "Soundtrack",
    "23": "Stings", "24": "Unclassifiable", "25": "World", "26": "Urban",
}

# Géneros excluidos
EXCLUDE_GENRES = {"Holiday", "Polka", "Disco", "Reggae", "Ska", "Stings"}

# ── Mapeo feel → categoría ────────────────────────────────────────────────────
# Feels reales de incompetech.com:
# Action, Aggressive, Bouncy, Bright, Calming, Calm, Dark, Driving,
# Eerie, Epic, Grooving, Humorous, Intense, Mysterious, Mystical,
# Relaxed, Somber, Suspenseful, Unnerving, Uplifting, Ren Faire, Medieval
FEEL_TO_CATEGORY = {
    "Action":       "combate",
    "Aggressive":   "combate",
    "Intense":      "combate",
    "Epic":         "combate",
    "Driving":      "combate",     # rítmico y tenso → también combate

    "Uplifting":    "exploración",
    "Bright":       "exploración",
    "Mystical":     "exploración",
    "Ren Faire":    "exploración",
    "Medieval":     "exploración",

    "Suspenseful":  "tensión",
    "Unnerving":    "tensión",
    "Mysterious":   "tensión",
    "Eerie":        "tensión",

    "Grooving":     "ciudad",
    "Bouncy":       "ciudad",
    "Humorous":     "ciudad",

    "Dark":         "mazmorra",
    "Somber":       "mazmorra",

    "Relaxed":      "descanso",
    "Calming":      "descanso",
    "Calm":         "descanso",
}

# Géneros que fuerzan categoría independientemente del feel
GENRE_OVERRIDE = {
    "Jazz":     "ciudad",
    "Horror":   "tensión",
}


def parse_duration(length_str):
    """Convierte '00:05:07' o '03:24' a segundos."""
    parts = length_str.strip().split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
    except Exception:
        pass
    return 0


def slugify(name):
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    return name.strip("-")


def load_metadata():
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH) as f:
            return json.load(f)
    return {}


def save_metadata(metadata):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def infer_categories(piece):
    """Devuelve lista de categorías para una pista."""
    genre_name = GENRE_ID.get(str(piece.get("genre", "")).strip(), "")

    # Excluir géneros no aptos
    if genre_name in EXCLUDE_GENRES:
        return []

    # Genre override directo
    if genre_name in GENRE_OVERRIDE:
        return [GENRE_OVERRIDE[genre_name]]

    feels = [f.strip() for f in piece.get("feel", "").split(",") if f.strip()]

    # Stings: género "Stings" o duración < 90s
    duration = parse_duration(piece.get("length", "").strip())
    if genre_name == "Stings" or (duration > 0 and duration < 90):
        return ["sting"]

    cats = set()
    for feel in feels:
        cat = FEEL_TO_CATEGORY.get(feel)
        if cat:
            cats.add(cat)

    # "ambiente": Soundtrack/Classical/Contemporary sin categoría específica fuerte
    if not cats and genre_name in ("Soundtrack", "Classical", "Contemporary", "Unclassifiable"):
        cats.add("ambiente")

    # También piezas "Mystical" en géneros orquestales sin otra categoría aún
    if genre_name in ("Soundtrack", "Classical") and not cats:
        cats.add("ambiente")

    return sorted(cats)


def fetch_catalog():
    print(f"Descargando catálogo desde {CATALOG_URL} ...")
    req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    print(f"Catálogo: {len(data)} pistas")
    return data


def safe_filename(piece):
    """Genera el nombre de archivo local para una pista."""
    orig = piece.get("filename", piece.get("title", "unknown") + ".mp3")
    # Prefijo para identificarlos fácilmente
    base = os.path.splitext(orig)[0]
    return f"incompetech_{slugify(base)}.mp3"


def download_mp3(piece, dry_run=False):
    """Descarga el mp3. Devuelve (local_filename, ok)."""
    orig_filename = piece.get("filename", "")
    if not orig_filename:
        return None, False

    local_name = safe_filename(piece)
    dest = os.path.join(AUDIO_DIR, local_name)

    if os.path.exists(dest):
        return local_name, True  # ya existe

    if dry_run:
        return local_name, True

    url = DOWNLOAD_BASE + urllib.parse.quote(orig_filename)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://incompetech.com/",
        })
        with urllib.request.urlopen(req, timeout=45) as r:
            content_type = r.headers.get("Content-Type", "")
            if "text/html" in content_type:
                return local_name, False
            data = r.read()
            if len(data) < 5_000:
                return local_name, False
            with open(dest, "wb") as f:
                f.write(data)
        return local_name, True
    except Exception as e:
        return local_name, False


def main():
    parser = argparse.ArgumentParser(description="Descarga música de incompetech categorizada por rol")
    parser.add_argument("--dry-run", action="store_true", help="No descargar, solo mostrar el plan")
    parser.add_argument("--limit", type=int, default=10,
                        help="Máximo de pistas por categoría (default: 10, 0 = todas)")
    parser.add_argument("--cat", type=str, default="",
                        help="Solo procesar esta categoría")
    parser.add_argument("--list", action="store_true",
                        help="Solo listar pistas disponibles sin descargar")
    args = parser.parse_args()

    try:
        catalog = fetch_catalog()
    except Exception as e:
        print(f"Error descargando catálogo: {e}")
        sys.exit(1)

    # Clasificar pistas
    by_category = {}
    skipped = 0
    for piece in catalog:
        cats = infer_categories(piece)
        if not cats:
            skipped += 1
            continue
        for cat in cats:
            by_category.setdefault(cat, []).append((piece, cats))

    print(f"\nClasificación ({skipped} pistas descartadas):")
    for cat in sorted(by_category):
        print(f"  {cat:12s}: {len(by_category[cat])} pistas")

    if args.list:
        print()
        for cat in sorted(by_category):
            if args.cat and cat != args.cat:
                continue
            print(f"\n── {cat.upper()} ──")
            for piece, cats in by_category[cat]:
                print(f"  [{', '.join(cats)}] {piece['title']} ({piece.get('length','?')}) – {piece.get('feel','')}")
        return

    print()
    metadata = load_metadata()
    stats = {}
    errors = []

    for cat in sorted(by_category):
        if args.cat and cat != args.cat:
            continue

        items = by_category[cat]
        if args.limit:
            items = items[:args.limit]

        print(f"\n── {cat.upper()} ({len(items)} pistas) ──")

        for piece, all_cats in items:
            title = piece.get("title", "?")
            already = safe_filename(piece)
            existing = os.path.exists(os.path.join(AUDIO_DIR, already))
            label = "(ya existe)" if existing else ""

            if args.dry_run:
                print(f"  [dry-run] {title} → {all_cats} {label}")
                continue

            print(f"  {title}...", end=" ", flush=True)
            local_name, ok = download_mp3(piece, dry_run=False)

            if ok:
                print(f"✓ {label}")
                if local_name not in metadata:
                    metadata[local_name] = {"categories": all_cats, "systems": []}
                else:
                    existing_cats = set(metadata[local_name].get("categories", []))
                    metadata[local_name]["categories"] = sorted(existing_cats | set(all_cats))
                stats[cat] = stats.get(cat, 0) + 1
            else:
                print("✗ (falló)")
                errors.append(title)

            if not existing:
                time.sleep(0.4)  # respetar servidor

    if not args.dry_run:
        save_metadata(metadata)
        print(f"\nmetadata.json actualizado → {METADATA_PATH}")

    print("\n── Resumen ──")
    for cat, count in sorted(stats.items()):
        print(f"  {cat:12s}: {count} descargadas")
    if errors:
        print(f"\nFallidas ({len(errors)}):")
        for e in errors[:20]:
            print(f"  - {e}")

    print(f"""
Atribución requerida (CC BY 4.0):
  Music by Kevin MacLeod (incompetech.com)
  Licensed under Creative Commons: By Attribution 4.0 License
  http://creativecommons.org/licenses/by/4.0/
""")


if __name__ == "__main__":
    main()
