#!/usr/bin/env python3
"""
Migración: añade el campo 'game_line' a todos los chunks de biblioteca_pdfs.

El campo permite filtrar por sistema/edición con $eq en lugar de depender
de $contains (no soportado en metadata where de ChromaDB).

Valores de game_line:
  dnd5e      — D&D 5ª edición
  adnd2e     — AD&D 2ª edición (genérico, excluye Dark Sun)
  darksun    — Dark Sun (AD&D 2ª edición / Dark Sun)
  mothership — Mothership
  otros      — cualquier otra cosa

Uso:
  venv/bin/python3 utils/rag_migrate_game_line.py
  venv/bin/python3 utils/rag_migrate_game_line.py --dry-run
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from config import Config
from pathlib import Path

CHROMA_DIR   = Path(Config.CHROMA_DIR)
COLLECTION   = "biblioteca_pdfs"
BATCH_SIZE   = 500


def get_game_line(source: str) -> str:
    """Determina la game_line a partir de la ruta del source."""
    if "Dark Sun" in source:
        return "darksun"
    if "AD&D 2" in source or "AD&D2" in source:
        return "adnd2e"
    if "D&D 5" in source:
        return "dnd5e"
    if "Mothership" in source:
        return "mothership"
    return "otros"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin aplicarlos")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        col = client.get_collection(COLLECTION)
    except Exception:
        print(f"✗ Colección '{COLLECTION}' no encontrada")
        sys.exit(1)

    total = col.count()
    print(f"Total chunks: {total}")
    if args.dry_run:
        print("(modo dry-run, no se aplicarán cambios)")

    # Estadísticas
    counts = {"dnd5e": 0, "adnd2e": 0, "darksun": 0, "mothership": 0, "otros": 0}
    updated = 0
    skipped = 0

    offset = 0
    while offset < total:
        batch = col.get(
            limit=BATCH_SIZE,
            offset=offset,
            include=["metadatas"],
        )
        ids = batch["ids"]
        metadatas = batch["metadatas"]
        if not ids:
            break

        new_ids, new_metas = [], []
        for doc_id, meta in zip(ids, metadatas):
            if "game_line" in meta:
                skipped += 1
                continue
            gl = get_game_line(meta.get("source", ""))
            counts[gl] += 1
            new_ids.append(doc_id)
            new_metas.append({**meta, "game_line": gl})

        if new_ids and not args.dry_run:
            col.update(ids=new_ids, metadatas=new_metas)

        updated += len(new_ids)
        offset += len(ids)

        pct = offset / total * 100
        print(f"\r  {offset}/{total} ({pct:.0f}%) — actualizados: {updated}, ya tenían game_line: {skipped}", end="", flush=True)

    print(f"\n\n✅ Migración completa")
    print(f"   Actualizados: {updated}")
    print(f"   Ya tenían game_line (saltados): {skipped}")
    print(f"\n   Distribución:")
    for gl, n in sorted(counts.items(), key=lambda x: -x[1]):
        if n:
            print(f"   • {gl}: {n}")


if __name__ == "__main__":
    main()
