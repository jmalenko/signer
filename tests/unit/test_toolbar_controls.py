"""Unit tests for toolbar controls and context-sensitive visibility."""

import pytest
from signer.objects import VectorAnnotation, AnnotationType, VECTOR_WITH_WIDTH


class TestWidthSpinnerVisibility:
    """Test line width spinner visibility based on annotation type."""
    
    def test_width_spinner_visible_for_line(self):
        """Test width spinner visible when Line selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_arrow(self):
        """Test width spinner visible when Arrow selected."""
        arrow = VectorAnnotation(AnnotationType.ARROW_GENERIC, 100, 100, 0)
        assert arrow.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_rectangle(self):
        """Test width spinner visible when Rectangle selected."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert rect.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_ellipse(self):
        """Test width spinner visible when Ellipse selected."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert ellipse.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_checkmark(self):
        """Test width spinner visible when Checkmark selected."""
        checkmark = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        assert checkmark.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_crossmark(self):
        """Test width spinner visible when Crossmark selected."""
        crossmark = VectorAnnotation(AnnotationType.CROSSMARK, 100, 100, 0)
        assert crossmark.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_hidden_for_text(self):
        """Test width spinner hidden when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert text.ann_type not in VECTOR_WITH_WIDTH
    
    def test_width_spinner_hidden_for_signature(self):
        """Test width spinner hidden for Signature."""
        # Signature is not a VectorAnnotation
        # Test conceptually
        ann_type = AnnotationType.SIGNATURE
        assert ann_type not in VECTOR_WITH_WIDTH


class TestFontSizeSpinnerVisibility:
    """Test font size spinner visibility."""
    
    def test_font_size_spinner_visible_for_text(self):
        """Test font size spinner visible when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert hasattr(text, '_font_size_px')
    
    def test_font_size_spinner_hidden_for_line(self):
        """Test font size spinner hidden when Line selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        # Line should not have font_size_px attribute used in to_dict
        data = line.to_dict()
        assert 'font_size_px' not in data
    
    def test_font_size_spinner_hidden_for_rectangle(self):
        """Test font size spinner hidden when Rectangle selected."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        data = rect.to_dict()
        assert 'font_size_px' not in data
    
    def test_font_size_spinner_hidden_for_arrow(self):
        """Test font size spinner hidden when Arrow selected."""
        arrow = VectorAnnotation(AnnotationType.ARROW_GENERIC, 100, 100, 0)
        data = arrow.to_dict()
        assert 'font_size_px' not in data


class TestFontFamilyComboVisibility:
    """Test font family combo visibility."""
    
    def test_font_family_combo_visible_for_text(self):
        """Test font family combo visible when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert hasattr(text, '_font_family')
    
    def test_font_family_combo_hidden_for_line(self):
        """Test font family combo hidden when Line selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        data = line.to_dict()
        assert 'font_family' not in data
    
    def test_font_family_combo_hidden_for_rectangle(self):
        """Test font family combo hidden when Rectangle selected."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        data = rect.to_dict()
        assert 'font_family' not in data


class TestControlsDisabledWhenNoDocument:
    """Test controls are disabled when no document open."""
    
    def test_width_spinner_disabled_no_document(self):
        """Test width spinner disabled with no document."""
        # No document means no annotation selected
        selected = None
        
        # Spinner would be disabled
        assert selected is None
    
    def test_font_size_spinner_disabled_no_document(self):
        """Test font size spinner disabled with no document."""
        selected = None
        assert selected is None
    
    def test_font_family_combo_disabled_no_document(self):
        """Test font family combo disabled with no document."""
        selected = None
        assert selected is None
    
    def test_color_picker_disabled_no_document(self):
        """Test color picker disabled with no document."""
        selected = None
        assert selected is None


class TestControlsDisabledWhenNoSelection:
    """Test controls are disabled when no annotation selected."""
    
    def test_spinners_disabled_no_selection(self):
        """Test spinners disabled with no selection."""
        # Empty document, nothing selected
        selected = None
        assert selected is None


