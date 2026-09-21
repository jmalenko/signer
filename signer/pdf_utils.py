from __future__ import annotations

from pathlib import Path

from PIL import Image

from .document_loader import DocumentLoaderRegistry


def render_all_pages(
    document_path: str | Path,
    password: str = "",
    libreoffice_path: str | None = None
) -> list[Image.Image]:
    """Render every page of a document to PIL RGB images at 300 DPI.
    
    Supports PDF, Word (.docx, .doc), ODT, and image formats.
    
    Args:
        document_path: Path to the document file
        password: Password for encrypted PDFs (default empty string)
        libreoffice_path: Optional path to LibreOffice installation for Word/ODT conversion
        
    Returns:
        List of PIL Image objects, one per page
        
    Raises:
        ValueError: If the document cannot be loaded or format is unsupported
    """
    loader_registry = DocumentLoaderRegistry(libreoffice_path)
    
    # For PDFs with password
    if str(document_path).lower().endswith('.pdf'):
        return loader_registry.load(document_path, password)
    
    # For all other formats
    return loader_registry.load(document_path)
