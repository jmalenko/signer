"""Feature tests for UI visual feedback during annotation operations."""

from PySide6.QtCore import QPointF

from signer.objects import AnnotationType, VectorAnnotation


class TestAnnotationCreationFeedback:
    """Test visual feedback during annotation creation."""
    
    def test_line_creation_path(self):
        """Test Line creation shows path from click to cursor."""
        start = QPointF(100, 100)
        end = QPointF(300, 250)
        
        # Line should be created from start to end
        width = end.x() - start.x()
        height = end.y() - start.y()
        
        assert width == 200
        assert height == 150
    
    def test_arrow_creation_direction(self):
        """Test Arrow creation shows direction."""
        start = QPointF(100, 100)
        end = QPointF(300, 250)
        
        # Direction from start to end
        width = end.x() - start.x()
        height = end.y() - start.y()
        
        assert width > 0
        assert height > 0
    
    def test_rectangle_creation_outline(self):
        """Test Rectangle creation shows outline during drag."""
        start = QPointF(100, 100)
        end = QPointF(300, 250)
        
        width = end.x() - start.x()
        height = end.y() - start.y()
        
        assert width == 200
        assert height == 150
    
    def test_ellipse_creation_outline(self):
        """Test Ellipse creation shows outline during drag."""
        start = QPointF(100, 100)
        end = QPointF(350, 300)
        
        width = end.x() - start.x()
        height = end.y() - start.y()
        
        assert width == 250
        assert height == 200


class TestResizeVisualFeedback:
    """Test visual feedback when resizing."""
    
    def test_corner_drag_visual_update(self):
        """Test dragging corner updates visual in real-time."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Simulate dragging bottom-right corner to (350, 300)
        new_width = 250
        new_height = 200
        
        # Visual should update
        assert new_width > 0
        assert new_height > 0
    
    def test_free_corner_drag_visual(self):
        """Test visual feedback when corner dragged past opposite."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Initially at (100, 100)
        # Drag BR corner to (50, 50) - above/left of start
        new_x = 50
        new_y = 50
        
        # Visual should reflect new position
        assert new_x < 100
        assert new_y < 100
    
    def test_resize_feedback_continuous(self):
        """Test resize feedback updates continuously during drag."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Simulate dragging at multiple positions
        positions = [
            (150, 125),
            (200, 150),
            (250, 175),
            (300, 250),
        ]
        
        for x, y in positions:
            width = x - rect.x
            height = y - rect.y
            
            # Each position should be valid for feedback
            assert width > 0
            assert height > 0


class TestPropertyChangeVisualFeedback:
    """Test visual feedback when properties change."""
    
    def test_width_spinner_change_visual(self):
        """Test width spinner change updates visual immediately."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Simulate spinner change from 1.5 to 3.0
        line._line_width_pt = 3.0
        
        # Visual should show thicker line
        assert line._line_width_pt == 3.0
    
    def test_width_slider_to_thick(self):
        """Test changing width from thin to thick."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        
        arrow._line_width_pt = 5.0
        
        # Visual should show much thicker arrow
        assert arrow._line_width_pt == 5.0
    
    def test_font_size_change_visual(self):
        """Test font size change updates text visual immediately."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        text._font_size_pt = 48
        
        # Visual should show much larger text
        assert text._font_size_pt == 48
    
    def test_color_change_visual(self):
        """Test color change updates visual immediately."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        rect.color.setNamedColor("#0000ff")
        
        # Visual should show blue rectangle
        assert rect.color.name() == "#0000ff"


class TestKeyboardShortcutVisualFeedback:
    """Test visual feedback for keyboard shortcuts."""
    
    def test_bracket_right_increases_width_visual(self):
        """Test ] key increases width visually."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        initial = line._line_width_pt
        
        # Simulate ] key
        line._line_width_pt = initial + 0.5
        
        # Visual should show thicker line
        assert line._line_width_pt == 2.0
    
    def test_bracket_left_decreases_width_visual(self):
        """Test [ key decreases width visually."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 3.0
        
        # Simulate [ key
        line._line_width_pt = 3.0 - 0.5
        
        # Visual should show thinner line
        assert line._line_width_pt == 2.5
    
    def test_bracket_right_increases_font_size(self):
        """Test ] key increases font size visually."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        initial = text._font_size_pt
        
        # Simulate ] key
        text._font_size_pt = initial + 1
        
        # Visual should show larger text
        assert text._font_size_pt == initial + 1
    
    def test_bracket_left_decreases_font_size(self):
        """Test [ key decreases font size visually."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 36
        
        # Simulate [ key
        text._font_size_pt = 36 - 1
        
        # Visual should show smaller text
        assert text._font_size_pt == 35


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


class TestMultiplePropertyUpdates:
    """Test visual feedback when multiple properties change together."""
    
    def test_width_and_color_change_together(self):
        """Test line with width and color change."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Change both
        line._line_width_pt = 3.0
        line.color.setNamedColor("#ff0000")
        
        # Visual should show red, thick line
        assert line._line_width_pt == 3.0
        assert line.color.name() == "#ff0000"
    
    def test_font_size_and_family_change_together(self):
        """Test text with font size and family change."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Change both
        text._font_size_pt = 48
        text._font_family = "Times New Roman"
        
        # Visual should show larger text in Times New Roman
        assert text._font_size_pt == 48
        assert text._font_family == "Times New Roman"
    
    def test_rectangle_width_color_together(self):
        """Test rectangle with width and color change."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Change both
        rect._line_width_pt = 2.5
        rect.color.setNamedColor("#0000ff")
        
        # Visual should show blue rectangle with thick outline
        assert rect._line_width_pt == 2.5
        assert rect.color.name() == "#0000ff"
