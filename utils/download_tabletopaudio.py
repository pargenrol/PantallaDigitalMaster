#!/usr/bin/env python3
"""
Descarga música de Tabletop Audio (tabletopaudio.com) y la categoriza
automáticamente según nuestras ambientaciones de rol.

Uso:
    python3 utils/download_tabletopaudio.py [--dry-run] [--limit N] [--cat CATEGORIA]

El script:
1. Descarga el catálogo de canciones desde el JS de la web (SongList)
2. Descarga los tags de categorización (tags_data.js)
3. Mapea los moods/actions/biomes de TTA a nuestras categorías de rol
4. Descarga los mp3 a static/uploads/audio/
5. Actualiza static/uploads/audio/metadata.json

Categorías: combate, exploración, tensión, ciudad, mazmorra, descanso, ambiente

La música de Tabletop Audio es gratuita para uso personal/no comercial.
Atribución: "Ambient music by Tabletop Audio (tabletopaudio.com)"
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

# ── URLs de Tabletop Audio ────────────────────────────────────────────────────
TTA_BASE = "https://sounds.tabletopaudio.com/"
MAIN_JS_URL = "https://tabletopaudio.com/bootstrap/js/tta4XFADE4_min.js?d=07012026"
TAGS_JS_URL = "https://tabletopaudio.com/bootstrap/js/tags_data.js"

# ── Mapeo tags TTA → nuestras categorías ─────────────────────────────────────
# Moods TTA: peaceful, somber, optimistic, fun, dramatic, tension, mysterious, epic
# Actions TTA: explore, investigate, celebrate, ritual, sneak, chase, skirmish, monster, war, boss
# Biomes TTA: forest, desert, ice, mountains, swamp, underground, water, weather, planar, hellscape
# Civs TTA: cities, outposts, public, interiors, roads, transit, facilities, ruins, slums, temples

MOOD_TO_CAT = {
    "epic":        "combate",
    "dramatic":    "combate",
    "tension":     "tensión",
    "mysterious":  "tensión",
    "optimistic":  "exploración",
    "fun":         "ciudad",
    "peaceful":    "descanso",
    "somber":      "mazmorra",
}

ACTION_TO_CAT = {
    "war":         "combate",
    "skirmish":    "combate",
    "boss":        "combate",
    "chase":       "combate",
    "monster":     "tensión",
    "sneak":       "tensión",
    "investigate": "tensión",
    "explore":     "exploración",
    "celebrate":   "ciudad",
    "ritual":      "ambiente",
}

BIOME_TO_CAT = {
    "underground": "mazmorra",
    "hellscape":   "mazmorra",
    "planar":      "ambiente",
}

CIV_TO_CAT = {
    "cities":    "ciudad",
    "public":    "ciudad",
    "slums":     "ciudad",
    "outposts":  "ambiente",
    "temples":   "ambiente",
    "ruins":     "ambiente",
}


def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_songlist(js):
    """Extrae {song_id: {title, mp3_filename}} del JS minificado."""
    # Buscar base URL
    m = re.search(r'var\s+\w\s*=\s*["\'](' + re.escape(TTA_BASE) + r'[^"\']*)["\']', js)
    base = m.group(1) if m else TTA_BASE

    # Extraer SongList
    m = re.search(r'SongList\s*=\s*(\{.*?\});', js, re.DOTALL)
    if not m:
        return {}

    raw = m.group(1)

    # Parsear cada entrada: song_N:{title:"...",artist:i,mp3:e+"filename.mp3"}
    # La variable base puede ser 'e' o cualquier letra
    base_var = re.search(r'var\s+(\w)\s*=\s*["\']' + re.escape(base) + r'["\']', js)
    base_var_name = base_var.group(1) if base_var else 'e'

    entries = re.findall(
        r'song_(\d+)\s*:\s*\{[^}]*title\s*:\s*"([^"]+)"[^}]*mp3\s*:\s*\w\s*\+\s*"([^"]+)"',
        raw
    )

    songs = {}
    for song_id, title, filename in entries:
        songs[song_id] = {
            "title": title,
            "filename": filename,
            "url": base + filename,
        }
    return songs


def parse_tags(tags_js):
    """Extrae {song_id: {civ, biome, mood, action}} del tags_data.js."""
    # Transformar JS a JSON-like
    # useCaseTags = { "516": { civ: [], biome: [...], mood: [...], action: [...] }, ... }
    m = re.search(r'var\s+useCaseTags\s*=\s*(\{.*?\});', tags_js, re.DOTALL)
    if not m:
        return {}

    raw = m.group(1)

    tags = {}
    # Extraer cada entrada
    blocks = re.finditer(
        r'"(\d+)"\s*:\s*\{[^}]*?'
        r'civ\s*:\s*(\[[^\]]*\])[^}]*?'
        r'biome\s*:\s*(\[[^\]]*\])[^}]*?'
        r'mood\s*:\s*(\[[^\]]*\])[^}]*?'
        r'action\s*:\s*(\[[^\]]*\])',
        raw,
        re.DOTALL
    )
    for b in blocks:
        sid = b.group(1)
        def parse_list(s):
            return re.findall(r'"([^"]+)"', s)
        tags[sid] = {
            "civ":    parse_list(b.group(2)),
            "biome":  parse_list(b.group(3)),
            "mood":   parse_list(b.group(4)),
            "action": parse_list(b.group(5)),
        }
    return tags


def infer_categories(tag_entry):
    """Devuelve lista de categorías para una pista TTA."""
    if not tag_entry:
        return ["ambiente"]  # sin tags → ambiente genérico

    cats = set()

    for mood in tag_entry.get("mood", []):
        cat = MOOD_TO_CAT.get(mood)
        if cat:
            cats.add(cat)

    for action in tag_entry.get("action", []):
        cat = ACTION_TO_CAT.get(action)
        if cat:
            cats.add(cat)

    for biome in tag_entry.get("biome", []):
        cat = BIOME_TO_CAT.get(biome)
        if cat:
            cats.add(cat)

    for civ in tag_entry.get("civ", []):
        cat = CIV_TO_CAT.get(civ)
        if cat:
            cats.add(cat)

    # Limpiar combinaciones confusas: si es combate, quitar descanso
    if "combate" in cats:
        cats.discard("descanso")

    # Sin categoría clara → ambiente
    if not cats:
        cats.add("ambiente")

    return sorted(cats)


def safe_filename(song):
    return f"tta_{song['filename']}"


def load_metadata():
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH) as f:
            return json.load(f)
    return {}


def save_metadata(metadata):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def download_mp3(song, dry_run=False):
    local_name = safe_filename(song)
    dest = os.path.join(AUDIO_DIR, local_name)

    if os.path.exists(dest):
        return local_name, True

    if dry_run:
        return local_name, True

    os.makedirs(AUDIO_DIR, exist_ok=True)
    try:
        req = urllib.request.Request(song["url"], headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://tabletopaudio.com/",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            content_type = r.headers.get("Content-Type", "")
            if "text/html" in content_type:
                return local_name, False
            data = r.read()
            if len(data) < 5_000:
                return local_name, False
            with open(dest, "wb") as f:
                f.write(data)
        return local_name, True
    except Exception:
        return local_name, False


def main():
    parser = argparse.ArgumentParser(description="Descarga ambient music de Tabletop Audio")
    parser.add_argument("--dry-run", action="store_true", help="No descargar, solo mostrar el plan")
    parser.add_argument("--limit", type=int, default=8,
                        help="Máximo de pistas por categoría (default: 8, 0 = todas)")
    parser.add_argument("--cat", type=str, default="", help="Solo procesar esta categoría")
    parser.add_argument("--list", action="store_true", help="Solo listar sin descargar")
    args = parser.parse_args()

    print("Descargando catálogo de Tabletop Audio...")
    try:
        main_js = fetch_url(MAIN_JS_URL)
        tags_js = fetch_url(TAGS_JS_URL)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    songs = parse_songlist(main_js)
    tags = parse_tags(tags_js)
    print(f"Pistas: {len(songs)} | Con tags: {len(tags)}")

    # Clasificar
    by_category = {}
    for sid, song in songs.items():
        tag_entry = tags.get(sid, {})
        cats = infer_categories(tag_entry)
        for cat in cats:
            by_category.setdefault(cat, []).append((sid, song, cats))

    print(f"\nClasificación:")
    for cat in sorted(by_category):
        print(f"  {cat:12s}: {len(by_category[cat])} pistas")

    if args.list:
        print()
        for cat in sorted(by_category):
            if args.cat and cat != args.cat:
                continue
            print(f"\n── {cat.upper()} ──")
            for sid, song, cats in by_category[cat]:
                t = tags.get(sid, {})
                print(f"  [{', '.join(cats)}] {song['title']} "
                      f"(mood={t.get('mood',[])} action={t.get('action',[])})")
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

        for sid, song, all_cats in items:
            title = song["title"]
            local_name = safe_filename(song)
            already = os.path.exists(os.path.join(AUDIO_DIR, local_name))
            label = "(ya existe)" if already else ""

            if args.dry_run:
                print(f"  [dry-run] {title} → {all_cats} {label}")
                continue

            print(f"  {title}...", end=" ", flush=True)
            local_name, ok = download_mp3(song)

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

            if not already:
                time.sleep(0.5)

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

    print("""
Atribución:
  Ambient music by Tabletop Audio (tabletopaudio.com)
  Free for personal, non-commercial use.
""")


if __name__ == "__main__":
    main()
