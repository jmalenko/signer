"""Tests for the bug where moving the selected annotation with arrow keys
updates its stored position immediately, but the canvas is never told to
repaint, so the move is only visible once some unrelated action (e.g.
deselecting) happens to trigger a repaint.
"""

from unittest.mock import patch

from PIL import Image

from signer.canvas import DocumentCanvas
from signer.objects import AnnotationType, VectorAnnotation


class TestArrowKeyMoveRepaint:
    def test_move_selected_schedules_a_repaint(self, qtbot):
        """Expected behavior: moving the selected annotation triggers a
        repaint immediately, so the new position is visible right away."""
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        canvas.set_pages([Image.new("RGB", (600, 800), "white")])
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        canvas.add_object(ann)

        with patch.object(DocumentCanvas, "update", autospec=True) as mock_update:
            canvas.move_selected(12.0, 0.0)

        assert (ann.x, ann.y) == (112.0, 100.0)
        assert mock_update.called
