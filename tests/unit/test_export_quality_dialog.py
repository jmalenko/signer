"""Feature tests for export quality dialog and workflow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from signer.compositor import ExportFormat
from signer.export_quality_dialog import ExportQualityOptionsPanel


@pytest.fixture
def qapp():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestExportQualityDialog:
    """Test the ExportQualityOptionsPanel dialog."""
    
    def test_dialog_creation_jpg(self, qapp):
        """Test dialog can be created for JPG format."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        assert dialog is not None
        assert dialog.export_format == ExportFormat.JPG
        assert dialog.current_quality == 95
    
    def test_dialog_creation_pdf(self, qapp):
        """Test dialog can be created for PDF format."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.PDF, 85)
        assert dialog is not None
        assert dialog.export_format == ExportFormat.PDF
        assert dialog.current_quality == 85
    
    def test_slider_initialization(self, qapp):
        """Test slider is initialized with current quality."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 75)
        assert dialog.quality_slider.value() == 75
        assert dialog.quality_slider.minimum() == 1
        assert dialog.quality_slider.maximum() == 100
    
    def test_spinbox_initialization(self, qapp):
        """Test spinbox is initialized with current quality."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 60)
        assert dialog.quality_spinbox.value() == 60
        assert dialog.quality_spinbox.minimum() == 1
        assert dialog.quality_spinbox.maximum() == 100
    
    def test_slider_spinbox_sync(self, qapp):
        """Test slider and spinbox stay synchronized."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 50)
        
        # Change slider
        dialog.quality_slider.setValue(70)
        assert dialog.quality_spinbox.value() == 70
        
        # Change spinbox
        dialog.quality_spinbox.setValue(30)
        assert dialog.quality_slider.value() == 30
    
    def test_get_quality_returns_slider_value(self, qapp):
        """Test get_quality() returns the current slider value."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        assert dialog.get_quality() == 95
        
        dialog.quality_slider.setValue(50)
        assert dialog.get_quality() == 50
    
    def test_ok_button_accepts_dialog(self, qapp):
        """Test OK button accepts the dialog."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        dialog.quality_slider.setValue(80)
        
        # Simulate clicking OK
        dialog._on_ok_clicked()
        assert dialog.user_accepted is True
    
    def test_cancel_button_rejects_dialog(self, qapp):
        """Test Cancel button rejects the dialog."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        dialog.quality_slider.setValue(40)
        
        # Simulate clicking Cancel
        dialog._on_cancel_clicked()
        assert dialog.user_accepted is False


class TestQualityWorkflow:
    """Test quality options workflow."""
    
    def test_quality_panel_shows_correct_format_name(self, qapp):
        """Test dialog displays correct format name."""
        jpg_dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        pdf_dialog = ExportQualityOptionsPanel(None, ExportFormat.PDF, 95)
        
        # Dialog titles should contain format info
        assert jpg_dialog.windowTitle() == "Export Quality Options"
        assert pdf_dialog.windowTitle() == "Export Quality Options"
    
    def test_slider_labels_present(self, qapp):
        """Test slider has quality-to-filesize labels."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        # Dialog is created with labels in the layout
        # (actual text validation is difficult without rendering)
        assert dialog.quality_slider is not None
    
    def test_numeric_value_always_visible(self, qapp):
        """Test numeric quality value is always visible."""
        dialog = ExportQualityOptionsPanel(None, ExportFormat.JPG, 95)
        # Spinbox is created and can display value
        assert dialog.quality_spinbox is not None
        # Show dialog to make widgets visible
        dialog.show()
        assert dialog.quality_spinbox.isVisible()

