"""Regression tests: action coalescing must not reach across a finished gesture,
and a new action must always invalidate the redo branch.

See CODE_REVIEW_PLAN.md section A4.
"""

from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from signer.history import ChangeColorAction, HistoryStack, MoveAnnotationAction
from signer.objects import AnnotationType, VectorAnnotation


class _FakeMouseEvent:
    """Minimal stand-in for QMouseEvent as used by DocumentCanvas.mouseMoveEvent."""

    def __init__(self, pos: QPointF):
        self._pos = pos

    def position(self) -> QPointF:
        return self._pos

    def modifiers(self):
        return Qt.NoModifier


def _release_event(pos: tuple[float, float]) -> QMouseEvent:
    return QMouseEvent(
        QEvent.MouseButtonRelease, QPointF(*pos), QPointF(*pos),
        Qt.LeftButton, Qt.NoButton, Qt.NoModifier,
    )


def _canvas_with_annotation(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
    canvas.add_object(obj)
    canvas.select_annotation(obj)
    canvas.history.clear()
    return obj


def _drag(canvas, obj, start, *waypoints):
    """Press on obj at `start`, move through `waypoints`, release."""
    canvas._dragging = True
    canvas._drag_handle = -1
    canvas._drag_doc_offset_x = start[0] - obj.x
    canvas._drag_doc_offset_y = start[1] - obj.y
    canvas._drag_start_x = obj.x
    canvas._drag_start_y = obj.y
    canvas._action_recorded_this_drag = False
    for point in waypoints:
        canvas.mouseMoveEvent(_FakeMouseEvent(QPointF(*point)))
    canvas.mouseReleaseEvent(_release_event(waypoints[-1]))


def test_moves_within_one_drag_coalesce(canvas):
    obj = _canvas_with_annotation(canvas)

    _drag(canvas, obj, (100, 100), (150, 150), (200, 200), (250, 250))

    assert len(canvas.history.undo_stack) == 1


def test_two_drags_are_two_undo_steps(canvas):
    """Releasing the mouse ends the coalescing window."""
    obj = _canvas_with_annotation(canvas)

    _drag(canvas, obj, (100, 100), (200, 200))
    intermediate = (obj.x, obj.y)
    _drag(canvas, obj, (obj.x, obj.y), (300, 300))

    assert len(canvas.history.undo_stack) == 2

    canvas.undo()
    assert (obj.x, obj.y) == intermediate, "one undo must revert only the second drag"

    canvas.undo()
    assert (obj.x, obj.y) == (100, 100)


def test_coalescing_clears_the_redo_branch():
    """A merged action is still a new user edit, so pending redos are invalidated."""
    stack = HistoryStack()
    stack.record_action(MoveAnnotationAction(object_id=1, from_x=0, from_y=0, to_x=10, to_y=10))
    stack.redo_stack.append(ChangeColorAction(object_id=1, color="#00ff00", from_color="#ff0000"))

    stack.record_action(MoveAnnotationAction(object_id=1, x=20, y=20))

    assert len(stack.undo_stack) == 1, "the move should still have merged"
    assert stack.redo_stack == []


def test_new_action_after_redo_does_not_merge_into_the_redone_action():
    """Redo puts an action back on the undo stack; a later edit must not rewrite it."""
    stack = HistoryStack()
    first = MoveAnnotationAction(object_id=1, from_x=0, from_y=0, to_x=10, to_y=10)
    stack.record_action(first)
    stack.undo_stack.pop()
    stack.redo_stack.append(first)

    class _Canvas:
        _object_map: dict = {}

        class objectChanged:
            @staticmethod
            def emit():
                pass

        @staticmethod
        def current_page_objects():
            return []

    stack.redo(_Canvas())
    stack.record_action(MoveAnnotationAction(object_id=1, from_x=10, from_y=10, to_x=30, to_y=30))

    assert len(stack.undo_stack) == 2
    assert first.data["to_x"] == 10, "the redone action must keep its own target state"
