"""Feature tests for what the user sees when annotations are edited: the rendered result
changes with the toolbar controls and keyboard shortcuts, and the handles are where they are
drawn."""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent

from signer.objects import AnnotationType, VectorAnnotation
from tests.utils.test_helpers import export_to_page


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    return main_window


def ink(annotation) -> int:
    """Amount of ink the annotation paints when exported."""
    return sum(export_to_page(annotation).getchannel("A").getdata())


def opaque_colors(annotation) -> set[tuple[int, int, int]]:
    return {pixel[:3] for pixel in export_to_page(annotation).getdata() if pixel[3] == 255}


class TestPropertyChangeVisualFeedback:
    """The toolbar controls change what is drawn."""

    def test_width_spinner_draws_a_thicker_line(self, window):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, line_width_pt=1.5)
        window.canvas.add_object(line)
        before = ink(line)

        window._width_spinner.setValue(6.0)

        assert line._line_width_pt == 6.0
        assert ink(line) > before

    def test_font_size_spinner_draws_larger_text(self, window):
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, text="Test")
        window.canvas.add_object(text)
        before = ink(text)

        window._font_size_spinner.setValue(48)

        assert text._font_size_pt == 48
        assert ink(text) > before

    def test_the_colour_control_draws_in_the_new_colour(self, window):
        from unittest.mock import patch

        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
        window.canvas.add_object(rect)

        with patch("signer.main_window.QColorDialog.getColor", return_value=QColor("#0000ff")):
            window._pick_color()

        assert opaque_colors(rect) == {(0, 0, 255)}


class TestKeyboardShortcutVisualFeedback:
    """The [ and ] keys change what is drawn."""

    @staticmethod
    def press(canvas, key):
        canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))

    def test_bracket_right_draws_a_thicker_line_and_bracket_left_a_thinner_one(self, window):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, line_width_pt=2.0)
        window.canvas.add_object(line)
        start = ink(line)

        self.press(window.canvas, Qt.Key_BracketRight)
        thicker = ink(line)
        self.press(window.canvas, Qt.Key_BracketLeft)
        self.press(window.canvas, Qt.Key_BracketLeft)

        assert thicker > start
        assert ink(line) < start

    def test_bracket_keys_change_the_text_size(self, window):
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, text="Test", font_size_pt=12)
        window.canvas.add_object(text)

        self.press(window.canvas, Qt.Key_BracketRight)
        larger = text._font_size_pt
        self.press(window.canvas, Qt.Key_BracketLeft)
        self.press(window.canvas, Qt.Key_BracketLeft)

        assert larger > 12 > text._font_size_pt


class TestSelectionHighlighting:
    """Test visual indication of selection state."""
    
    def test_selected_annotation_has_handles(self):
        """Test selected annotation shows handles."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Line now uses endpoint handles.
        handles = line.handle_rects_viewport(100, 100, 200, 150)
        assert len(handles) == 2
    
    def test_handles_at_corners_and_edges(self):
        """Test handles appear at corners and edge midpoints."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        handles = rect.handle_rects_viewport(100, 100, 200, 150)
        
        # Should have 8 handles positioned correctly
        assert len(handles) == 8
        
        # TL corner handle (0)
        assert handles[0].x() < 110
        assert handles[0].y() < 110
        
        # BR corner handle (7)
        assert handles[7].x() > 290
        assert handles[7].y() > 240


class TestCursorFeedback:
    """Test cursor changes during operations."""
    
    def test_corner_handle_resize_cursor(self):
        """Test cursor indicates diagonal resize on corner handle."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Hit test corner handles (0, 2, 5, 7)
        handles = rect.handle_rects_viewport(100, 100, 200, 150)
        
        # Corner 0 (TL)
        corner_point = QPointF(handles[0].center().x(), handles[0].center().y())
        hit = rect.hit_test_handle(100, 100, 200, 150, corner_point)
        assert hit == 0  # Should hit corner handle 0
    
    def test_edge_handle_resize_cursor(self):
        """Test cursor indicates constrained resize on edge handle."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        handles = rect.handle_rects_viewport(100, 100, 200, 150)
        
        # Edge handle 1 (top middle)
        edge_point = QPointF(handles[1].center().x(), handles[1].center().y())
        hit = rect.hit_test_handle(100, 100, 200, 150, edge_point)
        assert hit == 1  # Should hit edge handle 1
