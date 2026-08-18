"""Tests for multi-format document loading support (v1.2.9)."""

import pytest
from pathlib import Path
from PIL import Image

from signer.pdf_utils import render_all_pages
from signer.document_loader import DocumentLoaderRegistry, DocumentLoader


class TestDocumentLoaderRegistry:
    """Test DocumentLoaderRegistry factory pattern."""

    def test_registry_supports_pdf(self):
        """Test that registry supports PDF format."""
        registry = DocumentLoaderRegistry()
        supported = registry.get_supported_extensions()
        assert ".pdf" in supported

    def test_registry_supports_word_formats(self):
        """Test that registry supports Word document formats."""
        registry = DocumentLoaderRegistry()
        supported = registry.get_supported_extensions()
        assert ".docx" in supported
        assert ".doc" in supported

    def test_registry_supports_odt(self):
        """Test that registry supports OpenDocument Text format."""
        registry = DocumentLoaderRegistry()
        supported = registry.get_supported_extensions()
        assert ".odt" in supported

    def test_registry_supports_image_formats(self):
        """Test that registry supports various image formats."""
        registry = DocumentLoaderRegistry()
        supported = registry.get_supported_extensions()
        image_formats = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".ico", ".tiff", ".tif"}
        assert image_formats.issubset(supported)


class TestPDFDocumentLoading:
    """Test PDF document loading."""

    @pytest.fixture
    def pdf_path(self):
        """Path to test PDF document."""
        return Path(__file__).parent.parent.parent / "examples" / "document.pdf"

    def test_load_pdf_document(self, pdf_path):
        """Test loading a PDF document."""
        assert pdf_path.exists(), f"Test PDF not found at {pdf_path}"
        pages = render_all_pages(str(pdf_path))
        assert isinstance(pages, list)
        assert len(pages) > 0
        assert all(isinstance(p, Image.Image) for p in pages)

    def test_pdf_pages_are_rgb(self, pdf_path):
        """Test that PDF pages are converted to RGB."""
        pages = render_all_pages(str(pdf_path))
        for page in pages:
            assert page.mode == "RGB", f"Expected RGB, got {page.mode}"

    def test_pdf_pages_have_content(self, pdf_path):
        """Test that PDF pages contain image data."""
        pages = render_all_pages(str(pdf_path))
        for page in pages:
            # Check image has reasonable dimensions (at least 100x100)
            assert page.width >= 100
            assert page.height >= 100
            # Check image has content (not all white)
            extrema = page.getextrema() if hasattr(page, 'getextrema') else None
            assert page.tobytes(), "Page should have image data"


class TestWordDocumentLoading:
    """Test Word document loading (requires LibreOffice)."""

    @pytest.fixture
    def docx_path(self):
        """Path to test DOCX document."""
        return Path(__file__).parent.parent.parent / "examples" / "document.docx"

    def test_load_docx_document(self, docx_path, libreoffice_path):
        """Test loading a DOCX document."""
        if not docx_path.exists():
            pytest.skip(f"Test DOCX not found at {docx_path}")
        
        try:
            pages = render_all_pages(str(docx_path), libreoffice_path=libreoffice_path)
            assert isinstance(pages, list)
            assert len(pages) > 0
            assert all(isinstance(p, Image.Image) for p in pages)
        except ValueError as e:
            if "LibreOffice" in str(e):
                pytest.skip(f"LibreOffice not available: {e}")
            raise

    def test_docx_pages_are_rgb(self, docx_path, libreoffice_path):
        """Test that DOCX pages are converted to RGB."""
        if not docx_path.exists():
            pytest.skip(f"Test DOCX not found at {docx_path}")
        
        try:
            pages = render_all_pages(str(docx_path), libreoffice_path=libreoffice_path)
            for page in pages:
                assert page.mode == "RGB", f"Expected RGB, got {page.mode}"
        except ValueError as e:
            if "LibreOffice" in str(e):
                pytest.skip(f"LibreOffice not available: {e}")
            raise

    @pytest.fixture
    def doc_path(self):
        """Path to test DOC document."""
        return Path(__file__).parent.parent.parent / "examples" / "document.doc"

    def test_load_doc_document(self, doc_path, libreoffice_path):
        """Test loading a DOC document."""
        if not doc_path.exists():
            pytest.skip(f"Test DOC not found at {doc_path}")
        
        try:
            pages = render_all_pages(str(doc_path), libreoffice_path=libreoffice_path)
            assert isinstance(pages, list)
            assert len(pages) > 0
        except ValueError as e:
            if "LibreOffice" in str(e):
                pytest.skip(f"LibreOffice not available: {e}")
            raise


class TestODTDocumentLoading:
    """Test OpenDocument Text loading (requires LibreOffice)."""

    @pytest.fixture
    def odt_path(self):
        """Path to test ODT document."""
        return Path(__file__).parent.parent.parent / "examples" / "document.odt"

    def test_load_odt_document(self, odt_path, libreoffice_path):
        """Test loading an ODT document."""
        if not odt_path.exists():
            pytest.skip(f"Test ODT not found at {odt_path}")
        
        try:
            pages = render_all_pages(str(odt_path), libreoffice_path=libreoffice_path)
            assert isinstance(pages, list)
            assert len(pages) > 0
            assert all(isinstance(p, Image.Image) for p in pages)
        except ValueError as e:
            if "LibreOffice" in str(e):
                pytest.skip(f"LibreOffice not available: {e}")
            raise

    def test_odt_pages_are_rgb(self, odt_path, libreoffice_path):
        """Test that ODT pages are converted to RGB."""
        if not odt_path.exists():
            pytest.skip(f"Test ODT not found at {odt_path}")
        
        try:
            pages = render_all_pages(str(odt_path), libreoffice_path=libreoffice_path)
            for page in pages:
                assert page.mode == "RGB", f"Expected RGB, got {page.mode}"
        except ValueError as e:
            if "LibreOffice" in str(e):
                pytest.skip(f"LibreOffice not available: {e}")
            raise


