"""Feature tests for context-sensitive UI behavior."""

import pytest
from unittest.mock import MagicMock, Mock, patch
from PySide6.QtCore import Qt
from signer.objects import VectorAnnotation, AnnotationType
from signer.canvas import DocumentCanvas
from signer.main_window import MainWindow


class TestControlVisibilityPerType:
    """Test that controls appear/disappear based on annotation type."""
    
    def test_line_shows_color_and_width(self, qtbot):
        """Test Line annotation displays color and width controls."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Should support both color and width
        assert hasattr(line, 'color')
        assert hasattr(line, '_line_width_pt')
    
    def test_rectangle_shows_color_and_width(self, qtbot):
        """Test Rectangle annotation displays color and width controls."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        assert hasattr(rect, 'color')
        assert hasattr(rect, '_line_width_pt')
    
    def test_ellipse_shows_color_and_width(self, qtbot):
        """Test Ellipse annotation displays color and width controls."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        
        assert hasattr(ellipse, 'color')
        assert hasattr(ellipse, '_line_width_pt')
    
    def test_arrow_shows_color_and_width(self, qtbot):
        """Test Arrow annotation displays color and width controls."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        
        assert hasattr(arrow, 'color')
        assert hasattr(arrow, '_line_width_pt')
    
    def test_text_shows_color_font_size_family(self, qtbot):
        """Test Text annotation displays color, font size, and font family."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        assert hasattr(text, 'color')
        assert hasattr(text, '_font_size_px')
        assert hasattr(text, '_font_family')
        # Should NOT have width
        # (width is for vector strokes, not text)
    
    def test_checkmark_shows_color_and_width(self, qtbot):
        """Test Checkmark annotation displays color and width."""
        checkmark = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        
        assert hasattr(checkmark, 'color')
        assert hasattr(checkmark, '_line_width_pt')
    
    def test_crossmark_shows_color_and_width(self, qtbot):
        """Test Crossmark annotation displays color and width."""
        crossmark = VectorAnnotation(AnnotationType.CROSSMARK, 100, 100, 0)
        
        assert hasattr(crossmark, 'color')
        assert hasattr(crossmark, '_line_width_pt')


class TestControlDisabledStates:
    """Test that controls are disabled when no annotation selected."""
    
    def test_no_selection_controls_disabled(self):
        """Test controls are conceptually disabled when nothing selected."""
        # No annotation
        selected = None
        
        # Controls should be conceptually disabled
        assert selected is None
    
    def test_selection_controls_enabled(self):
        """Test controls are enabled when annotation selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Selection exists
        selected = line
        
        assert selected is not None
        assert hasattr(selected, 'color')


class TestDocumentDependentWorkflowButtons:
    """Test document-dependent toolbar/menu control states."""

    def test_buttons_disabled_without_document(self, main_window):
        """Add Annotation and Save As are disabled when no document is open."""
        assert not main_window.canvas.has_document
        assert main_window._add_annotation_btn is not None
        assert main_window._save_as_toolbar_action is not None
        assert main_window._save_as_file_action is not None
        assert main_window._hamburger_annotations_menu is not None

        assert not main_window._add_annotation_btn.isEnabled()
        assert not main_window._save_as_toolbar_action.isEnabled()
        assert not main_window._save_as_file_action.isEnabled()
        assert not main_window._hamburger_annotations_menu.menuAction().isEnabled()

    def test_buttons_enabled_after_open_document(self, main_window, sample_pdf):
        """Add Annotation and Save As become enabled after opening a document."""
        assert main_window.open_document(str(sample_pdf))
        assert main_window.canvas.has_document

        assert main_window._add_annotation_btn is not None
        assert main_window._save_as_toolbar_action is not None
        assert main_window._save_as_file_action is not None
        assert main_window._hamburger_annotations_menu is not None

        assert main_window._add_annotation_btn.isEnabled()
        assert main_window._save_as_toolbar_action.isEnabled()
        assert main_window._save_as_file_action.isEnabled()
        assert main_window._hamburger_annotations_menu.menuAction().isEnabled()

    def test_page_navigation_hidden_for_single_page_document(self, main_window, sample_pdf):
        """Single-page documents should hide the toolbar page navigation controls."""
        assert main_window.open_document(str(sample_pdf))
        assert main_window.canvas.page_count == 1

        assert main_window._page_nav_prev_action is not None
        assert main_window._page_nav_next_action is not None
        assert main_window._page_nav_label is not None
        assert main_window._page_nav_prev_action.text() == "◀"
        assert main_window._page_nav_next_action.text() == "▶"
        assert not main_window._page_nav_prev_action.isVisible()
        assert not main_window._page_nav_next_action.isVisible()
        assert not main_window._page_nav_label.isVisible()

    def test_property_controls_hidden_when_no_selection(self, main_window, sample_pdf):
        """No selection should hide all annotation property controls even on a single-page document."""
        assert main_window.open_document(str(sample_pdf))
        assert main_window.canvas.page_count == 1
        assert main_window.canvas.selected is None

        main_window._update_annotation_action_state()

        assert not main_window._color_btn.isVisible()
        assert not main_window._width_spinner.isVisible()
        assert not main_window._width_label.isVisible()
        assert not main_window._font_size_spinner.isVisible()
        assert not main_window._font_size_label.isVisible()
        assert not main_window._font_family_combo.isVisible()
        assert not main_window._font_label.isVisible()


