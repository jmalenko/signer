from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image


def render_all_pages(pdf_path: str | Path, dpi: int = 300) -> list[Image.Image]:
    """Render every page of a PDF to PIL RGB images at the given DPI."""
    pdf_path = str(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pages: list[Image.Image] = []
    with fitz.open(pdf_path) as doc:
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pages.append(img)
    return pages
