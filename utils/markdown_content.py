import os
import re
import frontmatter
import markdown


def parse_dg(dg_raw) -> int | None:
    """Extrae el número base de Dados de Golpe (HD) de un campo `dg` de AD&D2e.
    AD&D2e no tiene "nivel de desafío" como D&D 5e — el DG es el indicador
    tradicional de peligrosidad de un monstruo. El campo es texto libre y muy
    variado ("1d8", "3d4+3", "7+7", "1d8 / 1d8", "8,12,16", "-12-14"...); esta
    función se queda con el primer número de dados (o el primer entero si no
    hay notación de dados). Devuelve None si no se puede interpretar con
    confianza (texto no numérico, o un valor fuera de rango razonable, señal
    de erratas de OCR como "743" o "246")."""
    if not dg_raw:
        return None
    s = str(dg_raw).strip()
    s = s.lstrip("-—–").strip()  # el OCR a veces confunde un guion/raya inicial
    s = re.split(r"[/,]", s)[0].strip()  # quedarse con el primer valor si hay varios
    m = re.match(r"^(\d+)\s*d\s*\d+", s, re.IGNORECASE)
    if m:
        valor = int(m.group(1))
    else:
        m = re.match(r"^(\d+)", s)
        if not m:
            return None
        valor = int(m.group(1))
    if valor > 30:
        return None  # fuera de rango plausible para AD&D2e — probable errata de OCR
    return valor


def parse_px(px_raw) -> int | None:
    """Extrae el valor numérico base de Puntos de Experiencia (PX) que otorga
    un monstruo de AD&D2e. El campo es texto libre ("975", "10,000",
    "975 - 2000", "175 (Lugarteniente: 270, Jefe: 420...)", "Variable"); esta
    función se queda con el primer entero (usando la coma como separador de
    miles, no como lista de valores). Devuelve None si no hay ningún número."""
    if not px_raw:
        return None
    s = str(px_raw).strip().replace(",", "")
    m = re.match(r"^(\d+)", s)
    if not m:
        return None
    return int(m.group(1))


def load_markdown_content(dir_path: str) -> list[dict]:
    """
    Load markdown files from a directory and extract their metadata. Reads all .md files from the specified directory, parses their frontmatter,
    and extracts metadata. Normalizes metadata by ensuring a 'nombre' field exists, using 'title' as a fallback or the filename slug as a last resort.
    Args:
        dir_path (str): Path to the directory containing markdown files.
    Returns:
        list[dict]: A sorted list of metadata dictionaries extracted from markdown files, ordered alphabetically by 'nombre' field (case-insensitive).
                    Returns an empty list if the directory does not exist.
    """
    items: list[dict] = []

    if not os.path.exists(dir_path):
        return items

    for filename in os.listdir(dir_path):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(dir_path, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            metadata = dict(post.metadata or {})
            metadata["slug"] = filename.replace(".md", "")

            if "nombre" not in metadata and "title" in metadata:
                metadata["nombre"] = metadata["title"]
            if "nombre" not in metadata:
                metadata["nombre"] = metadata["slug"]

            items.append(metadata)

        except Exception as e:
            print(f"[markdown_content] Error leyendo {filename}: {e}")

    def _nombre_key(x):
        n = x.get("nombre") or ""
        if isinstance(n, list):
            n = n[0] if n else ""
        return str(n).lower()

    return sorted(items, key=_nombre_key)


def get_markdown_detail(dir_path: str, slug: str):
    """
    Load and parse a markdown file with frontmatter metadata. Reads a markdown file from the specified directory, extracts frontmatter metadata,
    converts the content to HTML, and returns both as a tuple.
    Args:
        dir_path (str): The directory path where the markdown file is located.
        slug (str): The filename (without .md extension) of the markdown file to load.
    Returns:
        tuple: A tuple containing:
            - dict: Dictionary of frontmatter metadata, or None if file not found or error occurs.
            - str: HTML-converted content of the markdown file, or None if file not found or error occurs.
    """
    filepath = os.path.join(dir_path, f"{slug}.md")

    if not os.path.exists(filepath):
        return None, None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        html = markdown.markdown(
            post.content,
            extensions=["tables"]
        )

        return dict(post.metadata or {}), html

    except Exception as e:
        print(f"[markdown_content] Error leyendo {slug}.md: {e}")
        return None, None