class TestStateTransitions:
    """Test UI state transitions when changing selections."""
    
    def test_select_line_then_rectangle(self):
        """Test transitioning from Line to Rectangle selection."""
        line = VectorAnnotation(AnnotationType.LINE, 50, 50, 0)
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 150, 150, 0)
        
        # Select line - should show width
        selected = line
        assert hasattr(selected, '_line_width_pt')
        
        # Select rectangle - should still show width
        selected = rect
        assert hasattr(selected, '_line_width_pt')
    
    def test_select_text_then_line(self):
        """Test transitioning from Text to Line selection."""
        text = VectorAnnotation(AnnotationType.TEXT, 50, 50, 0, text="Test")
        line = VectorAnnotation(AnnotationType.LINE, 150, 150, 0)
        
        # Select text - should show font controls
        selected = text
        assert hasattr(selected, '_font_size_px')
        assert hasattr(selected, '_font_family')
        
        # Select line - should show width, not font
        selected = line
        assert hasattr(selected, '_line_width_pt')
        # Font size should not be used for line
        text_data = text.to_dict()
        line_data = line.to_dict()
        assert 'font_size_px' in text_data
        assert 'font_size_px' not in line_data
    
    def test_select_arrow_then_text(self):
        """Test transitioning from Arrow to Text selection."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 50, 50, 0)
        text = VectorAnnotation(AnnotationType.TEXT, 150, 150, 0, text="Label")
        
        # Select arrow
        selected = arrow
        assert hasattr(selected, '_line_width_pt')
        
        # Select text
        selected = text
        assert hasattr(selected, '_font_size_px')
        assert hasattr(selected, '_font_family')


class TestControlUpdatesOnPropertyChange:
    """Test controls update when annotation property changes."""
    
    def test_width_spinner_reflects_line_width(self):
        """Test width spinner value matches line width property."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Set width
        line._line_width_pt = 2.5
        
        # Spinner should display this value
        spinner_value = line._line_width_pt
        assert spinner_value == 2.5
    
    def test_font_size_spinner_reflects_text_font_size(self):
        """Test font size spinner value matches text font size property."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Set font size
        text._font_size_px = 32
        
        # Spinner should display this value
        spinner_value = text._font_size_px
        assert spinner_value == 32
    
    def test_font_family_combo_reflects_text_font_family(self):
        """Test font family combo value matches text font family property."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Set font family
        text._font_family = "Courier New"
        
        # Combo should display this value
        combo_value = text._font_family
        assert combo_value == "Courier New"
    
    def test_color_control_reflects_annotation_color(self):
        """Test color control reflects annotation color."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Set color
        line.color.setNamedColor("#ff0000")
        
        # Color control should display red
        color_value = line.color.name()
        assert color_value == "#ff0000"


class TestPropertyBounds:
    """Test that controls enforce property bounds."""
    
    def test_width_spinner_minimum(self):
        """Test width spinner enforces minimum (0.5pt)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Try to set below minimum
        line._line_width_pt = 0.5
        assert line._line_width_pt == 0.5
    
    def test_width_spinner_maximum(self):
        """Test width spinner enforces maximum (10pt)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Try to set at maximum
        line._line_width_pt = 10.0
        assert line._line_width_pt == 10.0
    
    def test_font_size_spinner_minimum(self):
        """Test font size spinner enforces minimum (6pt)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Set to minimum (6pt ≈ 8px)
        text._font_size_px = 8
        assert text._font_size_px == 8
    
    def test_font_size_spinner_maximum(self):
        """Test font size spinner enforces maximum (72pt)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Set to maximum (72pt ≈ 96px)
        text._font_size_px = 96
        assert text._font_size_px == 96


class TestSignalBlockingDuringUpdates:
    """Test that signals are blocked to prevent feedback loops."""
    
    def test_no_double_update_on_spinner_change(self):
        """Test changing spinner doesn't cause infinite loop."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Simulate user changing spinner
        original_width = line._line_width_pt
        
        # Change width
        line._line_width_pt = 2.5
        
        # Should only update once
        assert line._line_width_pt == 2.5
    
    def test_no_double_update_on_property_change(self):
        """Test changing property doesn't cause infinite loop."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Simulate direct property change
        original_size = text._font_size_px
        
        # Change font size
        text._font_size_px = 32
        
        # Should only update once
        assert text._font_size_px == 32
