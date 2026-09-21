"""
Document loader abstraction for multi-format document support.
Normalizes various document formats (PDF, Word, ODT, Images) to PIL Image lists.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import fitz
from PIL import Image


class DocumentLoader(ABC):
    """Abstract base class for document loaders."""
    
    @abstractmethod
    def supports(self, file_path: str | Path) -> bool:
        """Check if this loader can handle the given file."""
    
    @abstractmethod
    def load(self, file_path: str | Path) -> list[Image.Image]:
        """Load document and return list of PIL Image objects (one per page).
        
        Raises:
            ValueError: If file cannot be loaded or format is invalid.
        """


class PDFLoader(DocumentLoader):
    """Load PDF documents via PyMuPDF."""
    
    SUPPORTED_EXTENSIONS = {'.pdf'}
    
    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def load(self, file_path: str | Path, password: str = "") -> list[Image.Image]:
        """Load PDF and render all pages to images at 300 DPI."""
        file_path = str(file_path)
        zoom = 300 / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages: list[Image.Image] = []
        
        with fitz.open(file_path) as doc:
            # Handle encrypted PDFs
            if doc.is_encrypted:
                if not doc.authenticate(password):
                    raise ValueError("PDF is encrypted and password is incorrect or missing")
            
            if len(doc) == 0:
                raise ValueError("PDF has no pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages.append(img)
        
        return pages


class ImageLoader(DocumentLoader):
    """Load image documents via Pillow."""
    
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.ico', '.tiff', '.tif'}
    
    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def load(self, file_path: str | Path) -> list[Image.Image]:
        """Load image(s) and return as list of PIL Images.
        
        For single-page formats: returns [image]
        For multi-page formats (TIFF): returns [page0, page1, ...]
        """
        file_path = str(file_path)
        pages: list[Image.Image] = []
        
        with Image.open(file_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Check if image has multiple frames (e.g., animated GIF, multi-frame TIFF)
            try:
                # Try to iterate through frames
                while True:
                    pages.append(img.copy().convert('RGB'))
                    img.seek(len(pages))
            except EOFError:
                # No more frames
                pass
            except AttributeError:
                # Image doesn't support seeking, just add the single image
                if not pages:
                    pages.append(img.convert('RGB'))
        
        if not pages:
            raise ValueError(f"Could not load any images from {file_path}")
        
        return pages


class LibreOfficeLoader(DocumentLoader):
    """Load Word and ODT documents via LibreOffice conversion."""
    
    SUPPORTED_EXTENSIONS = {'.docx', '.doc', '.odt'}
    
    def __init__(self, libreoffice_path: str | None = None):
        """Initialize with optional LibreOffice path."""
        self.libreoffice_path = libreoffice_path
    
    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def load(self, file_path: str | Path) -> list[Image.Image]:
        """Convert document to PDF via LibreOffice, then render pages."""
        import subprocess
        import tempfile
        
        file_path = str(file_path)
        
        # Determine LibreOffice executable path
        lo_exe = self._find_libreoffice()
        if not lo_exe:
            raise ValueError(
                "LibreOffice is required to open Word and ODT documents. "
                "Please install LibreOffice or configure the path in settings."
            )
        
        # Create temporary directory for conversion
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert to PDF
            try:
                subprocess.run(
                    [lo_exe, "--headless", "--convert-to", "pdf", "--outdir", temp_dir, file_path],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
            except subprocess.CalledProcessError as e:
                raise ValueError(f"Failed to convert {file_path}: {e.stderr.decode()}")
            except subprocess.TimeoutExpired:
                raise ValueError(
                    f"Converting {file_path} to PDF via LibreOffice timed out after 30 seconds. "
                    "The document may be too large or LibreOffice may be unresponsive; "
                    "try again or convert it to PDF manually first."
                )
            except FileNotFoundError:
                raise ValueError(f"LibreOffice executable not found at {lo_exe}")
            
            # Find converted PDF
            base_name = Path(file_path).stem
            pdf_path = Path(temp_dir) / f"{base_name}.pdf"
            
            if not pdf_path.exists():
                raise ValueError("Failed to convert document to PDF")
            
            # Load PDF using PDFLoader
            pdf_loader = PDFLoader()
            return pdf_loader.load(str(pdf_path))
    
    def _find_libreoffice(self) -> str | None:
        """Find LibreOffice executable on system."""
        import os
        import shutil
        import sys
        
        # If path was explicitly set, use it
        if self.libreoffice_path:
            lo_exe = self._construct_executable_path(self.libreoffice_path)
            if os.path.exists(lo_exe):
                return lo_exe
        
        # Platform-specific paths
        if sys.platform == "win32":
            # Windows paths
            windows_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                r"C:\Program Files\LibreOffice\soffice.exe",
            ]
            for path in windows_paths:
                if os.path.exists(path):
                    return path
        elif sys.platform == "darwin":
            # macOS paths
            macos_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                "/opt/homebrew/opt/libreoffice/bin/soffice",  # Homebrew ARM64
                "/usr/local/opt/libreoffice/bin/soffice",      # Homebrew Intel
            ]
            for path in macos_paths:
                if os.path.exists(path):
                    return path
        
        # Try system PATH (works on all platforms)
        lo_exe = shutil.which("soffice")
        if lo_exe:
            return lo_exe
        
        return None
    
    @staticmethod
    def _construct_executable_path(base_path: str) -> str:
        """Construct full path to soffice executable from LibreOffice installation path."""
        import os
        
        # If path already points to an executable, return it directly
        if base_path.endswith("soffice.exe") or base_path.endswith("soffice"):
            return base_path
        
        # On Windows, try program/soffice.exe first, then soffice.exe
        if os.name == 'nt':  # Windows
            candidates = [
                os.path.join(base_path, "program", "soffice.exe"),
                os.path.join(base_path, "soffice.exe"),
            ]
        else:  # Linux/Mac
            candidates = [
                os.path.join(base_path, "soffice"),
                os.path.join(base_path, "bin", "soffice"),
            ]
        
        for path in candidates:
            if os.path.exists(path):
                return path
        
        # Default to first candidate
        return candidates[0]


class DocumentLoaderRegistry:
    """Registry for document loaders with format detection."""
    
    def __init__(self, libreoffice_path: str | None = None):
        """Initialize registry with loaders."""
        self.loaders = [
            PDFLoader(),
            LibreOfficeLoader(libreoffice_path),
            ImageLoader(),
        ]
    
    def set_libreoffice_path(self, path: str | None):
        """Update LibreOffice path for LibreOfficeLoader."""
        for loader in self.loaders:
            if isinstance(loader, LibreOfficeLoader):
                loader.libreoffice_path = path
                break
    
    def load(self, file_path: str | Path, password: str = "") -> list[Image.Image]:
        """Load document using appropriate loader."""
        file_path = str(file_path)
        
        # Find matching loader
        for loader in self.loaders:
            if loader.supports(file_path):
                if isinstance(loader, PDFLoader):
                    return loader.load(file_path, password)
                return loader.load(file_path)
        
        # No loader found
        ext = Path(file_path).suffix.lower()
        raise ValueError(
            f"File format '{ext}' is not supported. "
            "Please choose a PDF, Word document, ODT, or image file."
        )
    
    def get_supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        extensions = set()
        for loader in self.loaders:
            if hasattr(loader, 'SUPPORTED_EXTENSIONS'):
                extensions.update(loader.SUPPORTED_EXTENSIONS)
        return extensions
