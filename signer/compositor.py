from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from PIL import Image

from .objects import CanvasObject

logger = logging.getLogger(__name__)

# Placeholder character replaced with the page number in multi-page per-file exports.
MULTIPAGE_PLACEHOLDER = "#"

# Default lossy-compression quality (1-100) used when the caller doesn't override it.
DEFAULT_JPG_QUALITY = 95
DEFAULT_PDF_QUALITY = 95


class ExportFormat(Enum):
    """Supported export formats."""
    JPG = "jpg"
    PNG = "png"
    PDF = "pdf"
    TIFF = "tiff"
    BMP = "bmp"

    def extension(self) -> str:
        """Get file extension for this format."""
        return _FORMAT_METADATA[self]["extension"]

    def file_filter(self) -> str:
        """Get Qt file dialog filter for this format."""
        return _FORMAT_METADATA[self]["filter"]

    @staticmethod
    def from_extension(ext: str) -> ExportFormat:
        """Detect format from file extension."""
        ext = ext.lower()
        for export_format, metadata in _FORMAT_METADATA.items():
            if ext in metadata["extensions"]:
                return export_format
        return ExportFormat.JPG

    @staticmethod
    def all_formats_filter() -> str:
        """Get Qt file dialog filter for all supported formats."""
        all_extensions = " ".join(
            extension
            for metadata in _FORMAT_METADATA.values()
            for extension in sorted(metadata["extensions"])
        )
        filters = ";;".join(metadata["filter"] for metadata in _FORMAT_METADATA.values())
        return f"Supported Files ({all_extensions});;{filters}"

    @staticmethod
    def from_filter_string(filter_string: str) -> ExportFormat:
        """Extract format from a Qt file dialog filter string.
        
        Args:
            filter_string: Filter string like "JPEG files (*.jpg *.jpeg)" or "PDF files (*.pdf)"
        
        Returns:
            Detected ExportFormat, defaults to JPG if not recognized
        """
        filter_lower = filter_string.lower()
        for export_format, metadata in _FORMAT_METADATA.items():
            if any(extension in filter_lower for extension in metadata["extensions"]):
                return export_format
        return ExportFormat.JPG

    def is_single_file_format(self) -> bool:
        """Check if this format stores all pages in a single file."""
        return _FORMAT_METADATA[self]["single_file"]

    def is_per_file_format(self) -> bool:
        """Check if this format stores each page in a separate file."""
        return not self.is_single_file_format()


_FORMAT_METADATA = {
    ExportFormat.JPG: {
        "extension": ".jpg",
        "extensions": {".jpg", ".jpeg"},
        "filter": "JPEG files (*.jpg *.jpeg)",
        "single_file": False,
    },
    ExportFormat.PNG: {
        "extension": ".png",
        "extensions": {".png"},
        "filter": "PNG files (*.png)",
        "single_file": False,
    },
    ExportFormat.PDF: {
        "extension": ".pdf",
        "extensions": {".pdf"},
        "filter": "PDF files (*.pdf)",
        "single_file": True,
    },
    ExportFormat.TIFF: {
        "extension": ".tif",
        "extensions": {".tif", ".tiff"},
        "filter": "TIFF files (*.tif *.tiff)",
        "single_file": True,
    },
    ExportFormat.BMP: {
        "extension": ".bmp",
        "extensions": {".bmp"},
        "filter": "BMP files (*.bmp)",
        "single_file": False,
    },
}


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


def build_suggested_filename_for_dialog(
    document_path: str | Path,
    total_pages: int,
    export_format: ExportFormat = ExportFormat.JPG,
) -> str:
    """
    Build suggested filename for Save As dialog with dynamic placeholder.
    
    Rules:
    1. Single-page document → single filename (no placeholder)
    2. Multi-page capable format (PDF/TIFF) → single filename (no placeholder)
    3. Multi-page per-file format (JPG/PNG/BMP) → use placeholder format
    """
    doc = Path(document_path)
    ext = export_format.extension()
    base = f"{doc.stem}-signed"
    
    # Rule 1: Single-page document
    if total_pages <= 1:
        return f"{base}{ext}"
    
    # Rule 2: Single-file format
    if export_format.is_single_file_format():
        return f"{base}{ext}"
    
    # Rule 3: Multi-page per-file format
    return f"{base}-p{MULTIPAGE_PLACEHOLDER}{ext}"


