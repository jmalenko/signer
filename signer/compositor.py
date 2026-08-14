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

    @staticmethod
    def from_filter_string(filter_string: str) -> "ExportFormat":
        """Extract format from a Qt file dialog filter string.
        
        Args:
            filter_string: Filter string like "JPEG files (*.jpg *.jpeg)" or "PDF files (*.pdf)"
        
        Returns:
            Detected ExportFormat, defaults to JPG if not recognized
        """
        filter_lower = filter_string.lower()
        if "jpeg" in filter_lower or "jpg" in filter_lower:
            return ExportFormat.JPG
        elif "png" in filter_lower:
            return ExportFormat.PNG
        elif "pdf" in filter_lower:
            return ExportFormat.PDF
        elif "tiff" in filter_lower or "tif" in filter_lower:
            return ExportFormat.TIFF
        elif "bmp" in filter_lower:
            return ExportFormat.BMP
        return ExportFormat.JPG

    def is_single_file_format(self) -> bool:
        """Check if this format stores all pages in a single file."""
        return self in (ExportFormat.PDF, ExportFormat.TIFF)

    def is_per_file_format(self) -> bool:
        """Check if this format stores each page in a separate file."""
        return self in (ExportFormat.JPG, ExportFormat.PNG, ExportFormat.BMP)


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
    return f"{base}-p#{ext}"


def replace_placeholder_with_page_number(
    filename: str,
    page_index: int,
    total_pages: int,
) -> str:
    """
    Replace '#' placeholder with zero-padded page number.
    
    Example: "document-p#.jpg" → "document-p01.jpg" (for 98-page doc, page 0)
    """
    if "#" not in filename:
        return filename
    
    pad_width = len(str(total_pages))
    page_num = f"{page_index + 1:0{pad_width}d}"
    return filename.replace("#", page_num)


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
    if "#" not in filename_stem:
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
    base_filename = filename_stem.replace("#", "")
    
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
    if export_format.is_single_file_format() and existing_files:
        if len(existing_files) == 1:
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
