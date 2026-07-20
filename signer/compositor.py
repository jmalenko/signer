from __future__ import annotations

from pathlib import Path

from PIL import Image

from .objects import CanvasObject


def _page_suffix(page_index: int, total_pages: int) -> str:
    if total_pages <= 1:
        return ""
    pad = len(str(total_pages))
    return f"-p{page_index + 1:0{pad}d}"


def build_default_output_path(
    document_path: str | Path,
    page_index: int,
    preferred_directory: str | None = None,
    total_pages: int = 1,
) -> Path:
    doc = Path(document_path)
    directory = Path(preferred_directory) if preferred_directory else doc.parent
    if total_pages <= 1:
        base = f"{doc.stem}-signed"
        candidate = directory / f"{base}.jpg"
        if not candidate.exists():
            return candidate
        i = 1
        while True:
            candidate = directory / f"{base}-{i}.jpg"
            if not candidate.exists():
                return candidate
            i += 1
    else:
        base = f"{doc.stem}-signed{_page_suffix(page_index, total_pages)}"
        return directory / f"{base}.jpg"


def build_page_output_path(
    base_stem: str,
    page_index: int,
    total_pages: int,
    directory: str | Path,
) -> Path:
    directory = Path(directory)
    return directory / f"{base_stem}{_page_suffix(page_index, total_pages)}.jpg"


def composite_objects_to_jpg(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
    jpg_quality: int = 95,
) -> None:
    """Composite all objects over the page image and save as JPEG."""
    base = page_image.convert("RGBA")
    pw, ph = base.size

    for obj in objects:
        try:
            overlay = obj.render_to_pil().convert("RGBA")
        except Exception:
            continue
        x = int(round(obj.x))
        y = int(round(obj.y))
        # Clamp destination to avoid out-of-bounds
        x = max(0, min(x, pw - 1))
        y = max(0, min(y, ph - 1))
        base.alpha_composite(overlay, dest=(x, y))

    base.convert("RGB").save(str(output_path), format="JPEG", quality=jpg_quality, optimize=True)
