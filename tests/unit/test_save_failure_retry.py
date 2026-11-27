"""A failed export offers Retry and Cancel; a retry writes the pages that failed again
(spec §14)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtWidgets import QMessageBox

from signer.objects import AnnotationType, VectorAnnotation
from tests.utils.test_helpers import FakeSaveDialog


@pytest.fixture
def window(main_window, tmp_path):
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
    main_window.document_path = str(tmp_path / "doc.pdf")
    main_window.canvas.set_pages([Image.new("RGB", (600, 800)) for _ in range(3)])
    main_window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 50, 50, page=0))
    main_window._settings.last_export_folder = str(tmp_path)
    return main_window


def export(window, name, answers, **patches):
    """Run Save As (typing `name`), answering the failure dialog with `answers` in turn."""
    FakeSaveDialog.shown = 0
    window._in_test_mode = False
    answers = list(answers)
    try:
        with patch("signer.main_window._SaveDialogWithFilterDetection", FakeSaveDialog([name])), \
             patch("signer.main_window.QMessageBox.critical", side_effect=lambda *a, **k: answers.pop(0)) as critical, \
             patch("signer.main_window.NotificationToast"):
            for target, replacement in patches.items():
                patcher = patch(f"signer.main_window.{target}", side_effect=replacement)
                patcher.start()
            try:
                result = window.save_document_as()
            finally:
                patch.stopall()
    finally:
        window._in_test_mode = True
    return result, critical


def test_a_failed_pdf_save_can_be_retried(window, tmp_path):
    attempts = []

    def flaky(pages, objects, out, quality):
        attempts.append(Path(out).name)
        if len(attempts) == 1:
            raise OSError("disk hiccup")

    result, critical = export(window, str(tmp_path / "out.pdf"), [QMessageBox.Retry], composite_pages_to_pdf=flaky)

    assert result is True
    assert attempts == ["out.pdf", "out.pdf"]
    buttons = critical.call_args.args[3]
    assert buttons & QMessageBox.Retry and buttons & QMessageBox.Cancel


def test_cancelling_after_a_failed_save_gives_up(window, tmp_path):
    def always_fails(pages, objects, out, quality):
        raise PermissionError("denied")

    result, critical = export(window, str(tmp_path / "out.pdf"), [QMessageBox.Cancel], composite_pages_to_pdf=always_fails)

    assert result is False
    critical.assert_called_once()
    assert window._has_unsaved_changes is True  # a failed export does not count as saved


def test_a_retry_writes_only_the_pages_that_failed(window, tmp_path):
    written = []

    def flaky(page_image, objects, out_path, export_format, quality):
        name = Path(out_path).name
        if name.endswith("p2.jpg") and written.count(name) == 0:
            written.append(name)
            raise OSError("disk hiccup")
        written.append(name)

    result, critical = export(
        window, str(tmp_path / "scan-p#.jpg"), [QMessageBox.Retry], composite_objects_to_format=flaky
    )

    assert result is True
    assert written == ["scan-p1.jpg", "scan-p2.jpg", "scan-p3.jpg", "scan-p2.jpg"]
    assert "Page 2" in critical.call_args.args[2]


def test_a_full_disk_stops_the_export_and_offers_a_retry(window, tmp_path):
    calls = []

    def disk_full(page_image, objects, out_path, export_format, quality):
        calls.append(Path(out_path).name)
        if len(calls) == 2:
            raise OSError(28, "No space left on device")

    result, critical = export(
        window, str(tmp_path / "scan-p#.jpg"), [QMessageBox.Cancel], composite_objects_to_format=disk_full
    )

    assert result is False
    assert calls == ["scan-p1.jpg", "scan-p2.jpg"], "the export stops at the full disk"
    assert "space" in critical.call_args.args[2].lower()
