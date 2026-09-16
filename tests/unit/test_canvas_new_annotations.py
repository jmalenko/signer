"""Unit tests for canvas interactions with new annotation types."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor
from signer.objects import VectorAnnotation, AnnotationType
from signer.canvas import DocumentCanvas
import math


class TestCanvasAnnotationCreation:
    """Test creating new annotation types on canvas."""
    
    def test_create_line_annotation(self, qtbot):
        """Test creating Line on canvas."""
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        
        # Create line
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line.ann_type == AnnotationType.LINE
        assert line._line_width_pt == 1.5
    
    def test_create_arrow(self, qtbot):
        """Test creating Arrow on canvas."""
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        assert arrow.ann_type == AnnotationType.ARROW
        assert hasattr(arrow, '_line_width_pt')
    
    def test_create_rectangle(self, qtbot):
        """Test creating Rectangle on canvas."""
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert rect.ann_type == AnnotationType.RECTANGLE
        assert rect.supports_free_resize() is True
    
    def test_create_ellipse(self, qtbot):
        """Test creating Ellipse on canvas."""
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert ellipse.ann_type == AnnotationType.ELLIPSE
        assert ellipse.supports_free_resize() is True
    
    def test_create_text(self, qtbot):
        """Test creating Text annotation."""
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello")
        assert text.ann_type == AnnotationType.TEXT
        assert text.text == "Hello"
        assert text.supports_free_resize() is True


class TestAnnotationProperties:
    """Test properties are correctly managed."""
    
    def test_line_width_range(self):
        """Test line width within valid range."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Test minimum
        line._line_width_pt = 0.5
        assert line._line_width_pt == 0.5
        
        # Test maximum
        line._line_width_pt = 10.0
        assert line._line_width_pt == 10.0
        
        # Test mid-range
        line._line_width_pt = 2.5
        assert line._line_width_pt == 2.5
    
    def test_font_size_range(self):
        """Test font size within valid range."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Test minimum (6pt ≈ 8px at 96 DPI)
        text._font_size_pt = 8
        assert text._font_size_pt == 8
        
        # Test maximum (72pt ≈ 96px)
        text._font_size_pt = 96
        assert text._font_size_pt == 96
        
        # Test mid-range
        text._font_size_pt = 32
        assert text._font_size_pt == 32
    
    def test_font_family_common_fonts(self):
        """Test setting common font families."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        fonts = ["Arial", "Times New Roman", "Courier New", "Verdana"]
        for font in fonts:
            text._font_family = font
            assert text._font_family == font
    
    def test_color_property(self):
        """Test color property on vector annotations."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Default color
        assert line.color is not None
        
        # Change color
        line.color.setNamedColor("#ff0000")
        assert line.color.name() == "#ff0000"
        
        # Change again
        line.color.setNamedColor("#0000ff")
        assert line.color.name() == "#0000ff"


class TestAnnotationResizing:
    """Test resizing annotations."""
    
    def test_line_set_scaled_size(self):
        """Test resizing Line."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Set new size
        line.set_scaled_size(300, 200)
        assert line.scaled_width == 300
        assert line.scaled_height == 200
    
    def test_rectangle_set_scaled_size(self):
        """Test resizing Rectangle."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        original_x = rect.x
        original_y = rect.y
        
        # Resize
        rect.set_scaled_size(250, 250)
        assert rect.scaled_width == 250
        assert rect.scaled_height == 250
    
    def test_ellipse_set_scaled_size(self):
        """Test resizing Ellipse."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        
        # Resize to perfect circle
        ellipse.set_scaled_size(200, 200)
        assert ellipse.scaled_width == 200
        assert ellipse.scaled_height == 200
    
    def test_text_set_scaled_size(self):
        """Test resizing Text annotation."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello World")
        
        # Resize text box
        text.set_scaled_size(300, 100)
        assert text.scaled_width == 300
        assert text.scaled_height == 100
    
    def test_minimum_size_enforced(self):
        """Test minimum size is enforced."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Try to set very small size
        line.set_scaled_size(2, 2)
        # Should be clamped to minimum (8.0)
        assert line.scaled_width >= 8.0
        assert line.scaled_height >= 8.0


class TestHandleDetection:
    """Test handle detection for resizing."""
    
    def test_handle_count(self):
        """Test line annotation has endpoint handles."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Get handle rects
        handles = line.handle_rects_viewport(100, 100, 200, 150)
        assert len(handles) == 2
    
    def test_corner_handles(self):
        """Test corner handle positions."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Get handles
        handles = rect.handle_rects_viewport(100, 100, 200, 150)
        
        # Corners: TL(0), TR(2), BL(5), BR(7)
        # Edges: T(1), L(3), R(4), B(6)
        assert len(handles) == 8
        
        # Verify corner positions (approximately)
        # TL (0) at (100, 100)
        assert handles[0].x() < 110
        assert handles[0].y() < 110
        
        # BR (7) at (300, 250)
        assert handles[7].x() > 290
        assert handles[7].y() > 240


class TestAnnotationMovement:
    """Test moving annotations."""
    
    def test_move_line(self):
        """Test moving Line annotation."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Move
        line.x = 150
        line.y = 200
        
        assert line.x == 150
        assert line.y == 200
    
    def test_move_arrow(self):
        """Test moving Arrow annotation."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        
        arrow.x = 250
        arrow.y = 150
        
        assert arrow.x == 250
        assert arrow.y == 150
    
    def test_move_rectangle(self):
        """Test moving Rectangle annotation."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        rect.x = 200
        rect.y = 300
        
        assert rect.x == 200
        assert rect.y == 300


class TestAnnotationSerialization:
    """Test serialization of new annotation types."""
    
    def test_line_roundtrip(self):
        """Test Line serialization and deserialization."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        line.color.setNamedColor("#0000ff")
        
        # Serialize
        data = line.to_dict()
        
        # Deserialize
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.LINE
        assert restored.x == 100
        assert restored.y == 100
    
    def test_arrow_roundtrip(self):
        """Test Arrow serialization and deserialization."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        arrow._line_width_pt = 3.0
        
        data = arrow.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.ARROW
        assert restored.x == 100
    
    def test_rectangle_roundtrip(self):
        """Test Rectangle serialization and deserialization."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect._line_width_pt = 1.5
        rect.color.setNamedColor("#ff0000")
        
        data = rect.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.RECTANGLE
        assert restored.x == 100
    
    def test_ellipse_roundtrip(self):
        """Test Ellipse serialization and deserialization."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        ellipse._line_width_pt = 2.0
        
        data = ellipse.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.ELLIPSE
    
    def test_text_roundtrip(self):
        """Test Text serialization and deserialization."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello World")
        text._font_size_pt = 32
        text._font_family = "Courier New"
        
        data = text.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.TEXT
        assert restored.text == "Hello World"
        assert restored._font_size_pt == 32
        assert restored._font_family == "Courier New"
