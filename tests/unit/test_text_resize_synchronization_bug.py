"""Regression tests for synchronized text resizing controls."""

import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle, QStyleOptionSpinBox

from signer.history import ResizeAnnotationAction
from signer.objects import AnnotationType, VectorAnnotation


def _click_spinbox_down_arrow(spinner):
    option = QStyleOptionSpinBox()
    spinner.initStyleOption(option)
    arrow_rect = spinner.style().subControlRect(
        QStyle.CC_SpinBox,
        option,
        QStyle.SC_SpinBoxDown,
        spinner,
    )
    QTest.mouseClick(spinner, Qt.LeftButton, pos=arrow_rect.center())


def test_toolbar_font_size_change_updates_text_without_error(main_window):
    annotation = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Signer")
    main_window.canvas.add_object(annotation)

    main_window._font_size_spinner.setValue(24)

    assert annotation._font_size_px == 24
    assert main_window._font_size_spinner.value() == 24


def test_bounding_box_resize_updates_font_size_and_toolbar(main_window):
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        0,
        0,
        text="Signer",
        font_size_px=12,
    )
    main_window.canvas.add_object(annotation)
    original_width = annotation.scaled_width
    original_height = annotation.scaled_height

    annotation.set_scaled_size(original_width * 2, original_height * 2)
    main_window.canvas.objectChanged.emit()

    assert annotation._font_size_px == 24
    assert main_window._font_size_spinner.value() == 24
    assert annotation.scaled_width == pytest.approx(original_width * 2, rel=0.01)
    assert annotation.scaled_height == pytest.approx(original_height * 2, rel=0.01)


def test_in_progress_text_resize_always_uses_fitted_bounds(qapp):
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        0,
        0,
        text="Signer",
        font_size_px=12,
    )

    for factor in (1.1, 1.2, 1.3, 1.4):
        annotation.resize_to_bounds(
            annotation.scaled_width * factor,
            annotation.scaled_height * factor,
        )
        fitted = VectorAnnotation(
            AnnotationType.TEXT,
            0,
            0,
            text=annotation.text,
            font_size_px=annotation._font_size_px,
        )

        assert annotation.scaled_width == pytest.approx(fitted.scaled_width)
        assert annotation.scaled_height == pytest.approx(fitted.scaled_height)


def test_font_size_down_arrow_works_after_bounding_box_resize(main_window):
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        0,
        0,
        text="Signer",
        font_size_px=12,
    )
    main_window.canvas.resize(800, 900)
    main_window.canvas.set_pages([Image.new("RGB", (1200, 1600), "white")])
    main_window.canvas.add_object(annotation)
    rect = main_window.canvas._object_view_rect(annotation)
    drag_start = rect.bottomRight().toPoint()
    drag_end = rect.bottomRight().toPoint()
    drag_end.setX(drag_start.x() + int(rect.width()))
    drag_end.setY(drag_start.y() + int(rect.height()))

    QTest.mousePress(main_window.canvas, Qt.LeftButton, pos=drag_start)
    QTest.mouseMove(main_window.canvas, drag_end)
    QTest.mouseRelease(main_window.canvas, Qt.LeftButton, pos=drag_end)
    size_after_resize = annotation._font_size_px

    _click_spinbox_down_arrow(main_window._font_size_spinner)

    assert not main_window.canvas._dragging
    assert size_after_resize > 12
    assert main_window._font_size_spinner.value() == size_after_resize - 1
    assert annotation._font_size_px == size_after_resize - 1


def test_text_resize_methods_stay_synchronized_through_history(main_window):
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        0,
        0,
        text="Signer",
        font_size_px=12,
    )
    main_window.canvas.add_object(annotation)
    original_width = annotation.scaled_width
    original_height = annotation.scaled_height

    main_window._font_size_spinner.setValue(24)
    assert main_window.canvas.undo()
    assert annotation._font_size_px == 12
    assert main_window._font_size_spinner.value() == 12
    assert main_window.canvas.redo()
    assert annotation._font_size_px == 24
    assert main_window._font_size_spinner.value() == 24

    resized_width = annotation.scaled_width * 0.5
    resized_height = annotation.scaled_height * 0.5
    annotation.set_scaled_size(resized_width, resized_height)
    main_window.canvas.history.record_action(
        ResizeAnnotationAction(
            object_id=0,
            from_width=original_width * 2,
            from_height=original_height * 2,
            to_width=resized_width,
            to_height=resized_height,
        )
    )
    main_window.canvas.objectChanged.emit()

    assert annotation._font_size_px == 12
    assert main_window._font_size_spinner.value() == 12
    assert main_window.canvas.undo()
    assert annotation._font_size_px == 24
    assert main_window._font_size_spinner.value() == 24
    assert main_window.canvas.redo()
    assert annotation._font_size_px == 12
    assert main_window._font_size_spinner.value() == 12