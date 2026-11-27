"""Undo/redo must restore the complete state of an annotation, and the selection must never
refer to something that is not on the page (spec §11)."""

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from signer.objects import AnnotationType, VectorAnnotation


def _mouse(kind, pos, button=Qt.LeftButton, buttons=Qt.LeftButton):
    return QMouseEvent(kind, QPointF(*pos), QPointF(*pos), button, buttons, Qt.NoModifier)


def press_move_release(canvas, start, *points):
    canvas.mousePressEvent(_mouse(QEvent.MouseButtonPress, start))
    for point in points:
        canvas.mouseMoveEvent(_mouse(QEvent.MouseMove, point, Qt.NoButton))
    canvas.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, points[-1], Qt.LeftButton, Qt.NoButton))


@pytest.fixture
def page_canvas(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    return canvas


def add_selected(canvas, ann_type, x, y):
    obj = VectorAnnotation(ann_type, x, y)
    canvas.add_object(obj)
    canvas.select_annotation(obj)
    canvas.history.clear()
    return obj


def handle_center(canvas, obj, index):
    rect = canvas._object_view_rect(obj)
    rects = obj.handle_rects_viewport(rect.x(), rect.y(), rect.width(), rect.height(), canvas._display_rotation(obj))
    center = rects[index].center()
    return center.x(), center.y()


def geometry(obj):
    return (round(obj.x, 3), round(obj.y, 3), round(obj.scaled_width, 3), round(obj.scaled_height, 3), obj._angle)


@pytest.mark.parametrize("ann_type", [AnnotationType.RECTANGLE, AnnotationType.TEXT, AnnotationType.CHECKMARK])
def test_undo_of_a_corner_resize_restores_position_and_size(page_canvas, ann_type):
    obj = add_selected(page_canvas, ann_type, 300, 300)
    before = geometry(obj)
    start = handle_center(page_canvas, obj, 0)

    press_move_release(page_canvas, start, (start[0] - 60, start[1] - 40), (start[0] - 120, start[1] - 90))
    after = geometry(obj)
    assert after != before

    assert page_canvas.undo()
    assert geometry(obj) == before
    assert page_canvas.redo()
    assert geometry(obj) == after


@pytest.mark.parametrize("ann_type", [AnnotationType.LINE, AnnotationType.ARROW])
def test_undo_of_an_endpoint_drag_restores_position_size_and_direction(page_canvas, ann_type):
    obj = add_selected(page_canvas, ann_type, 300, 300)
    before = geometry(obj)
    start = handle_center(page_canvas, obj, 1)

    press_move_release(page_canvas, start, (start[0] + 60, start[1] + 150), (start[0] + 20, start[1] + 260))
    after = geometry(obj)
    assert after != before

    assert page_canvas.undo()
    assert geometry(obj) == before
    assert page_canvas.redo()
    assert geometry(obj) == after


def test_redo_of_a_move_limited_by_the_page_goes_to_the_limited_position(page_canvas):
    obj = add_selected(page_canvas, AnnotationType.CHECKMARK, 300, 300)
    press_move_release(page_canvas, (320, 320), (4000, 4000))
    limited = (obj.x, obj.y)
    assert limited[0] < 1000 and limited[1] < 1000

    assert page_canvas.undo()
    assert page_canvas.redo()
    assert (obj.x, obj.y) == limited


def test_redo_of_a_delete_after_undoing_the_add(page_canvas):
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 300, 300)
    page_canvas.add_object(obj)
    page_canvas.select_annotation(obj)
    page_canvas.remove_selected()
    assert page_canvas.current_page_objects() == []

    for _ in range(2):
        assert page_canvas.undo()
    assert page_canvas.current_page_objects() == []
    for _ in range(2):
        assert page_canvas.redo()

    assert page_canvas.current_page_objects() == []


def test_selection_does_not_outlive_the_undone_annotation(page_canvas):
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 300, 300)
    page_canvas.add_object(obj)
    assert page_canvas.selected is obj

    assert page_canvas.undo()

    assert page_canvas.selected is None
    assert page_canvas.get_selected_annotations() == []


def test_adding_an_annotation_replaces_a_multi_selection(page_canvas):
    first = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    second = VectorAnnotation(AnnotationType.ELLIPSE, 500, 500)
    page_canvas.add_object(first)
    page_canvas.add_object(second)
    page_canvas.select_all_on_page()

    new = VectorAnnotation(AnnotationType.CHECKMARK, 700, 100)
    page_canvas.add_object(new)

    assert page_canvas.get_selected_annotations() == [new]


def test_nothing_stays_selected_after_deleting_the_selection(page_canvas):
    first = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    page_canvas.add_object(first)
    page_canvas.select_all_on_page()

    page_canvas.remove_selected()

    assert page_canvas.get_selected_annotations() == []
