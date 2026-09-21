"""Unit tests for new annotation types (Line, Arrow, Rectangle, Ellipse, Image)."""

from signer.objects import ARROW_TYPES, AnnotationType, VectorAnnotation


class TestLineAnnotation:
    """Test Line annotation type."""
    
    def test_line_creation(self):
        """Test creating a Line annotation."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line.ann_type == AnnotationType.LINE
        assert line.x == 100
        assert line.y == 100
        assert line.page == 0
    
    def test_line_has_width_property(self):
        """Test Line annotation has line_width_pt property."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert hasattr(line, '_line_width_pt')
        assert line._line_width_pt == 1.5  # Default
    
    def test_line_width_editable(self):
        """Test setting line width."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        assert line._line_width_pt == 2.5
    
    def test_line_serialization(self):
        """Test Line serialization to dict."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.0
        data = line.to_dict()
        
        assert data['x'] == 100
        assert data['y'] == 100
        assert data['line_width_pt'] == 2.0
        assert 'ann_type' in data or data.get('ann_type') == 'line'


class TestArrowAnnotation:
    """Test Arrow annotation (generic arrow pointing right)."""
    
    def test_arrow_creation(self):
        """Test creating arrow."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        assert arrow.ann_type == AnnotationType.ARROW
        assert arrow.x == 100
        assert arrow.y == 100
    
    def test_arrow_has_width(self):
        """Test arrow has line width."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        assert hasattr(arrow, '_line_width_pt')
        arrow._line_width_pt = 3.0
        assert arrow._line_width_pt == 3.0
    
    def test_arrow_in_arrow_types_set(self):
        """Test arrow is in ARROW_TYPES set."""
        assert AnnotationType.ARROW in ARROW_TYPES
        assert len(ARROW_TYPES) == 1  # Only one arrow type now
    
    def test_arrow_width_property(self):
        """Test arrow width property."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        assert hasattr(arrow, '_line_width_pt')
        arrow._line_width_pt = 2.5
        assert arrow._line_width_pt == 2.5


class TestRectangleAnnotation:
    """Test Rectangle annotation type."""
    
    def test_rectangle_creation(self):
        """Test creating Rectangle."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert rect.ann_type == AnnotationType.RECTANGLE
        assert rect.x == 100
        assert rect.y == 100
    
    def test_rectangle_has_width(self):
        """Test Rectangle has line width."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert hasattr(rect, '_line_width_pt')
        rect._line_width_pt = 2.0
        assert rect._line_width_pt == 2.0
    
    def test_rectangle_free_resize_support(self):
        """Test Rectangle supports free resizing."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert rect.supports_free_resize() is True
    
    def test_rectangle_serialization(self):
        """Test Rectangle serialization."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect._line_width_pt = 1.75
        data = rect.to_dict()
        
        assert data['x'] == 100
        assert data['y'] == 100
        assert data['line_width_pt'] == 1.75


class TestEllipseAnnotation:
    """Test Ellipse annotation type."""
    
    def test_ellipse_creation(self):
        """Test creating Ellipse."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert ellipse.ann_type == AnnotationType.ELLIPSE
        assert ellipse.x == 100
        assert ellipse.y == 100
    
    def test_ellipse_has_width(self):
        """Test Ellipse has line width."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert hasattr(ellipse, '_line_width_pt')
        ellipse._line_width_pt = 2.5
        assert ellipse._line_width_pt == 2.5
    
    def test_ellipse_free_resize_support(self):
        """Test Ellipse supports free resizing."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert ellipse.supports_free_resize() is True
    
    def test_ellipse_serialization(self):
        """Test Ellipse serialization."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        ellipse._line_width_pt = 1.5
        data = ellipse.to_dict()
        
        assert 'line_width_pt' in data


class TestTextAnnotation:
    """Test Text annotation with font properties."""
    
    def test_text_creation(self, qapp):
        """Test creating Text annotation."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello")
        assert text.ann_type == AnnotationType.TEXT
        assert text.text == "Hello"
        assert text.x == 100
    
    def test_text_has_font_size(self, qapp):
        """Test Text has font size property."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert hasattr(text, '_font_size_pt')
        assert isinstance(text._font_size_pt, (int, float))
    
    def test_text_has_font_family(self, qapp):
        """Test Text has font family property."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert hasattr(text, '_font_family')
        assert isinstance(text._font_family, str)
    
    def test_text_font_size_editable(self, qapp):
        """Test setting text font size."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 32
        assert text._font_size_pt == 32
    
    def test_text_font_family_editable(self, qapp):
        """Test setting text font family."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_family = "Courier New"
        assert text._font_family == "Courier New"


class TestAnnotationTypeProperties:
    """Test property availability across annotation types."""
    
    def test_line_width_only_on_vector_types(self):
        """Test line width available on all vector annotation types."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        
        for ann in [line, arrow, rect, ellipse]:
            assert hasattr(ann, '_line_width_pt')
    
    def test_font_size_only_on_text(self):
        """Test font size only available on Text."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        assert hasattr(text, '_font_size_pt')
        # Line should not have font_size_pt in to_dict
        data = line.to_dict()
        assert 'font_size_pt' not in data
    
    def test_font_family_only_on_text(self):
        """Test font family only available on Text."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        assert hasattr(text, '_font_family')
        data = line.to_dict()
        assert 'font_family' not in data


class TestBackwardCompatibility:
    """Test loading annotations without new properties."""
    
    def test_load_annotation_without_line_width(self):
        """Test loading old annotation format without line_width_pt."""
        data = {
            'type': 'VectorAnnotation',
            'x': 100,
            'y': 100,
            'base_width': 100,
            'base_height': 100,
            'scale': 1.0,
            'page': 0,
            'color': '#cc0000',
            'ann_type': 'line',
            # Missing line_width_pt
        }
        
        # Should load successfully with default width
        line = VectorAnnotation.from_dict(data)
        assert line.ann_type == AnnotationType.LINE
        assert line._line_width_pt == 1.5  # Default fallback


class TestAnnotationColorProperty:
    """Test color property on annotations."""
    
    def test_line_has_color(self):
        """Test Line annotation has color."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line.color is not None
        assert hasattr(line.color, 'name')
    
    def test_arrow_has_color(self):
        """Test Arrow annotation has color."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        assert arrow.color is not None
    
    def test_rectangle_has_color(self):
        """Test Rectangle annotation has color."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert rect.color is not None
    
    def test_ellipse_has_color(self):
        """Test Ellipse annotation has color."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert ellipse.color is not None
    
    def test_color_change(self):
        """Test changing annotation color."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        original = line.color.name()
        line.color.setNamedColor("#0000ff")
        assert line.color.name() != original
        assert line.color.name() == "#0000ff"
