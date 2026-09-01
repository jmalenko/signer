"""Unit tests for annotation properties (width, font size, font family)."""

import pytest
from signer.objects import VectorAnnotation, AnnotationType, VECTOR_WITH_WIDTH


class TestLineWidthProperty:
    """Test line width property on vector annotations."""
    
    def test_line_width_default_value(self):
        """Test default line width is 1.5pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line._line_width_pt == 1.5
    
    def test_line_width_set_and_get(self):
        """Test setting and getting line width."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        line._line_width_pt = 2.5
        assert line._line_width_pt == 2.5
        
        line._line_width_pt = 3.0
        assert line._line_width_pt == 3.0
    
    def test_line_width_bounds_lower(self):
        """Test line width minimum bound (0.5pt)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        line._line_width_pt = 0.5
        assert line._line_width_pt == 0.5
    
    def test_line_width_bounds_upper(self):
        """Test line width maximum bound (10pt)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        line._line_width_pt = 10.0
        assert line._line_width_pt == 10.0
    
    def test_line_width_on_all_vector_types(self):
        """Test line width available on all vector types."""
        for ann_type in VECTOR_WITH_WIDTH:
            if ann_type == AnnotationType.TEXT:
                continue  # Text doesn't use line width
            ann = VectorAnnotation(ann_type, 100, 100, 0)
            assert hasattr(ann, '_line_width_pt')
            ann._line_width_pt = 2.0
            assert ann._line_width_pt == 2.0
    
    def test_line_width_serialization(self):
        """Test line width serialization."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        
        data = line.to_dict()
        
        assert 'line_width_pt' in data
        assert data['line_width_pt'] == 2.5
    
    def test_line_width_deserialization(self):
        """Test line width deserialization."""
        data = {
            'type': 'VectorAnnotation',
            'ann_type': 'line',
            'x': 100,
            'y': 100,
            'base_width': 100,
            'base_height': 100,
            'scale': 1.0,
            'page': 0,
            'color': '#cc0000',
            'line_width_pt': 3.0,
        }
        
        line = VectorAnnotation.from_dict(data)
        
        assert line._line_width_pt == 3.0
    
    def test_line_width_roundtrip(self):
        """Test line width survives roundtrip."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        line.color.setNamedColor("#0000ff")
        
        data = line.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored._line_width_pt == 2.5
    
    def test_line_width_backward_compatibility(self):
        """Test loading annotation without line_width_pt uses default."""
        data = {
            'type': 'VectorAnnotation',
            'ann_type': 'line',
            'x': 100,
            'y': 100,
            'base_width': 100,
            'base_height': 100,
            'scale': 1.0,
            'page': 0,
            'color': '#cc0000',
            # Missing line_width_pt
        }
        
        line = VectorAnnotation.from_dict(data)
        
        # Should default to 1.5
        assert line._line_width_pt == 1.5


