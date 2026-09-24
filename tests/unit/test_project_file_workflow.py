"""Tests for signer project-file persistence and MainWindow integration."""

import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from signer.objects import AnnotationType, ProjectFile, VectorAnnotation
from signer.settings import AppSettings


def test_auto_save_project_is_enabled_by_default():
    assert AppSettings().auto_save_project is True


def test_auto_save_project_setting_round_trips(settings_store):
    settings = AppSettings(auto_save_project=False)
    settings_store.save(settings)

    restored = settings_store.load()

    assert restored.auto_save_project is False


def test_auto_save_project_menu_reflects_loaded_setting(main_window):
    main_window._settings.auto_save_project = False
    main_window._update_menu_state()

    assert main_window._auto_save_project_action.isChecked() is False


def test_auto_save_project_on_save_menu_action_toggles_checkmark_and_setting(main_window):
    main_window._settings.auto_save_project = False
    main_window._update_menu_state()

    main_window._auto_save_project_action.trigger()

    assert main_window._auto_save_project_action.isChecked() is True
    assert main_window._settings.auto_save_project is True


def test_auto_save_project_on_save_is_not_written_before_export(main_window, tmp_path):
    main_window.document_path = str(tmp_path / "form.pdf")
    main_window._settings.auto_save_project = True
    main_window.canvas.set_pages([Image.new("RGB", (600, 800), "white")])

    with patch("signer.main_window.ProjectFile.write") as write_project:
        main_window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 50, 60, 0))

    write_project.assert_not_called()


def test_auto_save_project_menu_label_explains_save_timing(main_window):
    assert main_window._auto_save_project_action.text() == "Auto-save Project on Save"


def test_project_file_disk_roundtrip(tmp_path):
    source = tmp_path / "form.pdf"
    export = tmp_path / "form-signed.jpg"
    project_path = tmp_path / "form.signer"
    annotation = VectorAnnotation(AnnotationType.CHECKMARK, 10, 20, 0)

    project = ProjectFile.from_annotations(
        document_path=source,
        export_path=export,
        annotations=[annotation],
        current_page=0,
        page_count=1,
    )
    ProjectFile.write(project_path, project)

    loaded = ProjectFile.read(project_path)
    ProjectFile.validate(loaded)
    restored = ProjectFile.load_annotations(loaded)

    assert not {"schema", "created_at", "updated_at", "current_page", "settings"} & set(loaded)
    assert set(loaded) == {"version", "document_path", "annotations"}
    assert loaded["document_path"] == str(source)
    assert restored[0].ann_type == AnnotationType.CHECKMARK
    assert restored[0].x == 10
    assert restored[0].y == 20
    assert loaded["annotations"][0]["width"] == restored[0].scaled_width
    assert loaded["annotations"][0]["height"] == restored[0].scaled_height


def test_project_file_roundtrip_preserves_scaled_dimensions(tmp_path):
    annotation = VectorAnnotation(AnnotationType.CHECKMARK, 10, 20, 0)
    annotation.scale = 4.0
    project = ProjectFile.from_annotations(
        document_path=tmp_path / "form.pdf",
        export_path=None,
        annotations=[annotation],
        current_page=0,
        page_count=1,
    )

    restored = ProjectFile.load_annotations(project)

    assert restored[0].scale == 4.0
    assert restored[0].scaled_width == annotation.scaled_width
    assert restored[0].scaled_height == annotation.scaled_height


