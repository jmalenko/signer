"""Unit tests for unsaved changes tracking feature."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from signer.main_window import MainWindow
from signer.settings import AppSettings, SettingsStore


class TestUnsavedChangesTracking:
    """Tests for unsaved changes tracking in MainWindow."""
    
    @pytest.fixture
    def settings_store(self):
        """Create a mock settings store."""
        return Mock(spec=SettingsStore)
    
    @pytest.fixture
    def settings(self):
        """Create default app settings."""
        return AppSettings()
    
    @pytest.fixture
    def main_window(self, qapp, settings_store, settings):
        """Create a MainWindow instance for testing."""
        settings_store.load.return_value = settings
        window = MainWindow(settings_store, settings)
        yield window
        # Clean up
        if window.isVisible():
            window.hide()
    
    def test_unsaved_changes_initialized_false(self, main_window):
        """Test that _has_unsaved_changes is initialized to False."""
        assert main_window._has_unsaved_changes is False
    
    def test_unsaved_changes_set_true_on_object_changed(self, main_window):
        """Test that _has_unsaved_changes becomes True when objects change."""
        # Simulate object change
        main_window.canvas.objectChanged.emit()
        assert main_window._has_unsaved_changes is True
    
    def test_unsaved_changes_reset_on_document_open(self, main_window):
        """Test that _has_unsaved_changes is reset to False when opening a document."""
        # Set the flag to True
        main_window._has_unsaved_changes = True
        main_window.document_path = None
        
        # Mock the render_all_pages function to return a test page
        with patch('signer.main_window.render_all_pages') as mock_render:
            from PIL import Image
            test_page = Image.new('RGB', (612, 792))
            mock_render.return_value = [test_page]
            
            # Open a document
            with patch('signer.main_window.QFileDialog.getOpenFileName') as mock_dialog:
                test_doc_path = str(Path(__file__).parent.parent.parent / "examples" / "document.pdf")
                mock_dialog.return_value = (test_doc_path, "")
                
                # This should reset the flag
                result = main_window.open_document(test_doc_path)
        
        # Flag should be False after opening
        assert main_window._has_unsaved_changes is False
    
    def test_unsaved_changes_reset_after_save(self, main_window):
        """Test that _has_unsaved_changes is reset to False after saving."""
        # Set up the window with a mock document
        main_window.document_path = "test.pdf"
        main_window._has_unsaved_changes = True
        
        # Mock the canvas to have objects
        from PIL import Image
        main_window.canvas._pages = [Image.new('RGB', (612, 792))]
        main_window.canvas._page_pixmaps = []
        main_window.canvas._page_objects = {0: [Mock()]}
        
        # Mock the save dialog and composite function
        with patch('signer.main_window.QFileDialog.getSaveFileName') as mock_save_dialog, \
             patch('signer.main_window.composite_objects_to_jpg') as mock_composite, \
             patch('signer.main_window.QMessageBox.information') as mock_info:
            
            mock_save_dialog.return_value = ("/tmp/output.jpg", "")
            
            # Call save
            result = main_window.save_signed_document()
        
        # Flag should be False after successful save
        if result:
            assert main_window._has_unsaved_changes is False
    
    def test_check_unsaved_changes_no_changes(self, main_window):
        """Test _check_unsaved_changes returns True when no changes."""
        main_window._has_unsaved_changes = False
        result = main_window._check_unsaved_changes()
        assert result is True
    
    def test_check_unsaved_changes_no_document_path(self, main_window):
        """Test _check_unsaved_changes returns True when no document path."""
        main_window._has_unsaved_changes = True
        main_window.document_path = None
        result = main_window._check_unsaved_changes()
        assert result is True
    
    def test_check_unsaved_changes_dialog_cancel(self, main_window):
        """Test _check_unsaved_changes returns False when user cancels."""
        main_window._has_unsaved_changes = True
        main_window.document_path = "test.pdf"
        main_window._in_test_mode = False
        with patch('signer.main_window.QMessageBox.warning') as mock_warning:
            mock_warning.return_value = QMessageBox.Cancel
            result = main_window._check_unsaved_changes()

        assert result is False
    
    def test_check_unsaved_changes_dialog_discard(self, main_window):
        """Test _check_unsaved_changes returns True when user discards."""
        main_window._has_unsaved_changes = True
        main_window.document_path = "test.pdf"
        main_window._in_test_mode = False
        with patch('signer.main_window.QMessageBox.warning') as mock_warning:
            mock_warning.return_value = QMessageBox.Discard
            result = main_window._check_unsaved_changes()

        assert result is True
    
    def test_close_event_with_unsaved_changes_and_cancel(self, main_window):
        """Test closeEvent ignores close when user cancels save prompt."""
        main_window._has_unsaved_changes = True
        main_window.document_path = "test.pdf"
        main_window._in_test_mode = False

        event = Mock()
        with patch('signer.main_window.QMessageBox.warning') as mock_warning:
            mock_warning.return_value = QMessageBox.Cancel
            main_window.closeEvent(event)

        event.ignore.assert_called_once()
        event.accept.assert_not_called()
    
    def test_close_event_without_unsaved_changes(self, main_window):
        """Test closeEvent accepts close when no unsaved changes."""
        main_window._has_unsaved_changes = False
        
        event = Mock()
        main_window.closeEvent(event)
        
        event.accept.assert_called_once()

    def test_check_unsaved_changes_auto_discard_in_test_mode(self, main_window):
        """Test _check_unsaved_changes automatically discards in test mode."""
        main_window._has_unsaved_changes = True
        main_window.document_path = "test.pdf"
        main_window._in_test_mode = True
        # Mock the warning dialog - it should NOT be called
        with patch('signer.main_window.QMessageBox.warning') as mock_warning:
            result = main_window._check_unsaved_changes()
            # Dialog should not be shown
            mock_warning.assert_not_called()

        # Should return True (discard)
        assert result is True
