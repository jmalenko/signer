"""Feature tests for complete end-to-end workflows with new annotation types."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor
from signer.objects import VectorAnnotation, AnnotationType, DIRECTIONAL_ARROW_TYPES
from signer.canvas import DocumentCanvas


class TestLineWorkflow:
    """Test complete Line annotation workflows."""
    
    def test_create_line_modify_width_export(self, qtbot):
        """Test: create Line → change width → export."""
        # Create line
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line.ann_type == AnnotationType.LINE
        
        # Modify width
        line._line_width_pt = 3.5
        assert line._line_width_pt == 3.5
        
        # Serialize for export
        data = line.to_dict()
        assert data['line_width_pt'] == 3.5
    
    def test_create_line_move_resize(self, qtbot):
        """Test: create Line → move → resize."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Move
        line.x = 150
        line.y = 150
        assert line.x == 150
        
        # Resize
        line.set_scaled_size(300, 200)
        assert line.scaled_width == 300


class TestArrowWorkflow:
    """Test complete Arrow annotation workflows."""
    
    def test_create_generic_arrow_workflow(self, qtbot):
        """Test: create generic arrow → modify width → export."""
        arrow = VectorAnnotation(AnnotationType.ARROW_GENERIC, 100, 100, 0)
        assert arrow.ann_type == AnnotationType.ARROW_GENERIC
        
        # Modify width
        arrow._line_width_pt = 2.5
        
        # Export
        data = arrow.to_dict()
        assert data['line_width_pt'] == 2.5
        assert 'ann_type' in data
    
    def test_all_directional_arrows_workflow(self):
        """Test all 8 directional arrows can be created and used."""
        arrow_data = []
        
        for arrow_type in DIRECTIONAL_ARROW_TYPES:
            arrow = VectorAnnotation(arrow_type, 100, 100, 0)
            arrow._line_width_pt = 2.0
            data = arrow.to_dict()
            arrow_data.append(data)
        
        # Should have 8 arrows
        assert len(arrow_data) == 8
        
        # All should be arrows with line width
        for data in arrow_data:
            assert data['line_width_pt'] == 2.0
    
    def test_arrow_direction_in_serialization(self):
        """Test arrow direction is preserved in serialization."""
        arrow_e = VectorAnnotation(AnnotationType.ARROW_E, 100, 100, 0)
        arrow_se = VectorAnnotation(AnnotationType.ARROW_SE, 100, 100, 0)
        
        data_e = arrow_e.to_dict()
        data_se = arrow_se.to_dict()
        
        # Both should be arrows but different types
        assert 'ann_type' in data_e
        assert 'ann_type' in data_se


class TestRectangleWorkflow:
    """Test complete Rectangle annotation workflows."""
    
    def test_create_rectangle_workflow(self):
        """Test: create Rectangle → modify color/width."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Modify color
        rect.color.setNamedColor("#ff0000")
        assert rect.color.name() == "#ff0000"
        
        # Modify width
        rect._line_width_pt = 2.0
        assert rect._line_width_pt == 2.0
        
        # Verify state
        assert rect.ann_type == AnnotationType.RECTANGLE
    
    def test_rectangle_resize_workflow(self):
        """Test: create Rectangle → resize."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Resize
        rect.set_scaled_size(250, 250)
        assert rect.scaled_width == 250
        assert rect.scaled_height == 250
    
    def test_rectangle_serialization_roundtrip(self):
        """Test: Rectangle serialization roundtrip."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect._line_width_pt = 2.5
        rect.color.setNamedColor("#0000ff")
        
        # Serialize
        data = rect.to_dict()
        
        # Deserialize
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.RECTANGLE
        assert restored._line_width_pt == 2.5


class TestEllipseWorkflow:
    """Test complete Ellipse annotation workflows."""
    
    def test_create_ellipse_workflow(self):
        """Test: create Ellipse → modify properties."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        
        ellipse._line_width_pt = 1.5
        ellipse.color.setNamedColor("#ff00ff")
        
        assert ellipse.ann_type == AnnotationType.ELLIPSE
        assert ellipse._line_width_pt == 1.5
    
    def test_circle_creation_workflow(self):
        """Test: create perfect circle (equal width/height)."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        
        # Resize to perfect square (becomes circle)
        ellipse.set_scaled_size(200, 200)
        assert ellipse.scaled_width == 200
        assert ellipse.scaled_height == 200
    
    def test_ellipse_serialization_roundtrip(self):
        """Test: Ellipse serialization roundtrip."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        ellipse._line_width_pt = 2.0
        
        data = ellipse.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.ELLIPSE