def test_main_window_opens_project_through_generic_open(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "form.signer"
    project = ProjectFile.from_annotations(
        document_path=source,
        export_path=tmp_path / "form-signed.jpg",
        annotations=[VectorAnnotation(AnnotationType.CHECKMARK, 30, 40, 0)],
        current_page=0,
        page_count=1,
    )
    ProjectFile.write(project_path, project)

    with patch("signer.main_window.render_all_pages", return_value=[Image.new("RGB", (600, 800), "white")]):
        assert main_window.open_document(str(project_path)) is True

    objects = main_window.canvas.page_objects_at(0)
    assert len(objects) == 1
    assert objects[0].x == 30
    assert objects[0].y == 40
    assert main_window.project_path == str(project_path)
    assert str(project_path) in main_window._settings.recent_document_paths


def test_main_window_opens_signer_project_through_generic_open(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "project.signer"
    project = ProjectFile.from_annotations(
        document_path=source,
        export_path=None,
        annotations=[VectorAnnotation(AnnotationType.CHECKMARK, 30, 40, 0)],
        current_page=0,
        page_count=1,
    )
    ProjectFile.write(project_path, project)

    with patch("signer.main_window.render_all_pages", return_value=[Image.new("RGB", (600, 800), "white")]):
        assert main_window.open_document(str(project_path)) is True

    assert len(main_window.canvas.page_objects_at(0)) == 1


def test_open_project_always_starts_on_first_page(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "form.signer"
    project_path.write_text(json.dumps({
        "version": 1,
        "document_path": "form.pdf",
        "current_page": 2,
        "annotations": [],
    }), encoding="utf-8")

    with patch("signer.main_window.render_all_pages", return_value=[
        Image.new("RGB", (600, 800), "white") for _ in range(3)
    ]):
        assert main_window.open_document(str(project_path)) is True

    assert main_window.canvas.current_page == 0


def test_open_project_restores_page_rotations(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "form.signer"
    project_path.write_text(json.dumps({
        "version": 1,
        "document_path": "form.pdf",
        "rotations": {"2": 90},
        "annotations": [],
    }), encoding="utf-8")

    with patch("signer.main_window.render_all_pages", return_value=[
        Image.new("RGB", (600, 800), "white") for _ in range(3)
    ]):
        assert main_window.open_document(str(project_path)) is True

    assert main_window.canvas._page_rotations == {2: 90}


def test_open_project_normalizes_invalid_page_rotation(main_window, tmp_path):
    """Regression test (silent-failure review finding #7): a malformed/hand-edited
    rotation value that isn't a multiple of 90 must be normalized to the nearest
    supported orientation instead of being silently accepted and then silently
    ignored by the coordinate-transform code (which only handles 0/90/180/270).
    """
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "form.signer"
    project_path.write_text(json.dumps({
        "version": 1,
        "document_path": "form.pdf",
        "rotations": {"1": 100},
        "annotations": [],
    }), encoding="utf-8")

    with patch("signer.main_window.render_all_pages", return_value=[
        Image.new("RGB", (600, 800), "white") for _ in range(3)
    ]):
        assert main_window.open_document(str(project_path)) is True

    assert main_window.canvas._page_rotations == {1: 90}


def test_open_project_returns_keyboard_focus_to_canvas(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "form.signer"
    project_path.write_text(json.dumps({
        "version": 1,
        "document_path": "form.pdf",
        "annotations": [],
    }), encoding="utf-8")

    with patch("signer.main_window.render_all_pages", return_value=[
        Image.new("RGB", (600, 800), "white") for _ in range(3)
    ]):
        assert main_window.open_document(str(project_path)) is True
        # Allow the event loop to process focus events after opening the document
        QApplication.instance().processEvents()

    assert main_window.canvas.hasFocus()


def test_right_key_navigates_after_project_open_without_click(main_window, tmp_path, qapp):
    source = tmp_path / "form.pdf"
    source.touch()
    project_path = tmp_path / "form.signer"
    project_path.write_text(json.dumps({
        "version": 1,
        "document_path": "form.pdf",
        "annotations": [],
    }), encoding="utf-8")

    with patch("signer.main_window.render_all_pages", return_value=[
        Image.new("RGB", (600, 800), "white") for _ in range(3)
    ]):
        assert main_window.open_document(str(project_path)) is True

    qapp.processEvents()
    QTest.keyClick(main_window.canvas, Qt.Key_Right)
    assert main_window.canvas.current_page == 1


def test_project_file_menu_uses_ellipsis_for_change_document(main_window):
    assert main_window._change_document_action.text() == "Change Document…"


def test_file_menu_has_no_new_project_action(main_window):
    assert all(action.text() != "New Project" for action in main_window._hamburger_file_menu.actions())


def test_schema_is_optional_for_project_files(tmp_path):
    project = {
        "version": 1,
        "document_path": "form.pdf",
        "annotations": [],
    }
    ProjectFile.validate(project)


def test_open_project_checks_unsaved_changes_only_once(main_window, tmp_path):
    project_path = tmp_path / "form.signer"
    source = tmp_path / "form.pdf"
    source.touch()
    project_path.write_text(json.dumps({
        "version": 1,
        "document_path": "form.pdf",
        "annotations": [],
    }), encoding="utf-8")
    main_window.document_path = str(source)
    main_window._has_unsaved_changes = True

    with patch.object(main_window, "_check_unsaved_changes", return_value=True) as check_changes, \
         patch("signer.main_window.render_all_pages", return_value=[Image.new("RGB", (600, 800), "white")]):
        assert main_window.open_document(str(project_path)) is True

    check_changes.assert_called_once_with()


def test_auto_save_does_not_write_project_when_annotation_changes(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    main_window.document_path = str(source)
    main_window.project_path = str(tmp_path / "form.signer")
    main_window._settings.auto_save_project = True
    main_window.canvas.set_pages([Image.new("RGB", (600, 800), "white")])

    with patch("signer.main_window.ProjectFile.write") as write_project:
        main_window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 50, 60, 0))

    write_project.assert_not_called()


def test_auto_save_project_path_uses_exported_file_name(main_window, tmp_path):
    assert main_window._project_path_for_export(tmp_path / "abc-signed-p#.jpg") == tmp_path / "abc-signed.signer"


def test_project_extension_is_signer(main_window, tmp_path):
    assert main_window._project_path_for_export(tmp_path / "abc-signed.jpg").suffix == ".signer"


def test_opening_document_does_not_create_document_based_project_path(main_window, tmp_path):
    source = tmp_path / "form.pdf"
    source.touch()
    with patch("signer.main_window.render_all_pages", return_value=[Image.new("RGB", (600, 800), "white")]):
        assert main_window.open_document(str(source)) is True

    assert main_window.project_path is None


def test_change_document_preserves_annotation_positions_when_orientation_changes(
    main_window, tmp_path
):
    source = tmp_path / "portrait.pdf"
    replacement = tmp_path / "landscape.pdf"
    source.touch()
    replacement.touch()
    annotation = VectorAnnotation(AnnotationType.CROSSMARK, 741, 2494, 0)
    annotation.scale = 8.0
    main_window.document_path = str(source)
    main_window.canvas.set_pages([Image.new("RGB", (2481, 3509), "white")])
    main_window.canvas._page_objects[0] = [annotation]

    with patch("signer.main_window.QFileDialog.getOpenFileName", return_value=(str(replacement), "")), \
         patch("signer.main_window.render_all_pages", return_value=[Image.new("RGB", (3509, 2481), "white")]):
        assert main_window.change_document() is True

    restored = main_window.canvas.page_objects_at(0)[0]
    assert restored.x == 741
    assert restored.y == 2494


EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _add_checkmarks_on_every_page(main_window, page_count):
    for page in range(page_count):
        main_window.canvas.goto_page(page)
        annotation = VectorAnnotation(AnnotationType.CHECKMARK, 10 + page, 20 + page, page)
        main_window.canvas.add_object(annotation)


def _save_and_reopen_project(main_window, project_path, document_path, page_count):
    objects = [
        obj
        for page in range(main_window.canvas.page_count)
        for obj in main_window.canvas.page_objects_at(page)
    ]
    project = ProjectFile.from_annotations(
        document_path=document_path, export_path=None, annotations=objects,
        current_page=0, page_count=page_count,
    )
    ProjectFile.write(project_path, project)
    with patch(
        "signer.main_window.render_all_pages",
        return_value=[Image.new("RGB", (600, 800), "white") for _ in range(page_count)],
    ):
        assert main_window.open_project(project_path) is True


def test_change_document_to_fewer_pages_keeps_only_annotations_on_remaining_pages(
    main_window, tmp_path
):
    """Changing to a document with fewer pages drops annotations whose page no longer exists."""
    document = EXAMPLES_DIR / "document.pdf"
    fewer_pages_document = EXAMPLES_DIR / "document1.pdf"
    project_path = tmp_path / "project.signer"

    with patch(
        "signer.main_window.render_all_pages",
        return_value=[Image.new("RGB", (600, 800), "white") for _ in range(3)],
    ):
        assert main_window.open_document(str(document)) is True

    _add_checkmarks_on_every_page(main_window, page_count=3)
    _save_and_reopen_project(main_window, project_path, document, page_count=3)

    with patch(
        "signer.main_window.render_all_pages",
        return_value=[Image.new("RGB", (600, 800), "white")],
    ), patch(
        "signer.main_window.QFileDialog.getOpenFileName",
        return_value=(str(fewer_pages_document), ""),
    ):
        assert main_window.change_document() is True

    assert main_window.canvas.page_count == 1
    remaining = [
        obj
        for page in range(main_window.canvas.page_count)
        for obj in main_window.canvas.page_objects_at(page)
    ]
    assert len(remaining) == 1
    assert remaining[0].x == 10
    assert remaining[0].y == 20
    assert remaining[0].ann_type == AnnotationType.CHECKMARK


def test_change_document_to_landscape_preserves_annotations_on_every_page(
    main_window, tmp_path
):
    """Changing to a same-page-count landscape document keeps every page's annotations."""
    document = EXAMPLES_DIR / "document.pdf"
    landscape_document = EXAMPLES_DIR / "doc-landscape.pdf"
    project_path = tmp_path / "project.signer"

    with patch(
        "signer.main_window.render_all_pages",
        return_value=[Image.new("RGB", (600, 800), "white") for _ in range(3)],
    ):
        assert main_window.open_document(str(document)) is True

    _add_checkmarks_on_every_page(main_window, page_count=3)
    _save_and_reopen_project(main_window, project_path, document, page_count=3)

    with patch(
        "signer.main_window.render_all_pages",
        return_value=[Image.new("RGB", (800, 600), "white") for _ in range(3)],
    ), patch(
        "signer.main_window.QFileDialog.getOpenFileName",
        return_value=(str(landscape_document), ""),
    ):
        assert main_window.change_document() is True

    assert main_window.canvas.page_count == 3
    for page in range(3):
        objects = main_window.canvas.page_objects_at(page)
        assert len(objects) == 1
        assert objects[0].x == 10 + page
        assert objects[0].y == 20 + page
        assert objects[0].ann_type == AnnotationType.CHECKMARK
