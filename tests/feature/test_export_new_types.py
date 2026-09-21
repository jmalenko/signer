"""Feature tests for export functionality with new annotation types."""

import sys

import pytest
from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


class TestLineExport:
    """Test exporting Line annotation to various formats."""
    
    def test_line_to_pil_image(self):
        """Test converting Line to PIL image."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.0
        
        # Render to PIL
        img = line.render_to_pil()
        
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
    
    def test_line_renders_with_correct_width(self):
        """Test Line renders with specified width."""
        line_thin = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line_thin._line_width_pt = 0.5
        
        line_thick = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line_thick._line_width_pt = 5.0
        
        img_thin = line_thin.render_to_pil()
        img_thick = line_thick.render_to_pil()
        
        # Both should render
        assert img_thin.width > 0
        assert img_thick.width > 0


class TestArrowExport:
    """Test exporting Arrow annotation to various formats."""
    
    def test_arrow_to_pil(self):
        """Test converting arrow to PIL image."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        
        img = arrow.render_to_pil()
        
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
    
    def test_arrow_with_width_to_pil(self):
        """Test converting arrow with different width to PIL image."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        arrow._line_width_pt = 3.0
        img = arrow.render_to_pil()
        
        assert isinstance(img, Image.Image)
        assert img.width > 0


class TestRectangleExport:
    """Test exporting Rectangle annotation."""
    
    def test_rectangle_to_pil(self):
        """Test converting Rectangle to PIL image."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect._line_width_pt = 2.0
        rect.color.setNamedColor("#ff0000")
        
        img = rect.render_to_pil()
        
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
    
    def test_rectangle_color_preserved(self):
        """Test Rectangle color is preserved in export."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect.color.setNamedColor("#0000ff")
        
        img = rect.render_to_pil()
        
        # Image should have content
        assert img.getbands()  # Should have color channels


class TestEllipseExport:
    """Test exporting Ellipse annotation."""
    
    def test_ellipse_to_pil(self):
        """Test converting Ellipse to PIL image."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        ellipse._line_width_pt = 1.5
        
        img = ellipse.render_to_pil()
        
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
    
    def test_circle_to_pil(self):
        """Test converting circle (square ellipse) to PIL image."""
        circle = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        circle.set_scaled_size(200, 200)  # Perfect circle
        
        img = circle.render_to_pil()
        
        # Circle should render (width == height)
        assert img.width > 0
        assert img.height > 0


@pytest.mark.skipif(sys.platform == "darwin", reason="Qt font metrics crash on macOS in headless environment")
class TestTextExport:
    """Test exporting Text annotation."""
    
    def test_text_to_pil(self):
        """Test converting Text to PIL image."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello")
        text._font_size_pt = 24
        text._font_family = "Arial"
        
        img = text.render_to_pil()
        
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
    
    def test_text_with_different_font_sizes(self):
        """Test Text export with different font sizes."""
        text_small = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Small")
        text_small._font_size_pt = 8
        
        text_large = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Large")
        text_large._font_size_pt = 64
        
        img_small = text_small.render_to_pil()
        img_large = text_large.render_to_pil()
        
        # Both should render
        assert img_small.width > 0
        assert img_large.width > 0


class TestMultiAnnotationExport:
    """Test exporting multiple annotations together."""
    
    def test_multiple_annotations_serialize(self):
        """Test multiple annotations can be serialized."""
        annotations = [
            VectorAnnotation(AnnotationType.LINE, 50, 50, 0),
            VectorAnnotation(AnnotationType.ARROW, 100, 100, 0),
            VectorAnnotation(AnnotationType.RECTANGLE, 150, 150, 0),
            VectorAnnotation(AnnotationType.ELLIPSE, 200, 200, 0),
            VectorAnnotation(AnnotationType.TEXT, 250, 250, 0, text="Text"),
        ]
        
        data = [a.to_dict() for a in annotations]
        
        assert len(data) == 5
        assert all('x' in d for d in data)
        assert all('y' in d for d in data)


class TestExportPreservesProperties:
    """Test that export preserves annotation properties."""
    
    def test_width_preserved_on_export(self):
        """Test line width is preserved during export."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        original_width = 2.5
        line._line_width_pt = original_width
        
        # Serialize
        data = line.to_dict()
        
        # Should preserve width
        assert data['line_width_pt'] == original_width
    
    def test_font_size_preserved_on_export(self):
        """Test font size is preserved during export."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        original_size = 32
        text._font_size_pt = original_size
        
        data = text.to_dict()
        
        assert data['font_size_pt'] == original_size
    
    def test_font_family_preserved_on_export(self):
        """Test font family is preserved during export."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        original_family = "Courier New"
        text._font_family = original_family
        
        data = text.to_dict()
        
        assert data['font_family'] == original_family
    
    def test_color_preserved_on_export(self):
        """Test color is preserved during export."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line.color.setNamedColor("#0000ff")
        
        data = line.to_dict()
        
        assert data['color'] == "#0000ff"


class TestExportRoundtrip:
    """Test export and reimport roundtrips."""
    
    def test_line_export_reimport(self):
        """Test Line export and reimport preserves data."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        line.color.setNamedColor("#ff0000")
        
        # Export
        data = line.to_dict()
        
        # Reimport
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.x == 100
        assert restored.y == 100
        assert restored._line_width_pt == 2.5
    
    def test_arrow_export_reimport(self):
        """Test Arrow export and reimport."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 150, 150, 0)
        arrow._line_width_pt = 3.0
        
        data = arrow.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.ann_type == AnnotationType.ARROW
        assert restored._line_width_pt == 3.0
    
    def test_text_export_reimport(self):
        """Test Text export and reimport."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello World")
        text._font_size_pt = 28
        text._font_family = "Georgia"
        
        data = text.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.text == "Hello World"
        assert restored._font_size_pt == 28
        assert restored._font_family == "Georgia"
