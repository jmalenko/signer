"""A recognized extension typed in Save As decides the export format; the invalid-filename
message returns to the Save As dialog instead of closing it (spec §5.3)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from signer.compositor import ExportFormat
from signer.objects import AnnotationType, VectorAnnotation
from tests.utils.test_helpers import FakeSaveDialog


@pytest.fixture
def three_page_window(main_window, tmp_path):
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
    main_window.document_path = str(tmp_path / "doc.pdf")
    main_window.canvas.set_pages([Image.new("RGB", (600, 800)) for _ in range(3)])
    main_window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 50, 50, page=0))
    main_window._settings.last_export_folder = str(tmp_path)
    return main_window


def test_a_typed_pdf_extension_wins_over_the_jpeg_filter(three_page_window, tmp_path):
    written = {}
    with patch(
        "signer.main_window.QFileDialog.getSaveFileName",
        return_value=(str(tmp_path / "my-scan.pdf"), ExportFormat.JPG.file_filter()),
    ), patch(
        "signer.main_window.composite_pages_to_pdf",
        side_effect=lambda pages, objs, out, quality: written.setdefault("pdf", Path(out)),
    ), patch("signer.main_window.composite_objects_to_format") as per_page:
        assert three_page_window.save_document_as()

    assert written["pdf"].name == "my-scan.pdf"
    per_page.assert_not_called()


def test_an_invalid_filename_returns_to_the_save_dialog(three_page_window, tmp_path):
    window = three_page_window
    FakeSaveDialog.shown = 0
    names = [str(tmp_path / "no-placeholder.jpg"), str(tmp_path / "good-p#.jpg")]
    window._in_test_mode = False
    try:
        with patch("signer.main_window._SaveDialogWithFilterDetection", FakeSaveDialog(names)), \
             patch("signer.main_window.QMessageBox.information") as info, \
             patch("signer.main_window.QMessageBox.warning") as warning, \
             patch("signer.main_window.composite_objects_to_format"), \
             patch("signer.main_window.NotificationToast"):
            assert window.save_document_as()
    finally:
        window._in_test_mode = True

    assert FakeSaveDialog.shown == 2
    info.assert_called_once()
    warning.assert_not_called()