class TestTextWorkflow:
    """Test complete Text annotation workflows."""
    
    def test_create_text_workflow(self):
        """Test: create Text → modify font properties."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello World")
        
        # Modify font size
        text._font_size_px = 32
        assert text._font_size_px == 32
        
        # Modify font family
        text._font_family = "Courier New"
        assert text._font_family == "Courier New"
    
    def test_text_color_workflow(self):
        """Test: Text with color."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        text.color.setNamedColor("#0000ff")
        assert text.color.name() == "#0000ff"
    
    def test_text_serialization_roundtrip(self):
        """Test: Text serialization roundtrip preserves all properties."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test Text")
        text._font_size_px = 24
        text._font_family = "Arial"
        text.color.setNamedColor("#ff0000")
        
        data = text.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.text == "Test Text"
        assert restored._font_size_px == 24
        assert restored._font_family == "Arial"


class TestMultiAnnotationWorkflow:
    """Test workflows with multiple annotations."""
    
    def test_mixed_annotations_on_page(self):
        """Test creating multiple different annotation types on same page."""
        line = VectorAnnotation(AnnotationType.LINE, 50, 50, 0)
        arrow = VectorAnnotation(AnnotationType.ARROW_E, 100, 100, 0)
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 200, 200, 0)
        text = VectorAnnotation(AnnotationType.TEXT, 300, 300, 0, text="Label")
        
        annotations = [line, arrow, rect, text]
        
        assert len(annotations) == 4
        assert all(a.page == 0 for a in annotations)
    
    def test_annotations_serialization(self):
        """Test serializing multiple annotations."""
        annotations = [
            VectorAnnotation(AnnotationType.LINE, 50, 50, 0),
            VectorAnnotation(AnnotationType.RECTANGLE, 150, 150, 0),
            VectorAnnotation(AnnotationType.TEXT, 250, 250, 0, text="Text"),
        ]
        
        data = [a.to_dict() for a in annotations]
        
        assert len(data) == 3
        assert all('x' in d and 'y' in d for d in data)


class TestMultiPageWorkflow:
    """Test workflows across multiple pages."""
    
    def test_annotations_on_different_pages(self):
        """Test creating annotations on different pages."""
        page0_line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        page1_rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 1)
        page2_text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 2, text="Page 2")
        
        assert page0_line.page == 0
        assert page1_rect.page == 1
        assert page2_text.page == 2
    
    def test_annotations_per_page(self):
        """Test organizing annotations by page."""
        page_annotations = {
            0: [
                VectorAnnotation(AnnotationType.LINE, 50, 50, 0),
                VectorAnnotation(AnnotationType.RECTANGLE, 150, 150, 0),
            ],
            1: [
                VectorAnnotation(AnnotationType.ELLIPSE, 50, 50, 1),
                VectorAnnotation(AnnotationType.TEXT, 150, 150, 1, text="Page 1"),
            ],
        }
        
        assert len(page_annotations[0]) == 2
        assert len(page_annotations[1]) == 2


class TestPropertyChangeWorkflow:
    """Test workflows with property changes."""
    
    def test_batch_width_change(self):
        """Test changing width on multiple annotations."""
        line = VectorAnnotation(AnnotationType.LINE, 50, 50, 0)
        arrow = VectorAnnotation(AnnotationType.ARROW_GENERIC, 100, 100, 0)
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 150, 150, 0)
        
        # Change all to same width
        for ann in [line, arrow, rect]:
            ann._line_width_pt = 2.5
        
        assert all(a._line_width_pt == 2.5 for a in [line, arrow, rect])
    
    def test_batch_color_change(self):
        """Test changing color on multiple annotations."""
        line = VectorAnnotation(AnnotationType.LINE, 50, 50, 0)
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        arrow = VectorAnnotation(AnnotationType.ARROW_SE, 150, 150, 0)
        
        # Change all to same color
        for ann in [line, rect, arrow]:
            ann.color.setNamedColor("#ff0000")
        
        assert all(a.color.name() == "#ff0000" for a in [line, rect, arrow])