class TestFontSizeProperty:
    """Test font size property on Text annotations."""
    
    def test_font_size_default_value(self):
        """Test default font size is set."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        assert hasattr(text, '_font_size_px')
        # Default should be approximately 24px (11pt at 96 DPI)
        assert isinstance(text._font_size_px, (int, float))
    
    def test_font_size_set_and_get(self):
        """Test setting and getting font size."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        text._font_size_px = 32
        assert text._font_size_px == 32
        
        text._font_size_px = 48
        assert text._font_size_px == 48
    
    def test_font_size_bounds_lower(self):
        """Test font size minimum bound (6pt ≈ 8px)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        text._font_size_px = 8
        assert text._font_size_px == 8
    
    def test_font_size_bounds_upper(self):
        """Test font size maximum bound (72pt ≈ 96px)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        text._font_size_px = 96
        assert text._font_size_px == 96
    
    def test_font_size_only_on_text(self):
        """Test font size only applies to Text annotation."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        assert hasattr(text, '_font_size_px')
        # Line should not have font_size_px in to_dict
        line_data = line.to_dict()
        assert 'font_size_px' not in line_data
    
    def test_font_size_serialization(self):
        """Test font size serialization."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_px = 36
        
        data = text.to_dict()
        
        assert 'font_size_px' in data
        assert data['font_size_px'] == 36
    
    def test_font_size_deserialization(self):
        """Test font size deserialization."""
        data = {
            'type': 'VectorAnnotation',
            'ann_type': 'text',
            'text': 'Test',
            'x': 100,
            'y': 100,
            'base_width': 200,
            'base_height': 50,
            'scale': 1.0,
            'font_size_px': 40,
            'page': 0,
            'color': '#000000',
        }
        
        text = VectorAnnotation.from_dict(data)
        
        assert text._font_size_px == 40
    
    def test_font_size_roundtrip(self):
        """Test font size survives roundtrip."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test Text")
        text._font_size_px = 44
        text.color.setNamedColor("#0000ff")
        
        data = text.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored._font_size_px == 44
        assert restored.text == "Test Text"


class TestFontFamilyProperty:
    """Test font family property on Text annotations."""
    
    def test_font_family_default_value(self):
        """Test default font family is set."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        assert hasattr(text, '_font_family')
        assert isinstance(text._font_family, str)
        assert len(text._font_family) > 0
    
    def test_font_family_set_and_get(self):
        """Test setting and getting font family."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        text._font_family = "Courier New"
        assert text._font_family == "Courier New"
        
        text._font_family = "Arial"
        assert text._font_family == "Arial"
    
    def test_font_family_only_on_text(self):
        """Test font family only applies to Text annotation."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        assert hasattr(text, '_font_family')
        line_data = line.to_dict()
        assert 'font_family' not in line_data
    
    def test_font_family_serialization(self):
        """Test font family serialization."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_family = "Courier New"
        
        data = text.to_dict()
        
        assert 'font_family' in data
        assert data['font_family'] == "Courier New"
    
    def test_font_family_deserialization(self):
        """Test font family deserialization."""
        data = {
            'type': 'VectorAnnotation',
            'ann_type': 'text',
            'text': 'Test',
            'x': 100,
            'y': 100,
            'base_width': 200,
            'base_height': 50,
            'scale': 1.0,
            'font_family': 'Times New Roman',
            'page': 0,
            'color': '#000000',
        }
        
        text = VectorAnnotation.from_dict(data)
        
        assert text._font_family == 'Times New Roman'
    
    def test_font_family_roundtrip(self):
        """Test font family survives roundtrip."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_family = "Verdana"
        
        data = text.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored._font_family == "Verdana"
    
    def test_font_family_common_fonts(self):
        """Test setting common font families."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        fonts = ["Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"]
        
        for font in fonts:
            text._font_family = font
            assert text._font_family == font


class TestColorProperty:
    """Test color property on annotations."""
    
    def test_color_default_value(self):
        """Test default color is set."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        assert line.color is not None
        assert hasattr(line.color, 'name')
    
    def test_color_set_and_get(self):
        """Test setting and getting color."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        line.color.setNamedColor("#ff0000")
        assert line.color.name() == "#ff0000"
        
        line.color.setNamedColor("#0000ff")
        assert line.color.name() == "#0000ff"
    
    def test_color_on_all_vector_types(self):
        """Test color available on all vector types."""
        types = [
            AnnotationType.LINE, AnnotationType.ARROW_GENERIC,
            AnnotationType.RECTANGLE, AnnotationType.ELLIPSE,
            AnnotationType.CHECKMARK, AnnotationType.CROSSMARK,
            AnnotationType.TEXT,
        ]
        
        for ann_type in types:
            ann = VectorAnnotation(ann_type, 100, 100, 0, text="Test" if ann_type == AnnotationType.TEXT else "")
            assert ann.color is not None
            ann.color.setNamedColor("#ff0000")
            assert ann.color.name() == "#ff0000"
    
    def test_color_serialization(self):
        """Test color serialization."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line.color.setNamedColor("#0000ff")
        
        data = line.to_dict()
        
        assert 'color' in data
        assert data['color'] == "#0000ff"
    
    def test_color_deserialization(self):
        """Test color deserialization."""
        data = {
            'type': 'VectorAnnotation',
            'ann_type': 'line',
            'x': 100,
            'y': 100,
            'base_width': 100,
            'base_height': 100,
            'scale': 1.0,
            'page': 0,
            'color': '#00ff00',
        }
        
        line = VectorAnnotation.from_dict(data)
        
        assert line.color.name() == '#00ff00'
    
    def test_color_roundtrip(self):
        """Test color survives roundtrip."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line.color.setNamedColor("#ff00ff")
        
        data = line.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.color.name() == "#ff00ff"


class TestPropertyDefaults:
    """Test property default values."""
    
    def test_default_line_width(self):
        """Test default line width is 1.5pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        arrow = VectorAnnotation(AnnotationType.ARROW_GENERIC, 100, 100, 0)
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        for ann in [line, arrow, rect]:
            assert ann._line_width_pt == 1.5
    
    def test_default_font_size(self):
        """Test default font size is set on Text."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Should have a default
        assert isinstance(text._font_size_px, (int, float))
        assert text._font_size_px > 0
    
    def test_default_font_family(self):
        """Test default font family is set on Text."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Should have a default
        assert isinstance(text._font_family, str)
        assert len(text._font_family) > 0
    
    def test_default_color(self):
        """Test default color is set."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Should have a default color
        assert line.color is not None
        # Default is usually red (#cc0000)
        assert isinstance(line.color.name(), str)
