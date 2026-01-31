import os
import frontmatter
import markdown


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

    return sorted(items, key=lambda x: (x.get("nombre") or "").lower())


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