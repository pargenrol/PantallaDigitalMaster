#!/usr/bin/env python3
"""
Indexador RAG para la PantallaDigitalMaster.

Extrae texto de los PDFs de la biblioteca de rol, los trocea en chunks
y los almacena en ChromaDB con embeddings de nomic-embed-text.

Uso:
  python utils/rag_indexer.py                  # indexa las carpetas configuradas en config.py
  python utils/rag_indexer.py --folder "Otros/Mothership"  # añade una carpeta concreta
  python utils/rag_indexer.py --grimoire-only  # solo el grimorio markdown de /resources/
  python utils/rag_indexer.py --list           # muestra qué hay indexado
"""

import sys
import os
import json
import argparse
import hashlib
import re
import time
import urllib.request

# Añadir el directorio raíz al path para importar config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import fitz           # pymupdf
import chromadb
import frontmatter    # python-frontmatter, ya en requirements.txt

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# ── Configuración ──────────────────────────────────────────────────────────────

from config import Config

BIBLIOTECA   = Path(Config.BIBLIOTECA_PATH)
CHROMA_DIR   = Path(Config.CHROMA_DIR)
OLLAMA_URL   = Config.OLLAMA_URL
EMBED_MODEL  = Config.OLLAMA_EMBED_MODEL
CHUNK_SIZE   = Config.RAG_CHUNK_SIZE
CHUNK_OVERLAP = Config.RAG_CHUNK_OVERLAP

RESOURCES_DIR = Path(__file__).parent.parent / "resources"

COLLECTION_PDFS     = "biblioteca_pdfs"
COLLECTION_GRIMOIRE = "grimoire_md"

# Commit a ChromaDB cada N chunks para no perder trabajo si se interrumpe
BATCH_SIZE = 50


# ── ChromaDB ───────────────────────────────────────────────────────────────────

def get_chroma_client():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection(client, name):
    return client.get_or_create_collection(
        name=name,
        metadata={
            "hnsw:space": "cosine",
            "hnsw:M": 8,              # default 16 → mitad de conexiones, mucho menos disco
            "hnsw:construction_ef": 100,  # default 200 → construcción más ligera
        },
    )