def replace_placeholder_with_page_number(
    filename: str,
    page_index: int,
    total_pages: int,
) -> str:
    """
    Replace '#' placeholder with zero-padded page number.
    
    Example: "document-p#.jpg" → "document-p01.jpg" (for 98-page doc, page 0)
    """
    if MULTIPAGE_PLACEHOLDER not in filename:
        return filename
    
    pad_width = len(str(total_pages))
    page_num = f"{page_index + 1:0{pad_width}d}"
    return filename.replace(MULTIPAGE_PLACEHOLDER, page_num)


def validate_placeholder_for_multipage_export(
    filename_stem: str,
    total_pages: int,
    export_format: ExportFormat,
) -> tuple[bool, str]:
    """
    Validate that placeholder exists when required for multi-page per-file export.
    
    Returns: (is_valid, error_message)
    """
    # Single-file formats don't need placeholder
    if export_format.is_single_file_format():
        return True, ""
    
    # Single-page documents don't need placeholder
    if total_pages <= 1:
        return True, ""
    
    # Multi-page per-file format MUST have placeholder
    if MULTIPAGE_PLACEHOLDER not in filename_stem:
        return False, (
            "File format cannot store multiple pages in one file. "
            "Each page will be in a separate file. "
            "You must use the # placeholder for the page number in the file name.\n\n"
            f"Example: {filename_stem}-p#"
        )
    
    return True, ""


def detect_existing_files(
    output_path: Path,
    total_pages: int,
    export_format: ExportFormat,
    filename_stem: str = "",
) -> list[Path]:
    """
    Detect which files would be overwritten by the export.
    
    Args:
        output_path: The target file path (for single-file formats)
        total_pages: Number of pages being exported
        export_format: The export format
        filename_stem: Base filename without extension (for multi-page formats, may contain # placeholder)
    
    Returns:
        List of existing files that would be overwritten
    """
    existing = []
    directory = output_path.parent
    
    if export_format.is_single_file_format():
        # PDF, TIFF: single file
        if output_path.exists():
            existing.append(output_path)
    else:
        # JPG, PNG, BMP: per-page files
        # Use the same placeholder-replacement logic as the actual export
        for idx in range(total_pages):
            # Replace placeholder with actual page number (same logic as export)
            actual_filename = replace_placeholder_with_page_number(filename_stem, idx, total_pages)
            filename = f"{actual_filename}{export_format.extension()}"
            file_path = directory / filename
            if file_path.exists():
                existing.append(file_path)
    
    return existing


def detect_older_page_files(
    directory: Path,
    filename_stem: str,
    total_pages: int,
    export_format: ExportFormat,
) -> list[Path]:
    """
    Detect "older" page files that extend beyond the new export range.
    
    Example: Exporting 20 pages when 50 previous pages exist, finds pages 21-50.
    
    Args:
        directory: Directory to search
        filename_stem: Base filename without extension (may contain # placeholder)
        total_pages: Number of pages being exported
        export_format: The export format
    
    Returns:
        List of files with page numbers > total_pages (sorted alphabetically)
    """
    if export_format.is_single_file_format():
        # Single-file formats don't have older files
        return []
    
    older_files = []
    ext = export_format.extension()
    
    # Remove placeholder from filename_stem to get the actual base name
    base_filename = filename_stem.replace(MULTIPAGE_PLACEHOLDER, "")
    
    # Build a glob pattern to find all page files
    # Since base_filename already has the suffix pattern (e.g., "doc-p" from "doc-p#")
    # we just look for files matching base_filename + digits + extension
    pad_width = len(str(total_pages))
    
    for file_path in directory.glob(f"{base_filename}[0-9]*{ext}"):
        # Extract page number from filename
        # Example: "doc-p042.jpg" → extract "42"
        try:
            # Get the part between base_filename and the extension
            name_without_ext = file_path.stem  # "doc-p042"
            if name_without_ext.startswith(base_filename):
                page_str = name_without_ext[len(base_filename):]  # "042"
                page_num = int(page_str)
                
                # If page number is beyond our export range, it's an "older" file
                if page_num > total_pages:
                    older_files.append(file_path)
        except (ValueError, IndexError):
            # Skip files that don't match the pattern
            continue
    
    return sorted(older_files)


