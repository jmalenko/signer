"""Tests that clicking the canvas always re-asserts window activation and
keyboard focus. Some launch methods (e.g. starting the app from an IDE
debugger) can cause the app window to silently lose "active" status between
interactions, leaving keyboard shortcuts (Delete, arrow-key move, etc.)
unresponsive for a "selected" annotation until an unrelated event happens to
restore focus.
"""

from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from signer.canvas import DocumentCanvas
from signer.objects import AnnotationType, VectorAnnotation


def _make_press_event(pos: tuple[float, float]) -> QMouseEvent:
    return QMouseEvent(
        QEvent.MouseButtonPress, QPointF(*pos), QPointF(*pos),
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    )


class TestCanvasMousePressReassertsActivation:
    def test_mouse_press_reasserts_window_activation_and_focus(self, qtbot):
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        canvas.set_pages([Image.new("RGB", (600, 800), "white")])
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        canvas.add_object(ann)
        canvas.clear_selection()

        r = canvas._object_view_rect(ann)
        pt = (r.x() + r.width() / 2, r.y() + r.height() / 2)

        with patch.object(DocumentCanvas, "setFocus", autospec=True) as mock_set_focus:
            canvas.mousePressEvent(_make_press_event(pt))

        assert canvas.selected is ann
        assert mock_set_focus.called
