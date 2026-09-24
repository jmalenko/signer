"""Tests for text annotation character spacing."""

import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from signer.objects import AnnotationType, ProjectFile, VectorAnnotation
from signer.settings import AppSettings, SettingsStore
from tests.recording.action_player import ActionPlayer


def _rotated_left_edge_midpoint(annotation):
    points = annotation.boundary_points_viewport(
        annotation.x,
        annotation.y,
        annotation.scaled_width,
        annotation.scaled_height,
        annotation.rotation,
    )
    return (points[0] + points[3]) / 2.0


def test_character_spacing_expands_text_bounds_and_roundtrips(qapp):
    compact = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="BOXES")
    spaced = VectorAnnotation(
        AnnotationType.TEXT,
        0,
        0,
        text="BOXES",
        character_spacing_pt=6.0,
    )

    assert compact._character_spacing_pt == 0.0
    assert spaced.scaled_width > compact.scaled_width

    restored = VectorAnnotation.from_dict(spaced.to_dict())
    assert restored._character_spacing_pt == pytest.approx(6.0)
    assert restored.scaled_width == pytest.approx(spaced.scaled_width)


def test_toolbar_character_spacing_change_is_undoable(main_window):
    annotation = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Signer")
    main_window.canvas.add_object(annotation)
    original_width = annotation.scaled_width

    main_window._character_spacing_spinner.setValue(-3.5)

    assert annotation._character_spacing_pt == pytest.approx(-3.5)
    assert annotation.scaled_width < original_width
    assert main_window.canvas.undo()
    assert annotation._character_spacing_pt == 0.0
    assert main_window.canvas.redo()
    assert annotation._character_spacing_pt == pytest.approx(-3.5)

    main_window._character_spacing_spinner.setValue(120.0)
    assert annotation._character_spacing_pt == pytest.approx(120.0)


def test_spacing_control_follows_font_family_and_steps_by_one(main_window):
    actions = main_window._main_toolbar.actions()

    assert actions.index(main_window._font_family_combo_action) < actions.index(
        main_window._character_spacing_label_action
    )
    assert main_window._character_spacing_spinner.singleStep() == 1.0


def test_rotated_spacing_change_keeps_left_edge_fixed(main_window):
    annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, text="Signer")
    annotation.rotation = 35.0
    main_window.canvas.add_object(annotation)
    original_left_edge = _rotated_left_edge_midpoint(annotation)

    main_window.canvas.set_character_spacing_selected(8.0)

    new_left_edge = _rotated_left_edge_midpoint(annotation)
    assert (new_left_edge.x(), new_left_edge.y()) == pytest.approx(
        (original_left_edge.x(), original_left_edge.y())
    )
    assert main_window.canvas.undo()
    undo_left_edge = _rotated_left_edge_midpoint(annotation)
    assert (undo_left_edge.x(), undo_left_edge.y()) == pytest.approx(
        (original_left_edge.x(), original_left_edge.y())
    )
    assert main_window.canvas.redo()
    redo_left_edge = _rotated_left_edge_midpoint(annotation)
    assert (redo_left_edge.x(), redo_left_edge.y()) == pytest.approx(
        (original_left_edge.x(), original_left_edge.y())
    )


def test_character_spacing_handle_drag_updates_spacing_and_is_undoable(main_window):
    canvas = main_window.canvas
    canvas.resize(800, 800)
    canvas.set_pages([Image.new("RGB", (800, 800), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, text="FORM")
    canvas.add_object(annotation)
    canvas.clear_history()
    original_font_size = annotation._font_size_pt
    rect = canvas._object_view_rect(annotation)
    start = annotation.character_spacing_handle_center_viewport(
        rect.x(), rect.y(), rect.width(), rect.height()
    ).toPoint()
    end = start + type(start)(80, 0)

    QTest.mousePress(canvas, Qt.LeftButton, pos=start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.LeftButton, pos=end)

    assert annotation._character_spacing_pt > 0.0
    assert annotation._font_size_pt == original_font_size
    assert main_window._character_spacing_spinner.value() == pytest.approx(
        annotation._character_spacing_pt
    )
    assert canvas.undo()
    assert annotation._character_spacing_pt == 0.0

    rect = canvas._object_view_rect(annotation)
    start = annotation.character_spacing_handle_center_viewport(
        rect.x(), rect.y(), rect.width(), rect.height()
    ).toPoint()
    end = start - type(start)(80, 0)
    QTest.mousePress(canvas, Qt.LeftButton, pos=start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.LeftButton, pos=end)

    assert annotation._character_spacing_pt < 0.0


def test_rotated_character_spacing_handle_follows_text_axis(main_window):
    canvas = main_window.canvas
    canvas.resize(800, 800)
    canvas.set_pages([Image.new("RGB", (800, 800), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, text="FORM")
    annotation.rotation = 90.0
    canvas.add_object(annotation)
    canvas.clear_history()
    rect = canvas._object_view_rect(annotation)
    start = annotation.character_spacing_handle_center_viewport(
        rect.x(), rect.y(), rect.width(), rect.height(), annotation.rotation
    ).toPoint()
    end = start + type(start)(0, 80)

    QTest.mousePress(canvas, Qt.LeftButton, pos=start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.LeftButton, pos=end)

    assert annotation._character_spacing_pt > 0.0
    assert canvas.undo()
    assert annotation._character_spacing_pt == 0.0


def test_project_roundtrip_preserves_character_spacing():
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        10,
        20,
        text="BOXES",
        character_spacing_pt=3.5,
    )

    project = ProjectFile.from_annotations(
        document_path="form.pdf",
        annotations=[annotation],
    )
    restored = ProjectFile.load_annotations(project)[0]

    assert project["annotations"][0]["character_spacing_pt"] == pytest.approx(3.5)
    assert restored._character_spacing_pt == pytest.approx(3.5)


def test_duplicate_preserves_character_spacing():
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        10,
        20,
        text="BOXES",
        character_spacing_pt=-2.5,
    )

    duplicate = annotation.duplicate()

    assert duplicate._character_spacing_pt == pytest.approx(-2.5)


def test_recent_character_spacing_setting_roundtrips(tmp_path):
    store = SettingsStore("SignerCharacterSpacingTest")
    store._settings_path = tmp_path / "config.json"
    store.save(AppSettings(recent_character_spacing_pt=-4.5))

    restored = store.load()

    assert restored.recent_character_spacing_pt == pytest.approx(-4.5)


def test_recorded_add_applies_character_spacing_metadata(main_window):
    main_window.canvas.set_pages([Image.new("RGB", (800, 800), "white")])
    player = ActionPlayer(main_window)

    player._execute_add_annotation({
        "type": "add_annotation",
        "annotation_type": "text",
        "x": 100,
        "y": 100,
        "object_id": 0,
        "text": "FORM",
        "font_family": "Courier New",
        "font_size_pt": 16,
        "character_spacing_pt": 8.0,
    })

    assert main_window.canvas.selected._character_spacing_pt == pytest.approx(8.0)
    assert main_window.canvas.selected._font_family == "Courier New"
    assert main_window.canvas.selected._font_size_pt == 16