def build_overwrite_dialog_info(
    existing_files: list[Path],
    older_files: list[Path],
    total_pages: int,
    export_format: ExportFormat,
    output_path: Path,
) -> tuple[str, str, bool]:
    """
    Build dialog info (title, message, show_cleanup_checkbox) based on overwrite scenario.
    
    Returns: (dialog_title, message, show_cleanup_checkbox)
    """
    show_cleanup_checkbox = False
    
    if not existing_files and not older_files:
        # No overwrite needed
        return "", "", False
    
    # Scenario A: Single file
    if export_format.is_single_file_format() and existing_files and len(existing_files) == 1:
        title = "File Already Exists"
        filename = existing_files[0].name
        message = f"The file '{filename}' already exists.\n\nDo you want to replace it?"
        return title, message, False
    
    # Scenario E: Older files detected (multi-page export)
    if older_files and existing_files and export_format.is_per_file_format():
        title = "Replace Files and Clean Up Old Pages?"
        
        # Build existing files list
        existing_names = [f.name for f in sorted(existing_files)]
        files_text = "\n".join(f"• {name}" for name in existing_names[:3])
        if len(existing_names) > 3:
            files_text += f"\n• ... ({len(existing_names) - 3} more files)"
        
        # Build older files list
        older_names = [f.name for f in sorted(older_files)]
        older_text = "\n".join(f"• {name}" for name in older_names[:3])
        if len(older_names) > 3:
            older_text += f"\n• ... ({len(older_names) - 3} more files)"
        
        message = (
            "These files will be overwritten:\n\n"
            f"{files_text}\n\n"
            "And these older page files can be deleted:\n\n"
            f"{older_text}"
        )
        return title, message, True
    
    # Scenario B/C/D: Multi-page existing files (without older files)
    if existing_files and export_format.is_per_file_format():
        existing_names = [f.name for f in sorted(existing_files)]
        
        # Scenario C: All files will be overwritten
        if len(existing_names) == total_pages:
            title = "All Files Will Be Overwritten"
            message = (
                f"All {total_pages} pages of '{output_path.stem}.{export_format.extension()}' "
                f"will be overwritten.\n\nDo you want to replace them?"
            )
            return title, message, False
        
        # Scenario B or D: Some/many files exist
        if len(existing_names) <= 10:
            # Scenario B: List all files
            title = "Some Files Already Exist"
            files_text = "\n".join(f"• {name}" for name in existing_names)
            message = (
                "The following files will be overwritten:\n\n"
                f"{files_text}\n\n"
                "Do you want to replace them?"
            )
        else:
            # Scenario D: Large number (>10) - show summary
            title = "Files Already Exist"
            files_text = "\n".join(f"• {name}" for name in existing_names[:3])
            message = (
                f"{len(existing_names)} file(s) will be overwritten:\n\n"
                f"{files_text}\n"
                f"• ... ({len(existing_names) - 3} more files)\n\n"
                "Do you want to replace them?"
            )
        
        return title, message, False
    
    # Default (shouldn't reach here)
    return "Overwrite Files", "Do you want to overwrite the existing files?", False


