from pathlib import Path


def load_markdown_files(root: str | Path) -> list[Path]:
    """
    Find all Markdown files under the knowledge directory.
    """
    root = Path(root)

    if not root.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {root}")

    return sorted(root.rglob("*.md"))