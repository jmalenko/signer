from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image


def render_first_page_to_image(pdf_path: str | Path, dpi: int = 300) -> Image.Image:
    pdf_path = str(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(pdf_path) as doc:
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