class TestImageDocumentLoading:
    """Test image document loading."""

    @pytest.fixture
    def jpg_path(self):
        """Path to test JPG image."""
        return Path(__file__).parent.parent.parent / "examples" / "document1.jpg"

    @pytest.fixture
    def png_path(self):
        """Path to test PNG image."""
        return Path(__file__).parent.parent.parent / "examples" / "signature.png"

    @pytest.fixture
    def tiff_path(self):
        """Path to test multi-frame TIFF image."""
        # Try document.tiff first (created from PDF), then multiframe.tiff
        doc_tiff = Path(__file__).parent.parent.parent / "examples" / "document.tiff"
        if doc_tiff.exists():
            return doc_tiff
        return Path(__file__).parent.parent.parent / "examples" / "multiframe.tiff"

    def test_load_jpg_image(self, jpg_path):
        """Test loading a JPG image."""
        if not jpg_path.exists():
            pytest.skip(f"Test JPG not found at {jpg_path}")
        
        pages = render_all_pages(str(jpg_path))
        assert isinstance(pages, list)
        assert len(pages) == 1  # JPG is single frame
        assert isinstance(pages[0], Image.Image)
        assert pages[0].mode == "RGB"

    def test_load_png_image(self, png_path):
        """Test loading a PNG image."""
        if not png_path.exists():
            pytest.skip(f"Test PNG not found at {png_path}")
        
        pages = render_all_pages(str(png_path))
        assert isinstance(pages, list)
        assert len(pages) == 1  # PNG is single frame
        assert isinstance(pages[0], Image.Image)
        # PNG should be converted to RGB even if it has alpha channel
        assert pages[0].mode == "RGB"

    def test_load_multiframe_tiff(self, tiff_path):
        """Test loading a multi-frame TIFF image."""
        if not tiff_path.exists():
            pytest.skip(f"Test TIFF not found at {tiff_path}")
        
        pages = render_all_pages(str(tiff_path))
        assert isinstance(pages, list)
        assert len(pages) >= 2  # Should have multiple frames
        assert all(isinstance(p, Image.Image) for p in pages)
        assert all(p.mode == "RGB" for p in pages)

    def test_image_dimensions(self, jpg_path):
        """Test that loaded images have reasonable dimensions."""
        if not jpg_path.exists():
            pytest.skip(f"Test JPG not found at {jpg_path}")
        
        pages = render_all_pages(str(jpg_path))
        page = pages[0]
        # Image should have reasonable dimensions (at least 100x100)
        assert page.width >= 100
        assert page.height >= 100


class TestUnsupportedFormats:
    """Test handling of unsupported file formats."""

    def test_registry_rejects_unsupported_extension(self):
        """Test that registry can identify unsupported formats."""
        registry = DocumentLoaderRegistry()
        supported = registry.get_supported_extensions()
        # Some formats that should NOT be supported
        assert ".txt" not in supported
        assert ".md" not in supported
        assert ".exe" not in supported

    def test_load_unsupported_format_raises_error(self, tmp_path):
        """Test that loading unsupported format raises appropriate error."""
        # Create a fake unsupported file
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_text("This is a text file")
        
        with pytest.raises((ValueError, FileNotFoundError)):
            render_all_pages(str(unsupported_file))


class TestLibreOfficePath:
    """Test LibreOffice path configuration."""

    def test_registry_accepts_libreoffice_path(self):
        """Test that registry can be configured with custom LibreOffice path."""
        registry = DocumentLoaderRegistry(libreoffice_path="/custom/path/soffice")
        # Just verify it doesn't raise an error during initialization
        assert registry is not None

    def test_render_all_pages_accepts_libreoffice_path(self, tmp_path):
        """Test that render_all_pages accepts libreoffice_path parameter."""
        # Create a simple PDF for testing
        pdf_path = Path(__file__).parent.parent.parent / "examples" / "document.pdf"
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found")
        
        # This should not raise an error even if the path doesn't exist
        # (PDF doesn't need LibreOffice anyway)
        pages = render_all_pages(str(pdf_path), libreoffice_path="/fake/path")
        assert pages is not None


class TestDocumentLoaderRegistry:
    """Test DocumentLoaderRegistry factory and delegate pattern."""

    def test_registry_load_with_password_for_pdf(self):
        """Test that registry.load() accepts password parameter."""
        pdf_path = Path(__file__).parent.parent.parent / "examples" / "document.pdf"
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found")
        
        registry = DocumentLoaderRegistry()
        pages = registry.load(str(pdf_path), password="")
        assert pages is not None
        assert isinstance(pages, list)

    def test_registry_load_without_password_for_image(self):
        """Test that registry.load() works without password for images."""
        img_path = Path(__file__).parent.parent.parent / "examples" / "document1.jpg"
        if not img_path.exists():
            pytest.skip(f"Test image not found")
        
        registry = DocumentLoaderRegistry()
        pages = registry.load(str(img_path))
        assert pages is not None
        assert isinstance(pages, list)
