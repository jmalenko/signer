"""Unit tests for encrypted PDF functionality."""

from pathlib import Path

import pytest

from signer.pdf_utils import render_all_pages


class TestEncryptedPDF:
    """Tests for encrypted PDF handling."""

    @pytest.fixture
    def examples_dir(self):
        """Get the examples directory."""
        return Path(__file__).parent.parent.parent / "examples"

    def test_unencrypted_pdf_opens_without_password(self, examples_dir):
        """Unencrypted PDFs should open normally without a password."""
        pdf = examples_dir / "document.pdf"
        pages = render_all_pages(pdf)
        assert len(pages) > 0
        assert pages[0].size[0] > 0
        assert pages[0].size[1] > 0

    def test_unencrypted_pdf_opens_with_empty_password(self, examples_dir):
        """Unencrypted PDFs should open with an empty password string."""
        pdf = examples_dir / "document.pdf"
        pages = render_all_pages(pdf, password="")
        assert len(pages) > 0

    def test_encrypted_pdf_fails_without_password(self, examples_dir):
        """Encrypted PDFs should fail to open without a password."""
        encrypted_pdf = examples_dir / "document-encrypted.pdf"
        with pytest.raises(ValueError, match="encrypted"):
            render_all_pages(encrypted_pdf, password="")

    def test_encrypted_pdf_opens_with_correct_password(self, examples_dir):
        """Encrypted PDFs should open with the correct password."""
        encrypted_pdf = examples_dir / "document-encrypted.pdf"
        pages = render_all_pages(encrypted_pdf, password="key123")
        assert len(pages) > 0
        assert pages[0].size[0] > 0
        assert pages[0].size[1] > 0

    def test_encrypted_pdf_fails_with_wrong_password(self, examples_dir):
        """Encrypted PDFs should fail with an incorrect password."""
        encrypted_pdf = examples_dir / "document-encrypted.pdf"
        with pytest.raises(ValueError, match="encrypted|incorrect"):
            render_all_pages(encrypted_pdf, password="wrongpassword")

    def test_encrypted_pdf_has_same_content_as_unencrypted(self, examples_dir):
        """Encrypted and unencrypted versions should have same number of pages."""
        pdf = examples_dir / "document.pdf"
        encrypted_pdf = examples_dir / "document-encrypted.pdf"
        
        pages_unencrypted = render_all_pages(pdf)
        pages_encrypted = render_all_pages(encrypted_pdf, password="key123")
        
        assert len(pages_unencrypted) == len(pages_encrypted)
        # Verify they have the same dimensions
        for unenc, enc in zip(pages_unencrypted, pages_encrypted):
            assert unenc.size == enc.size