def _composite_objects(
    base: Image.Image,
    objects: list[CanvasObject],
) -> None:
    """Composite all objects over the base RGBA image using alpha_composite.

    Each object's render is clamped to the image bounds before compositing.
    Render failures are silently skipped (matching the per-format behavior).
    """
    pw, ph = base.size
    for obj in objects:
        try:
            if hasattr(obj, "render_for_compositing"):
                overlay, overlay_x, overlay_y = obj.render_for_compositing()
            else:
                overlay = obj.render_to_pil().convert("RGBA")
                overlay_x, overlay_y = obj.x, obj.y
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning("Could not render annotation during compositing: %s", exc)
            continue
        x = round(overlay_x)
        y = round(overlay_y)
        right = x + overlay.width
        bottom = y + overlay.height
        clip_left = max(0, x)
        clip_top = max(0, y)
        clip_right = min(pw, right)
        clip_bottom = min(ph, bottom)
        if clip_left >= clip_right or clip_top >= clip_bottom:
            continue
        crop = overlay.crop((clip_left - x, clip_top - y, clip_right - x, clip_bottom - y))
        base.alpha_composite(crop, dest=(clip_left, clip_top))


def composite_objects_to_jpg(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
    jpg_quality: int = DEFAULT_JPG_QUALITY,
) -> None:
    """Composite all objects over the page image and save as JPEG.
    """
    base = page_image.convert("RGBA")
    _composite_objects(base, objects)
    base.convert("RGB").save(str(output_path), format="JPEG", quality=jpg_quality, optimize=True)


def composite_objects_to_png(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
) -> None:
    """Composite all objects over the page image and save as PNG with maximum compression."""
    base = page_image.convert("RGBA")
    _composite_objects(base, objects)

    # Use compress_level=9 for maximum lossless compression
    base.save(str(output_path), format="PNG", optimize=True, compress_level=9)


def composite_objects_to_bmp(
    page_image: Image.Image,
    objects: list[CanvasObject],
    output_path: str | Path,
) -> None:
    """Composite all objects over the page image and save as BMP."""
    base = page_image.convert("RGBA")
    _composite_objects(base, objects)

    base.convert("RGB").save(str(output_path), format="BMP")


def composite_pages_to_pdf(
    page_images: list[Image.Image],
    page_objects: list[list[CanvasObject]],
    output_path: str | Path,
    pdf_quality: int = DEFAULT_PDF_QUALITY,
) -> None:
    """Composite objects over pages and save as PDF (raster images).
    
    Args:
        page_images: List of PIL Image objects for each page
        page_objects: List of object lists for each page
        output_path: Path to save the PDF
        pdf_quality: Image quality for PDF (1-100, default 95)
    """
    composited_images = []
    
    for page_image, objects in zip(page_images, page_objects):
        base = page_image.convert("RGBA")
        _composite_objects(base, objects)
        composited_images.append(base.convert("RGB"))
    
    if composited_images:
        composited_images[0].save(
            str(output_path),
            format="PDF",
            save_all=True,
            append_images=composited_images[1:] if len(composited_images) > 1 else [],
            quality=pdf_quality,
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
        _composite_objects(base, objects)
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
    jpg_quality: int = DEFAULT_JPG_QUALITY,
) -> None:
    """Composite objects to specified format. For single-page export.
    
    Args:
        page_image: PIL Image object for the page
        objects: List of objects to composite
        output_path: Path to save the file
        export_format: Format to export as
        jpg_quality: Quality for JPG format (1-100, default 95)
    """
    if export_format == ExportFormat.JPG:
        composite_objects_to_jpg(page_image, objects, output_path, jpg_quality)
    elif export_format == ExportFormat.PNG:
        composite_objects_to_png(page_image, objects, output_path)
    elif export_format == ExportFormat.BMP:
        composite_objects_to_bmp(page_image, objects, output_path)
    else:
        # Default to JPG for unknown formats
        composite_objects_to_jpg(page_image, objects, output_path, jpg_quality)
