"""Project path rules of spec §16: an export establishes the project path (auto-save or not),
the document is stored by its absolute path, and a missing `version` is accepted."""

import json
import shutil
from unittest.mock import patch

from PIL import Image

from signer.compositor import ExportFormat
from signer.objects import AnnotationType, ProjectFile, VectorAnnotation


def export_one_page(window, tmp_path):
    window.canvas.set_pages([Image.new("RGB", (600, 800), "white")])
    window.document_path = str(tmp_path / "doc.pdf")
    window.canvas._page_objects[0] = [VectorAnnotation(AnnotationType.CHECKMARK, 10, 10)]
    with patch(
        "signer.main_window.QFileDialog.getSaveFileName",
        return_value=(str(tmp_path / "doc-signed.jpg"), ExportFormat.JPG.file_filter()),
    ):
        assert window.save_document_as()


def test_export_establishes_the_project_path_without_auto_save(main_window, tmp_path):
    main_window._settings.auto_save_project = False

    export_one_page(main_window, tmp_path)

    assert main_window.project_path == str(tmp_path / "doc-signed.signer")
    assert not (tmp_path / "doc-signed.signer").exists()


def test_export_with_auto_save_writes_the_project(main_window, tmp_path):
    main_window._settings.auto_save_project = True

    export_one_page(main_window, tmp_path)

    assert (tmp_path / "doc-signed.signer").exists()


def test_the_document_is_stored_by_its_absolute_path(main_window, sample_pdf, tmp_path, monkeypatch):
    shutil.copy(sample_pdf, tmp_path / "rel.pdf")
    monkeypatch.chdir(tmp_path)

    assert main_window.open_document("rel.pdf")

    assert main_window.document_path == str(tmp_path / "rel.pdf")
    assert main_window.save_project(tmp_path / "p.signer", silent=True)
    assert json.loads((tmp_path / "p.signer").read_text())["document_path"] == str(tmp_path / "rel.pdf")


def test_a_project_without_version_is_accepted():
    ProjectFile.validate({"document_path": "form.pdf", "annotations": []})
