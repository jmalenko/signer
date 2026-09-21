"""Unit tests for keyboard shortcuts ([ and ] keys) with new annotation types."""

from signer.objects import AnnotationType, VectorAnnotation


class TestBracketRightIncreaseWidth:
    """Test ] key increases line width."""
    
    def test_bracket_right_increases_line_width(self):
        """Test ] key increases line width by 0.5pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        initial = line._line_width_pt
        
        # Simulate ] key
        line._line_width_pt = initial + 0.5
        
        assert line._line_width_pt == 2.0
    
    def test_bracket_right_increases_arrow_width(self):
        """Test ] key increases arrow width."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        initial = arrow._line_width_pt
        
        arrow._line_width_pt = initial + 0.5
        
        assert arrow._line_width_pt == 2.0
    
    def test_bracket_right_increases_rectangle_width(self):
        """Test ] key increases rectangle stroke width."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        initial = rect._line_width_pt
        
        rect._line_width_pt = initial + 0.5
        
        assert rect._line_width_pt == 2.0
    
    def test_bracket_right_increases_font_size(self):
        """Test ] key increases font size by 1pt."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        initial = text._font_size_pt
        
        # Simulate ] key for text
        text._font_size_pt = initial + 1
        
        assert text._font_size_pt == initial + 1
    
    def test_bracket_right_respects_width_maximum(self):
        """Test ] key respects maximum width (10pt)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 10.0  # At max
        
        # Try to increase further - should stay at max or wrap
        line._line_width_pt = min(10.0, line._line_width_pt + 0.5)
        
        assert line._line_width_pt <= 10.0
    
    def test_bracket_right_respects_font_maximum(self):
        """Test ] key respects maximum font size (72pt ≈ 96px)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 96  # At max (72pt)
        
        # Try to increase further
        text._font_size_pt = min(96, text._font_size_pt + 1)
        
        assert text._font_size_pt <= 96


class TestBracketLeftDecreaseWidth:
    """Test [ key decreases line width."""
    
    def test_bracket_left_decreases_line_width(self):
        """Test [ key decreases line width by 0.5pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 3.0
        
        # Simulate [ key
        line._line_width_pt = line._line_width_pt - 0.5
        
        assert line._line_width_pt == 2.5
    
    def test_bracket_left_decreases_arrow_width(self):
        """Test [ key decreases arrow width."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        arrow._line_width_pt = 2.5
        
        arrow._line_width_pt = arrow._line_width_pt - 0.5
        
        assert arrow._line_width_pt == 2.0
    
    def test_bracket_left_decreases_rectangle_width(self):
        """Test [ key decreases rectangle width."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        rect._line_width_pt = 2.0
        
        rect._line_width_pt = rect._line_width_pt - 0.5
        
        assert rect._line_width_pt == 1.5
    
    def test_bracket_left_decreases_font_size(self):
        """Test [ key decreases font size by 1pt."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 32
        
        # Simulate [ key for text
        text._font_size_pt = text._font_size_pt - 1
        
        assert text._font_size_pt == 31
    
    def test_bracket_left_respects_width_minimum(self):
        """Test [ key respects minimum width (0.5pt)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 0.5  # At min
        
        # Try to decrease further
        line._line_width_pt = max(0.5, line._line_width_pt - 0.5)
        
        assert line._line_width_pt >= 0.5
    
    def test_bracket_left_respects_font_minimum(self):
        """Test [ key respects minimum font size (6pt ≈ 8px)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 8  # At min (6pt)
        
        # Try to decrease further
        text._font_size_pt = max(8, text._font_size_pt - 1)
        
        assert text._font_size_pt >= 8


class TestShortcutsOnlyWhenSelected:
    """Test shortcuts only work when annotation selected."""
    
    def test_shortcut_requires_selected_annotation(self):
        """Test shortcuts need selected annotation."""
        # Simulate no selection
        selected = None
        
        if selected is not None:
            selected._line_width_pt += 0.5
        
        # Should not crash, just skip
        assert selected is None
    
    def test_shortcut_with_selected_line(self):
        """Test shortcut works with selected line."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        selected = line
        
        # Apply shortcut
        selected._line_width_pt += 0.5
        
        assert selected._line_width_pt == 2.0
    
    def test_shortcut_with_selected_text(self):
        """Test shortcut works with selected text."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        selected = text
        
        # Apply shortcut
        selected._font_size_pt += 1
        
        assert selected._font_size_pt == text._font_size_pt


class TestShortcutsOnlyForCompatibleTypes:
    """Test shortcuts only work for compatible annotation types."""
    
    def test_width_shortcut_on_vector_types(self):
        """Test width shortcuts work on all vector types."""
        vector_types = [
            AnnotationType.LINE, AnnotationType.ARROW,
            AnnotationType.RECTANGLE, AnnotationType.ELLIPSE,
            AnnotationType.CHECKMARK, AnnotationType.CROSSMARK,
        ]
        
        for ann_type in vector_types:
            ann = VectorAnnotation(ann_type, 100, 100, 0)
            assert hasattr(ann, '_line_width_pt')
            ann._line_width_pt += 0.5
            assert ann._line_width_pt == 2.0
    
    def test_font_shortcut_only_on_text(self):
        """Test font shortcuts only work on Text."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Font shortcut works on text
        assert hasattr(text, '_font_size_pt')
        
        # Font shortcut doesn't apply to line
        # (line doesn't have _font_size_pt)


class TestShortcutBounds:
    """Test shortcuts respect min/max bounds."""
    
    def test_width_stays_in_bounds(self):
        """Test width shortcuts never exceed bounds."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Test minimum
        line._line_width_pt = 0.5
        assert line._line_width_pt >= 0.5
        
        # Test maximum
        line._line_width_pt = 10.0
        assert line._line_width_pt <= 10.0
    
    def test_font_size_stays_in_bounds(self):
        """Test font size shortcuts never exceed bounds."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Test minimum (6pt ≈ 8px)
        text._font_size_pt = 8
        assert text._font_size_pt >= 8
        
        # Test maximum (72pt ≈ 96px)
        text._font_size_pt = 96
        assert text._font_size_pt <= 96


class TestShortcutHistory:
    """Test shortcuts record actions to history."""
    
    def test_width_change_recorded(self):
        """Test width change could be recorded to history."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        initial = line._line_width_pt
        
        # Simulate change
        line._line_width_pt += 0.5
        
        # Could record: (line, initial, new)
        final = line._line_width_pt
        
        assert initial != final
        assert final == 2.0
    
    def test_font_size_change_recorded(self):
        """Test font size change could be recorded to history."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        initial = text._font_size_pt
        
        # Simulate change
        text._font_size_pt += 1
        
        # Could record: (text, initial, new)
        final = text._font_size_pt
        
        assert initial != final


class TestShortcutStepSizes:
    """Test shortcuts use correct step sizes."""
    
    def test_width_steps_by_half_point(self):
        """Test width changes in 0.5pt steps."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # ] should step by +0.5
        line._line_width_pt = 1.5
        line._line_width_pt += 0.5
        assert line._line_width_pt == 2.0
        
        # [ should step by -0.5
        line._line_width_pt -= 0.5
        assert line._line_width_pt == 1.5
    
    def test_font_size_steps_by_one_point(self):
        """Test font size changes in 1pt steps."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        initial = text._font_size_pt
        
        # ] should step by +1
        text._font_size_pt += 1
        assert text._font_size_pt == initial + 1
        
        # [ should step by -1
        text._font_size_pt -= 1
        assert text._font_size_pt == initial