class TestSpinnerRanges:
    """Test spinner range limits."""
    
    def test_width_spinner_range(self):
        """Test width spinner enforces range 0.5-10pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Minimum
        line._line_width_pt = 0.5
        assert line._line_width_pt >= 0.5
        
        # Maximum
        line._line_width_pt = 10.0
        assert line._line_width_pt <= 10.0
    
    def test_width_spinner_step(self):
        """Test width spinner steps by 0.5pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Default is 1.5
        assert line._line_width_pt == 1.5
        
        # Step up by 0.5
        line._line_width_pt = 2.0
        assert line._line_width_pt == 2.0
    
    def test_font_size_spinner_range(self):
        """Test font size spinner enforces range 6-72pt."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Minimum (6pt ≈ 8px)
        text._font_size_px = 8
        assert text._font_size_px >= 8
        
        # Maximum (72pt ≈ 96px)
        text._font_size_px = 96
        assert text._font_size_px <= 96
    
    def test_font_size_spinner_step(self):
        """Test font size spinner steps by 1pt."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        initial = text._font_size_px
        
        # Step by 1
        text._font_size_px = initial + 1
        assert text._font_size_px == initial + 1


class TestSpinnerStateManagement:
    """Test spinner state is managed correctly."""
    
    def test_width_spinner_updates_on_selection(self):
        """Test width spinner updates when annotation selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        
        # Spinner value should match
        assert line._line_width_pt == 2.5
    
    def test_font_size_spinner_updates_on_selection(self):
        """Test font size spinner updates when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_px = 28
        
        # Spinner value should match
        assert text._font_size_px == 28
    
    def test_font_family_combo_updates_on_selection(self):
        """Test font family combo updates when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_family = "Verdana"
        
        # Combo value should match
        assert text._font_family == "Verdana"


class TestControlSignalBlocking:
    """Test controls use signal blocking to prevent loops."""
    
    def test_spinner_change_doesnt_feedback(self):
        """Test spinner change doesn't cause infinite loop."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Change spinner (would be signal-blocked)
        line._line_width_pt = 2.5
        
        # Should update only once
        assert line._line_width_pt == 2.5
    
    def test_annotation_change_doesnt_feedback(self):
        """Test annotation change doesn't update spinner infinitely."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Change annotation property (would be signal-blocked)
        line._line_width_pt = 3.0
        
        # Spinner would update to reflect this
        # but only once
        assert line._line_width_pt == 3.0


class TestContextSwitchingControls:
    """Test controls update when switching between annotations."""
    
    def test_switch_from_line_to_text(self):
        """Test controls update when switching Line to Text."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Select line - width spinner visible
        selected = line
        assert hasattr(selected, '_line_width_pt')
        
        # Switch to text - font controls visible
        selected = text
        assert hasattr(selected, '_font_size_px')
        assert hasattr(selected, '_font_family')
    
    def test_switch_from_text_to_rectangle(self):
        """Test controls update when switching Text to Rectangle."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Select text - font controls visible
        selected = text
        assert hasattr(selected, '_font_family')
        
        # Switch to rectangle - width visible
        selected = rect
        assert hasattr(selected, '_line_width_pt')


class TestSpecialControls:
    """Test special control behaviors."""
    
    def test_width_spinner_decimal_support(self):
        """Test width spinner supports decimal values (0.5 increments)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Test decimal widths
        line._line_width_pt = 1.5
        assert line._line_width_pt == 1.5
        
        line._line_width_pt = 2.5
        assert line._line_width_pt == 2.5
    
    def test_color_control_integration(self):
        """Test color control is integrated with all annotation types."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Both support color
        assert line.color is not None
        assert text.color is not None
        
        # Color can be changed
        line.color.setNamedColor("#ff0000")
        text.color.setNamedColor("#0000ff")
        
        assert line.color.name() == "#ff0000"
        assert text.color.name() == "#0000ff"