# ── Embeddings ─────────────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    """Genera embedding con nomic-embed-text vía Ollama."""
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["embedding"]


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Divide el texto en chunks por palabras (aproximación a tokens).
    Mantiene solapamiento entre chunks para no perder contexto en los bordes.
    """
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ── Extracción de texto PDF ────────────────────────────────────────────────────

def clean_text(raw: str) -> str:
    """Limpia texto extraído: une palabras partidas con guión, colapsa espacios."""
    lines = raw.splitlines()
    buf, paragraphs = [], []
    for line in lines:
        s = line.strip()
        if not s:
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
        else:
            if buf and buf[-1].endswith("-"):
                buf[-1] = buf[-1][:-1] + s
            else:
                buf.append(s)
    if buf:
        paragraphs.append(" ".join(buf))
    return "\n\n".join(paragraphs)


def extract_pages_ocr(pdf_path: Path) -> list[tuple[int, str]]:
    """OCR con tesseract para PDFs escaneados (sin texto digital).
    Procesa página a página para no cargar todo el PDF en RAM."""
    try:
        doc = fitz.open(str(pdf_path))
        n_pages = len(doc)
        doc.close()
    except Exception as e:
        print(f"  ✗ OCR: no se pudo abrir: {e}")
        return []

    pages = []
    for i in range(n_pages):
        try:
            images = convert_from_path(
                str(pdf_path), dpi=150,
                first_page=i + 1, last_page=i + 1,
            )
            if not images:
                continue
            raw = pytesseract.image_to_string(images[0], lang="spa+eng")
        except Exception:
            continue
        clean = clean_text(raw)
        # Descartar páginas con muy poco texto (OCR de imágenes/tablas/páginas en blanco)
        if len(clean.split()) >= 30:
            pages.append((i + 1, clean))
    return pages


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """
    Extrae texto de cada página del PDF.
    Intenta primero PyMuPDF (texto digital); si el PDF está escaneado,
    cae back a OCR con tesseract.
    Devuelve lista de (numero_pagina_1based, texto_limpio).
    """
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"  ✗ No se pudo abrir: {e}")
        return []

    pages = []
    for i, page in enumerate(doc):
        raw = page.get_text().strip()
        if not raw:
            continue
        clean = clean_text(raw)
        if clean:
            pages.append((i + 1, clean))
    doc.close()

    if pages:
        return pages

    # Sin texto digital → intentar OCR
    if OCR_AVAILABLE:
        print(f"OCR… ", end="", flush=True)
        return extract_pages_ocr(pdf_path)

    return []


# ── ID determinista ────────────────────────────────────────────────────────────

def make_id(rel_path: str, page: int, chunk_idx: int) -> str:
    key = f"{rel_path}::p{page}::c{chunk_idx}"
    return hashlib.md5(key.encode()).hexdigest()


# ── Mapeo de carpeta a game_line ───────────────────────────────────────────────

def folder_to_game_line(folder_rel: str) -> str:
    """Deriva el id de sistema (game_line) a partir de la carpeta relativa."""
    p = folder_rel.replace("\\", "/")
    if "D&D 5ª edición" in p or "D&D 5a edicion" in p:
        return "dnd5e"
    if "AD&D 2ª edición/Dark Sun" in p or "AD&D 2a edicion/Dark Sun" in p:
        return "darksun"
    if "AD&D 2ª edición" in p or "AD&D 2a edicion" in p:
        return "adnd2e"
    if "Mothership" in p:
        return "mothership"
    return folder_rel.split("/")[0]  # fallback: carpeta raíz


# ── Indexado de PDFs ───────────────────────────────────────────────────────────

def already_indexed(collection, pdf_rel_path: str) -> bool:
    """Comprueba si ya existe algún chunk de este PDF en la colección."""
    results = collection.get(where={"source": pdf_rel_path}, limit=1)
    return len(results["ids"]) > 0


def index_pdf(collection, pdf_path: Path, rel_path: str, system: str, game_line: str | None = None):
    """Indexa un PDF completo en la colección, por batches."""
    if already_indexed(collection, rel_path):
        print(f"  ↩ Ya indexado, saltando")
        return 0

    pages = extract_pages(pdf_path)
    if not pages:
        print(f"  ✗ Sin texto extraíble")
        return 0

    ids, embeddings, documents, metadatas = [], [], [], []
    total_chunks = 0

    for page_num, page_text in pages:
        chunks = chunk_text(page_text)
        for chunk_idx, chunk in enumerate(chunks):
            doc_id = make_id(rel_path, page_num, chunk_idx)
            try:
                emb = embed(chunk)
            except Exception as e:
                print(f"  ✗ Error embedding p{page_num}c{chunk_idx}: {e}")
                continue

            ids.append(doc_id)
            embeddings.append(emb)
            documents.append(chunk)
            meta = {
                "source": rel_path,
                "system": system,
                "page": page_num,
                "chunk_index": chunk_idx,
            }
            if game_line:
                meta["game_line"] = game_line
            metadatas.append(meta)
            total_chunks += 1

            # Commit por batches
            if len(ids) >= BATCH_SIZE:
                collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
                ids, embeddings, documents, metadatas = [], [], [], []

    # Commit del resto
    if ids:
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    return total_chunks


def index_folder(collection, folder_rel: str):
    """Indexa todos los PDFs de una carpeta (y subcarpetas)."""
    folder_abs = BIBLIOTECA / folder_rel
    if not folder_abs.exists():
        print(f"✗ Carpeta no encontrada: {folder_abs}")
        return

    pdfs = sorted(folder_abs.rglob("*.pdf"))
    if not pdfs:
        print(f"✗ Sin PDFs en: {folder_rel}")
        return

    # El sistema es la parte raíz del rel_path (ej. "Dungeons & Dragons")
    system = folder_rel.split("/")[0] if "/" in folder_rel else folder_rel
    game_line = folder_to_game_line(folder_rel)

    print(f"\n📂 {folder_rel} ({len(pdfs)} PDFs)")
    total = 0
    for i, pdf in enumerate(pdfs, 1):
        rel = str(pdf.relative_to(BIBLIOTECA))
        print(f"  [{i}/{len(pdfs)}] {pdf.name} … ", end="", flush=True)
        t0 = time.time()
        chunks = index_pdf(collection, pdf, rel, system, game_line)
        elapsed = time.time() - t0
        if chunks:
            print(f"{chunks} chunks ({elapsed:.1f}s)")
        total += chunks
    print(f"  ✓ Total: {total} chunks nuevos en '{folder_rel}'")


# ── Indexado del grimorio markdown ─────────────────────────────────────────────

def index_grimoire(collection):
    """Indexa los archivos .md de /resources/ (monsters, spells, rules)."""
    type_dirs = {
        "monster": RESOURCES_DIR / "monsters",
        "spell":   RESOURCES_DIR / "spells",
        "rule":    RESOURCES_DIR / "rules",
    }

    total = 0
    for content_type, dir_path in type_dirs.items():
        if not dir_path.exists():
            continue
        md_files = sorted(dir_path.glob("*.md"))
        print(f"\n📖 Grimorio — {content_type}s ({len(md_files)} archivos)")
        for md_file in md_files:
            slug = md_file.stem
            # Comprobar si ya está indexado
            existing = collection.get(where={"$and": [{"slug": {"$eq": slug}}, {"type": {"$eq": content_type}}]}, limit=1)
            if existing["ids"]:
                print(f"  ↩ {slug} ya indexado")
                continue

            try:
                post = frontmatter.load(str(md_file))
                text = post.content.strip()
                name = post.metadata.get("name") or post.metadata.get("nombre") or slug
            except Exception:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
                name = slug

            if not text:
                continue

            chunks = chunk_text(text)
            ids, embeddings, documents, metadatas = [], [], [], []
            for chunk_idx, chunk in enumerate(chunks):
                doc_id = make_id(f"grimoire/{content_type}/{slug}", 0, chunk_idx)
                try:
                    emb = embed(chunk)
                except Exception as e:
                    print(f"  ✗ Error embedding {slug}: {e}")
                    continue
                ids.append(doc_id)
                embeddings.append(emb)
                documents.append(chunk)
                metadatas.append({
                    "source": f"grimoire/{content_type}/{slug}.md",
                    "type": content_type,
                    "slug": slug,
                    "name": name,
                    "system": "grimoire",
                    "page": 0,
                    "chunk_index": chunk_idx,
                })
                total += 1

            if ids:
                collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
                print(f"  ✓ {name}: {len(ids)} chunks")

    print(f"\n✓ Grimorio: {total} chunks nuevos")


# ── Listado ────────────────────────────────────────────────────────────────────

def list_indexed(client):
    """Muestra un resumen de lo que hay indexado en ChromaDB."""
    for col_name in [COLLECTION_PDFS, COLLECTION_GRIMOIRE]:
        try:
            col = client.get_collection(col_name)
            count = col.count()
            print(f"\n📚 Colección '{col_name}': {count} chunks")
            if count > 0:
                # Agrupar por source para mostrar qué PDFs hay
                all_meta = col.get(include=["metadatas"])["metadatas"]
                sources = {}
                for m in all_meta:
                    src = m.get("source", "?")
                    sources[src] = sources.get(src, 0) + 1
                for src, n in sorted(sources.items())[:30]:
                    print(f"  • {src} ({n} chunks)")
                if len(sources) > 30:
                    print(f"  … y {len(sources)-30} más")
        except Exception:
            print(f"\n📚 Colección '{col_name}': no existe aún")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Indexador RAG para PantallaDigitalMaster")
    parser.add_argument("--folder", metavar="CARPETA", help="Indexar una carpeta concreta de la biblioteca")
    parser.add_argument("--grimoire-only", action="store_true", help="Solo indexar el grimorio markdown")
    parser.add_argument("--list", action="store_true", help="Mostrar resumen de lo indexado")
    parser.add_argument("--all", action="store_true", help="Indexar todas las carpetas de config.py")
    parser.add_argument("--no-ocr", action="store_true", help="Desactivar OCR (más rápido, solo texto digital)")
    args = parser.parse_args()

    if args.no_ocr:
        global OCR_AVAILABLE
        OCR_AVAILABLE = False

    client = get_chroma_client()

    if args.list:
        list_indexed(client)
        return

    col_pdfs     = get_collection(client, COLLECTION_PDFS)
    col_grimoire = get_collection(client, COLLECTION_GRIMOIRE)

    if args.grimoire_only:
        index_grimoire(col_grimoire)
        return

    if args.folder:
        index_folder(col_pdfs, args.folder)
        index_grimoire(col_grimoire)
        return

    # Por defecto (--all o sin argumentos): carpetas de config.py
    print("🐉 Indexando carpetas configuradas en config.py…")
    for folder in Config.RAG_INDEX_FOLDERS:
        index_folder(col_pdfs, folder)
    index_grimoire(col_grimoire)
    print("\n✅ Indexado completo")


if __name__ == "__main__":
    main()
