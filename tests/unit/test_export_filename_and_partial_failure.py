"""Regression tests for export filename handling and partial-export reporting.

See CODE_REVIEW_PLAN.md sections B7 and B8.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from signer.compositor import ExportFormat, ensure_export_extension
from signer.objects import AnnotationType, VectorAnnotation


class TestEnsureExportExtension:
    def test_replaces_a_known_export_extension(self):
        result = ensure_export_extension(Path("/tmp/report.png"), ".jpg")
        assert result == Path("/tmp/report.jpg")

    def test_leaves_a_matching_extension_alone(self):
        result = ensure_export_extension(Path("/tmp/report.jpg"), ".jpg")
        assert result == Path("/tmp/report.jpg")

    def test_appends_when_the_name_merely_contains_a_dot(self):
        """`contract v1.2-signed` must not be truncated to `contract v1.jpg`."""
        result = ensure_export_extension(Path("/tmp/contract v1.2-signed"), ".jpg")
        assert result == Path("/tmp/contract v1.2-signed.jpg")

    def test_appends_when_there_is_no_extension_at_all(self):
        result = ensure_export_extension(Path("/tmp/report"), ".pdf")
        assert result == Path("/tmp/report.pdf")

    def test_keeps_a_version_number_when_switching_known_formats(self):
        result = ensure_export_extension(Path("/tmp/report v2.1-signed-p#.png"), ".jpg")
        assert result == Path("/tmp/report v2.1-signed-p#.jpg")

    def test_is_case_insensitive_about_the_existing_extension(self):
        result = ensure_export_extension(Path("/tmp/report.JPG"), ".jpg")
        assert result == Path("/tmp/report.JPG")


class TestKnownExtension:
    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".pdf", ".tif", ".tiff", ".bmp"])
    def test_known(self, ext):
        assert ExportFormat.is_known_extension(ext) is True

    @pytest.mark.parametrize("ext", ["", ".2-signed", ".docx", ".v2"])
    def test_unknown(self, ext):
        assert ExportFormat.is_known_extension(ext) is False


def test_export_reports_failure_when_some_pages_could_not_be_written(main_window, tmp_path):
    """A partial export must not be reported as a successful save."""
    main_window.canvas.set_pages([Image.new("RGB", (600, 800), "white") for _ in range(3)])
    main_window.document_path = str(tmp_path / "doc.pdf")
    main_window._has_unsaved_changes = True
    for page in range(3):
        main_window.canvas._page_objects[page] = [
            VectorAnnotation(AnnotationType.CHECKMARK, 10, 10, page=page)
        ]

    calls = {"n": 0}

    def flaky_export(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk hiccup")

    with patch(
        "signer.main_window.QFileDialog.getSaveFileName",
        return_value=(str(tmp_path / "out-p#.jpg"), ExportFormat.JPG.file_filter()),
    ), patch("signer.main_window.composite_objects_to_format", side_effect=flaky_export):
        result = main_window.save_document_as()

    assert result is False, "an export that lost a page is not a successful save"
    assert main_window._has_unsaved_changes is True
