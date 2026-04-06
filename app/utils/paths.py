from __future__ import annotations

from pathlib import Path


def safe_resolve(base: Path, relative: str) -> Path:
    """Resolve *relative* under *base*, rejecting any traversal outside it."""
    resolved = (base / relative).resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(f"Path traversal detected: {relative!r} escapes {base_resolved}")
    return resolved


def is_text_file(path: Path, sample_bytes: int = 8192) -> bool:
    """Heuristic: file is text if the first *sample_bytes* contain no null bytes."""
    try:
        chunk = path.read_bytes()[:sample_bytes]
        return b"\x00" not in chunk
    except OSError:
        return False


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS
