"""Regression tests: arrow-key nudges are undoable, and a run of them is one
undo entry in the same way a drag is.

Found while reviewing the FUNCTIONAL_SPECIFICATION wording for §11 coalescing:
`move_selected()` changed coordinates without recording any action, so Ctrl+Z
after an arrow-key move silently undid whatever the user did *before* it.
"""

from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from signer.objects import AnnotationType, VectorAnnotation


def _canvas_with_annotation(canvas, x=100.0, y=100.0):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    obj = VectorAnnotation(AnnotationType.CHECKMARK, x, y, 0)
    canvas.add_object(obj)
    canvas.select_annotation(obj)
    canvas.history.clear()
    return obj


def _press(canvas, key, modifiers=Qt.NoModifier):
    canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, modifiers))


def test_arrow_key_move_is_undoable(canvas):
    obj = _canvas_with_annotation(canvas)

    _press(canvas, Qt.Key_Right)
    assert obj.x > 100.0

    assert canvas.undo() is True
    assert (obj.x, obj.y) == (100.0, 100.0)


def test_consecutive_nudges_are_one_undo_entry(canvas):
    """A run of nudges is one continuous adjustment, like a drag."""
    obj = _canvas_with_annotation(canvas)

    for _ in range(3):
        _press(canvas, Qt.Key_Right)
    moved_x = obj.x

    assert len(canvas.history.undo_stack) == 1
    canvas.undo()
    assert obj.x == 100.0 and moved_x > 100.0


def test_a_nudge_run_is_separated_by_another_action(canvas):
    """An unrelated edit between two runs keeps them as separate undo entries."""
    from PySide6.QtGui import QColor

    obj = _canvas_with_annotation(canvas)

    _press(canvas, Qt.Key_Right)
    canvas.set_color_selected(QColor("#0000ff"))
    _press(canvas, Qt.Key_Right)

    assert len(canvas.history.undo_stack) == 3


def test_a_drag_after_a_nudge_is_its_own_undo_entry(canvas):
    """Pressing the mouse starts a new gesture, so the drag must not merge into
    the preceding keyboard nudge."""
    obj = _canvas_with_annotation(canvas)
    _press(canvas, Qt.Key_Right)
    after_nudge = (obj.x, obj.y)

    # Press near the middle of the glyph so the hit test actually starts a drag.
    press_at = QPointF(obj.x + obj.scaled_width / 2, obj.y + obj.scaled_height / 2)
    canvas.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, press_at, press_at,
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    ))
    assert canvas._dragging, "precondition: the press must have started a drag"
    canvas.mouseMoveEvent(_FakeMove(QPointF(400, 400)))
    canvas.mouseReleaseEvent(QMouseEvent(
        QEvent.MouseButtonRelease, QPointF(400, 400), QPointF(400, 400),
        Qt.LeftButton, Qt.NoButton, Qt.NoModifier,
    ))
    assert (obj.x, obj.y) != after_nudge

    canvas.undo()
    assert (obj.x, obj.y) == after_nudge, "undo must return to the post-nudge position"


def test_multi_selection_nudge_undoes_every_annotation(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    first = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
    second = VectorAnnotation(AnnotationType.CROSSMARK, 300, 300, 0)
    canvas.add_object(first)
    canvas.add_object(second)
    canvas.select_all_on_page()
    canvas.history.clear()

    _press(canvas, Qt.Key_Down)
    assert first.y > 100 and second.y > 300

    assert canvas.undo() is True
    assert (first.y, second.y) == (100, 300)


def test_nudge_without_a_selection_records_nothing(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0))
    canvas.clear_selection()
    canvas.history.clear()

    _press(canvas, Qt.Key_Up)

    assert canvas.history.undo_stack == []


class _FakeMove:
    def __init__(self, pos):
        self._pos = pos

    def position(self):
        return self._pos

    def modifiers(self):
        return Qt.NoModifier
