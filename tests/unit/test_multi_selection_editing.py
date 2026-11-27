"""Moving and resizing with the mouse and the keyboard (spec §8, §9)."""

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from signer.constants import DPI_SCALE
from signer.objects import AnnotationType, VectorAnnotation


def mouse(kind, pos, button=Qt.LeftButton, buttons=Qt.LeftButton, modifiers=Qt.NoModifier):
    return QMouseEvent(kind, QPointF(*pos), QPointF(*pos), button, buttons, modifiers)


def drag(canvas, start, *points, modifiers=Qt.NoModifier):
    canvas.mousePressEvent(mouse(QEvent.MouseButtonPress, start, modifiers=modifiers))
    for point in points:
        canvas.mouseMoveEvent(mouse(QEvent.MouseMove, point, Qt.NoButton))
    canvas.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, points[-1] if points else start, Qt.LeftButton, Qt.NoButton))


@pytest.fixture
def page_canvas(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    return canvas


@pytest.fixture
def two_selected(page_canvas):
    first = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    second = VectorAnnotation(AnnotationType.ELLIPSE, 500, 500)
    page_canvas.add_object(first)
    page_canvas.add_object(second)
    page_canvas.select_all_on_page()
    page_canvas.history.clear()
    return page_canvas, first, second


def test_dragging_a_multi_selection_moves_every_member_by_the_same_distance(two_selected):
    canvas, first, second = two_selected
    # Press well inside the second one (its transparent interior is selectable inside the box).
    drag(canvas, (600, 600), (650, 640), (700, 680))

    assert (first.x, first.y) == pytest.approx((200, 180))
    assert (second.x, second.y) == pytest.approx((600, 580))
    assert len(canvas.get_selected_annotations()) == 2


def test_a_group_drag_is_one_undo_step(two_selected):
    canvas, first, second = two_selected
    drag(canvas, (600, 600), (650, 640), (700, 680))
    assert len(canvas.history.undo_stack) == 1

    assert canvas.undo()
    assert (first.x, first.y, second.x, second.y) == pytest.approx((100, 100, 500, 500))
    assert canvas.redo()
    assert (first.x, first.y) == pytest.approx((200, 180))


def test_clicking_a_member_without_moving_selects_only_that_one(two_selected):
    canvas, first, second = two_selected
    drag(canvas, (600, 600))

    assert canvas.get_selected_annotations() == [second]


def test_a_multi_selection_has_no_active_resize_handles(two_selected):
    canvas, first, second = two_selected
    canvas._selected = first
    rect = canvas._object_view_rect(first)
    handle = first.handle_rects_viewport(rect.x(), rect.y(), rect.width(), rect.height(), 0.0)[0].center()
    before = (first.scaled_width, first.scaled_height)

    drag(canvas, (handle.x(), handle.y()), (handle.x() - 50, handle.y() - 50))

    assert (first.scaled_width, first.scaled_height) == before


@pytest.mark.parametrize("ann_type", [AnnotationType.RECTANGLE, AnnotationType.TEXT, AnnotationType.LINE])
def test_a_mouse_move_keeps_every_type_on_the_page(page_canvas, ann_type):
    obj = VectorAnnotation(ann_type, 300, 300)
    page_canvas.add_object(obj)

    drag(page_canvas, (310, 310), (5000, 5000))

    assert 0 <= obj.x and obj.x + obj.scaled_width <= 1000
    assert 0 <= obj.y and obj.y + obj.scaled_height <= 1000


def press(canvas, key, modifiers=Qt.NoModifier):
    canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, modifiers))


def test_arrow_keys_move_12pt_and_shift_arrow_1pt(page_canvas):
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 300, 300)
    page_canvas.add_object(obj)

    press(page_canvas, Qt.Key_Right)
    assert obj.x == pytest.approx(300 + 12 * DPI_SCALE)
    press(page_canvas, Qt.Key_Down, Qt.ShiftModifier)
    assert obj.y == pytest.approx(300 + 1 * DPI_SCALE)


def test_rotating_a_group_in_steps_gives_the_same_result_as_in_one_step(page_canvas):
    def build():
        page_canvas.clear_selection()
        page_canvas._page_objects[0] = []
        first = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
        second = VectorAnnotation(AnnotationType.ELLIPSE, 500, 400)
        page_canvas.add_object(first)
        page_canvas.add_object(second)
        page_canvas.select_all_on_page()
        page_canvas._selected = first
        return first, second

    first, second = build()
    for angle in range(1, 91):
        page_canvas.rotate_selected_to(angle)
    stepwise = [v for o in (first, second) for v in (o.x, o.y, o.rotation)]

    first, second = build()
    page_canvas.rotate_selected_to(90)
    at_once = [v for o in (first, second) for v in (o.x, o.y, o.rotation)]

    assert stepwise == pytest.approx(at_once, abs=0.01)
