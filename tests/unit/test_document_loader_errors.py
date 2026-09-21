"""Error-path tests for document loaders."""

import pytest

from signer.document_loader import LibreOfficeLoader, PDFLoader


def test_empty_pdf_raises_value_error(monkeypatch, tmp_path):
    class EmptyDocument:
        is_encrypted = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def __len__(self):
            return 0

    monkeypatch.setattr("signer.document_loader.fitz.open", lambda _: EmptyDocument())

    with pytest.raises(ValueError, match="no pages"):
        PDFLoader().load(tmp_path / "empty.pdf")


def test_missing_libreoffice_raises_value_error(tmp_path):
    document_path = tmp_path / "document.docx"
    document_path.write_bytes(b"not a real document")

    with pytest.raises(ValueError, match="LibreOffice is required"):
        LibreOfficeLoader(str(tmp_path / "missing-libreoffice")).load(document_path)