"""Feature tests for export functionality with new annotation types."""

from signer.objects import AnnotationType, VectorAnnotation
from tests.utils.test_helpers import export_to_page


def ink_bbox(annotation: VectorAnnotation):
    """Bounding box of everything the annotation paints when exported onto a page."""
    return export_to_page(annotation).getchannel("A").getbbox()


def ink_amount(annotation: VectorAnnotation) -> int:
    return sum(export_to_page(annotation).getchannel("A").getdata())


class TestLineExport:
    """Test exporting Line annotation."""

    def test_line_is_exported(self):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.0

        assert ink_bbox(line) is not None

    def test_line_exports_with_correct_width(self):
        line_thin = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line_thin._line_width_pt = 0.5

        line_thick = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line_thick._line_width_pt = 5.0

        assert ink_amount(line_thick) > ink_amount(line_thin) > 0


class TestArrowExport:
    """Test exporting Arrow annotation."""

    def test_arrow_is_exported(self):
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)

        assert ink_bbox(arrow) is not None

    def test_arrow_with_width_is_exported_thicker(self):
        thin = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        thick = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        thick._line_width_pt = 3.0

        assert ink_amount(thick) > ink_amount(thin) > 0


class TestRectangleExport:
    """Test exporting Rectangle annotation."""

    def test_rectangle_is_exported(self):
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect._line_width_pt = 2.0
        rect.color.setNamedColor("#ff0000")

        assert ink_bbox(rect) is not None

    def test_rectangle_color_preserved(self):
        """Test Rectangle color is preserved in export."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect.color.setNamedColor("#0000ff")

        page = export_to_page(rect)
        opaque = [pixel for pixel in page.getdata() if pixel[3] == 255]

        assert opaque
        assert all(pixel[:3] == (0, 0, 255) for pixel in opaque)


class TestEllipseExport:
    """Test exporting Ellipse annotation."""

    def test_ellipse_is_exported(self):
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        ellipse._line_width_pt = 1.5

        assert ink_bbox(ellipse) is not None

    def test_circle_is_exported_as_a_circle(self):
        """Test a square ellipse is exported with equal width and height."""
        circle = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        circle.set_scaled_size(200, 200)

        left, top, right, bottom = ink_bbox(circle)

        assert abs((right - left) - (bottom - top)) <= 1


class TestTextExport:
    """Test exporting Text annotation."""

    def test_text_is_exported(self, qapp):
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello")
        text._font_size_pt = 24
        text._font_family = "Arial"

        assert ink_bbox(text) is not None

    def test_text_with_different_font_sizes(self, qapp):
        """Test Text export with different font sizes."""
        text_small = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Small")
        text_small._font_size_pt = 8

        text_large = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Large")
        text_large._font_size_pt = 64

        assert ink_amount(text_large) > ink_amount(text_small) > 0


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
