from __future__ import annotations

from enum import Enum
from pathlib import Path

from PIL import Image

from .objects import CanvasObject


class ExportFormat(Enum):
    """Supported export formats."""
    JPG = "jpg"
    PNG = "png"
    PDF = "pdf"
    TIFF = "tiff"
    BMP = "bmp"

    def extension(self) -> str:
        """Get file extension for this format."""
        if self == ExportFormat.JPG:
            return ".jpg"
        elif self == ExportFormat.PNG:
            return ".png"
        elif self == ExportFormat.PDF:
            return ".pdf"
        elif self == ExportFormat.TIFF:
            return ".tif"
        elif self == ExportFormat.BMP:
            return ".bmp"
        return ".jpg"

    def file_filter(self) -> str:
        """Get Qt file dialog filter for this format."""
        if self == ExportFormat.JPG:
            return "JPEG files (*.jpg *.jpeg)"
        elif self == ExportFormat.PNG:
            return "PNG files (*.png)"
        elif self == ExportFormat.PDF:
            return "PDF files (*.pdf)"
        elif self == ExportFormat.TIFF:
            return "TIFF files (*.tif *.tiff)"
        elif self == ExportFormat.BMP:
            return "BMP files (*.bmp)"
        return "JPEG files (*.jpg *.jpeg)"

    @staticmethod
    def from_extension(ext: str) -> "ExportFormat":
        """Detect format from file extension."""
        ext = ext.lower()
        if ext in {".jpg", ".jpeg"}:
            return ExportFormat.JPG
        elif ext == ".png":
            return ExportFormat.PNG
        elif ext == ".pdf":
            return ExportFormat.PDF
        elif ext in {".tif", ".tiff"}:
            return ExportFormat.TIFF
        elif ext == ".bmp":
            return ExportFormat.BMP
        return ExportFormat.JPG

    @staticmethod
    def all_formats_filter() -> str:
        """Get Qt file dialog filter for all supported formats."""
        return "Supported Files (*.jpg *.jpeg *.png *.pdf *.tif *.tiff *.bmp);;JPEG files (*.jpg *.jpeg);;PNG files (*.png);;PDF files (*.pdf);;TIFF files (*.tif *.tiff);;BMP files (*.bmp)"


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
    export_format: ExportFormat = ExportFormat.JPG,
) -> Path:
    doc = Path(document_path)
    directory = Path(preferred_directory) if preferred_directory else doc.parent
    ext = export_format.extension()
    
    if total_pages <= 1:
        base = f"{doc.stem}-signed"
        candidate = directory / f"{base}{ext}"
        if not candidate.exists():
            return candidate
        i = 1
        while True:
            candidate = directory / f"{base}-{i}{ext}"
            if not candidate.exists():
                return candidate
            i += 1
    else:
        base = f"{doc.stem}-signed{_page_suffix(page_index, total_pages)}"
        return directory / f"{base}{ext}"


def build_page_output_path(
    base_stem: str,
    page_index: int,
    total_pages: int,
    directory: str | Path,
    export_format: ExportFormat = ExportFormat.JPG,
) -> Path:
    directory = Path(directory)
    ext = export_format.extension()
    return directory / f"{base_stem}{_page_suffix(page_index, total_pages)}{ext}"


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


def composite_objects_to_png(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
) -> None:
    """Composite all objects over the page image and save as PNG."""
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

    base.save(str(output_path), format="PNG", optimize=True)


def composite_objects_to_bmp(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
) -> None:
    """Composite all objects over the page image and save as BMP."""
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

    base.convert("RGB").save(str(output_path), format="BMP")


def composite_pages_to_pdf(
    page_images: list[Image.Image],
    page_objects: list[list[CanvasObject]],
    output_path: str | Path,
) -> None:
    """Composite objects over pages and save as PDF (raster images)."""
    composited_images = []
    
    for page_image, objects in zip(page_images, page_objects):
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

        composited_images.append(base.convert("RGB"))
    
    if composited_images:
        composited_images[0].save(
            str(output_path),
            format="PDF",
            save_all=True,
            append_images=composited_images[1:] if len(composited_images) > 1 else []
        )


def composite_pages_to_tiff(
    page_images: list[Image.Image],
    page_objects: list[list[CanvasObject]],
    output_path: str | Path,
) -> None:
    """Composite objects over pages and save as compressed TIFF (multi-page)."""
    composited_images = []
    
    for page_image, objects in zip(page_images, page_objects):
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

        composited_images.append(base.convert("RGB"))
    
    if composited_images:
        composited_images[0].save(
            str(output_path),
            format="TIFF",
            compression="lzw",
            save_all=True,
            append_images=composited_images[1:] if len(composited_images) > 1 else []
        )


def composite_objects_to_format(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
    export_format: ExportFormat,
) -> None:
    """Composite objects to specified format. For single-page export."""
    if export_format == ExportFormat.JPG:
        composite_objects_to_jpg(page_image, objects, output_path)
    elif export_format == ExportFormat.PNG:
        composite_objects_to_png(page_image, objects, output_path)
    elif export_format == ExportFormat.BMP:
        composite_objects_to_bmp(page_image, objects, output_path)
    else:
        # Default to JPG for unknown formats
        composite_objects_to_jpg(page_image, objects, output_path)
