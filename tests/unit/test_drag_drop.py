"""Unit tests for drag-and-drop file handling feature (v1.2.25)."""

import os
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO

import pytest
from PIL import Image
from PySide6.QtCore import Qt, QMimeData, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog

from signer.main_window import MainWindow
from signer.canvas import DocumentCanvas
from signer.settings import SettingsStore, AppSettings
from signer.objects import SignatureObject


@pytest.fixture
def small_test_image(temp_dir):
    """Create a small test image (fits A6 at 300 DPI)."""
    # A6 at 300 DPI: 1240 × 1748 pixels
    # Small image: 800 × 600 pixels
    img = Image.new('RGB', (800, 600), color=(255, 0, 0))
    img_path = temp_dir / "small_image.png"
    img.save(img_path)
    return img_path


@pytest.fixture
def big_test_image(temp_dir):
    """Create a big test image (exceeds A6 at 300 DPI)."""
    # A6 at 300 DPI: 1240 × 1748 pixels
    # Big image: 2000 × 1500 pixels
    img = Image.new('RGB', (2000, 1500), color=(0, 255, 0))
    img_path = temp_dir / "big_image.png"
    img.save(img_path)
    return img_path


@pytest.fixture
def edge_case_image(temp_dir):
    """Create an image exactly at the A6 threshold."""
    # Exactly at the edge: 1748 × 1748 pixels
    img = Image.new('RGB', (1748, 1748), color=(0, 0, 255))
    img_path = temp_dir / "edge_case_image.png"
    img.save(img_path)
    return img_path


@pytest.fixture
def edge_case_image_over(temp_dir):
    """Create an image just over the A6 threshold."""
    # Just over: 1749 × 1748 pixels
    img = Image.new('RGB', (1749, 1748), color=(0, 0, 255))
    img_path = temp_dir / "edge_case_over_image.png"
    img.save(img_path)
    return img_path


@pytest.fixture
def corrupted_image(temp_dir):
    """Create a corrupted image file."""
    img_path = temp_dir / "corrupted.png"
    # Write invalid PNG data
    with open(img_path, 'wb') as f:
        f.write(b"This is not a valid PNG file")
    return img_path


@pytest.fixture
def test_pdf(temp_dir):
    """Create a simple test PDF."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test PDF")
    pdf_path = temp_dir / "test.pdf"
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def main_window_no_doc(qapp, temp_dir):
    """Create a MainWindow with no document loaded."""
    store = SettingsStore()
    store._settings_path = temp_dir / "config_never_exists.json"
    settings = AppSettings()
    window = MainWindow(settings_store=store, settings=settings)
    window.show()
    yield window
    window.close()


@pytest.fixture
def main_window_with_doc(qapp, temp_dir, test_pdf):
    """Create a MainWindow with a document loaded."""
    store = SettingsStore()
    store._settings_path = temp_dir / "config_never_exists.json"
    settings = AppSettings()
    window = MainWindow(settings_store=store, settings=settings)
    window.show()
    
    # Load the test PDF
    with patch('signer.main_window.render_all_pages') as mock_render:
        test_page = Image.new('RGB', (612, 792))
        mock_render.return_value = [test_page]
        window.open_document(str(test_pdf))
    
    yield window
    window.close()


@pytest.fixture
def main_window_with_unsaved(qapp, temp_dir, test_pdf):
    """Create a MainWindow with a document loaded and unsaved changes."""
    store = SettingsStore()
    store._settings_path = temp_dir / "config_never_exists.json"
    settings = AppSettings()
    window = MainWindow(settings_store=store, settings=settings)
    window.show()
    
    # Load the test PDF
    with patch('signer.main_window.render_all_pages') as mock_render:
        test_page = Image.new('RGB', (612, 792))
        mock_render.return_value = [test_page]
        window.open_document(str(test_pdf))
    
    # Mark as having unsaved changes
    window._has_unsaved_changes = True
    
    yield window
    window.close()


class TestSmallImageDetection:
    """Tests for small image size detection."""
    
    def test_is_small_image_small(self, main_window_no_doc, small_test_image):
        """Test that small images are correctly identified."""
        result = main_window_no_doc._is_small_image(str(small_test_image))
        assert result is True
    
    def test_is_small_image_big(self, main_window_no_doc, big_test_image):
        """Test that big images are correctly identified as not small."""
        result = main_window_no_doc._is_small_image(str(big_test_image))
        assert result is False
    
    def test_is_small_image_at_threshold(self, main_window_no_doc, edge_case_image):
        """Test image exactly at A6 threshold (1748px)."""
        result = main_window_no_doc._is_small_image(str(edge_case_image))
        assert result is True  # At threshold, should be small
    
    def test_is_small_image_over_threshold(self, main_window_no_doc, edge_case_image_over):
        """Test image just over A6 threshold."""
        result = main_window_no_doc._is_small_image(str(edge_case_image_over))
        assert result is False  # Over threshold, should be big
    
    def test_is_small_image_corrupted(self, main_window_no_doc, corrupted_image):
        """Test handling of corrupted image."""
        with patch('signer.main_window.logging') as mock_logging:
            result = main_window_no_doc._is_small_image(str(corrupted_image))
            assert result is False  # Should return False for corrupted images
    
    def test_is_small_image_landscape(self, main_window_no_doc, temp_dir):
        """Test landscape image at threshold."""
        # 1748w × 1000h - should be small (max dimension is 1748)
        img = Image.new('RGB', (1748, 1000))
        img_path = temp_dir / "landscape.png"
        img.save(img_path)
        
        result = main_window_no_doc._is_small_image(str(img_path))
        assert result is True
    
    def test_is_small_image_portrait(self, main_window_no_doc, temp_dir):
        """Test portrait image at threshold."""
        # 1000w × 1748h - should be small (max dimension is 1748)
        img = Image.new('RGB', (1000, 1748))
        img_path = temp_dir / "portrait.png"
        img.save(img_path)
        
        result = main_window_no_doc._is_small_image(str(img_path))
        assert result is True


class TestSmallImageDrop:
    """Tests for small image drop handling."""
    
    def test_small_image_drop_with_document(self, main_window_with_doc, small_test_image):
        """Test dropping small image on a document creates annotation."""
        initial_count = len(main_window_with_doc.canvas.current_page_objects())
        
        # Simulate drop
        main_window_with_doc._on_file_drop(str(small_test_image))
        
        # Should add an annotation
        final_count = len(main_window_with_doc.canvas.current_page_objects())
        assert final_count > initial_count
    
    def test_small_image_drop_no_document(self, main_window_no_doc, small_test_image):
        """Test dropping small image with no document shows error."""
        with patch('signer.main_window.QMessageBox.critical') as mock_error:
            main_window_no_doc._on_file_drop(str(small_test_image))
            mock_error.assert_called_once()
            # Check error mentions "No document"
            call_args = mock_error.call_args
            assert "No document" in str(call_args)
    
    def test_small_image_drop_creates_signature_object(self, main_window_with_doc, small_test_image):
        """Test that dropped small image creates a SignatureObject."""
        main_window_with_doc._on_file_drop(str(small_test_image))
        
        # Get the added object
        objects = main_window_with_doc.canvas.current_page_objects()
        assert len(objects) > 0
        
        # Last added object should be a signature/image object
        last_obj = objects[-1]
        assert isinstance(last_obj, SignatureObject)
    
    def test_small_image_drop_marks_unsaved(self, main_window_with_doc, small_test_image):
        """Test that dropping small image marks document as having unsaved changes."""
        main_window_with_doc._has_unsaved_changes = False
        main_window_with_doc._on_file_drop(str(small_test_image))
        assert main_window_with_doc._has_unsaved_changes is True
    
    def test_small_image_drop_corrupted(self, main_window_with_doc, corrupted_image):
        """Test dropping corrupted image shows error."""
        with patch('signer.main_window.QMessageBox.critical') as mock_error:
            main_window_with_doc._on_file_drop(str(corrupted_image))
            mock_error.assert_called_once()


class TestBigImageDrop:
    """Tests for big image/PDF drop handling."""
    
    def test_big_image_drop_no_unsaved(self, main_window_with_doc, big_test_image):
        """Test dropping big image with no unsaved changes opens directly."""
        main_window_with_doc._has_unsaved_changes = False
        
        with patch.object(main_window_with_doc, 'open_document') as mock_open:
            main_window_with_doc._on_file_drop(str(big_test_image))
            mock_open.assert_called_once_with(str(big_test_image))
    
    def test_big_image_drop_with_unsaved_calls_open(self, main_window_with_unsaved, big_test_image):
        """Test dropping big image with unsaved changes calls open_document."""
        with patch.object(main_window_with_unsaved, 'open_document') as mock_open:
            # open_document will check for unsaved changes
            main_window_with_unsaved._on_file_drop(str(big_test_image))
            mock_open.assert_called_once_with(str(big_test_image))
    
    def test_pdf_drop_no_unsaved(self, main_window_with_doc, test_pdf):
        """Test dropping PDF with no unsaved changes opens directly."""
        main_window_with_doc._has_unsaved_changes = False
        
        with patch.object(main_window_with_doc, 'open_document') as mock_open:
            main_window_with_doc._on_file_drop(str(test_pdf))
            mock_open.assert_called_once_with(str(test_pdf))
    
    def test_pdf_drop_with_unsaved_calls_open(self, main_window_with_unsaved, test_pdf):
        """Test dropping PDF with unsaved changes calls open_document."""
        with patch.object(main_window_with_unsaved, 'open_document') as mock_open:
            # open_document will check for unsaved changes
            main_window_with_unsaved._on_file_drop(str(test_pdf))
            mock_open.assert_called_once_with(str(test_pdf))


class TestFileDragEnter:
    """Tests for drag enter event handling on canvas."""
    
    def test_drag_enter_with_files(self, canvas):
        """Test dragEnterEvent accepts file drops."""
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile("test.png")])
        
        # Create a mock drag enter event
        event = Mock(spec=QDragEnterEvent)
        event.mimeData.return_value = mime_data
        
        # Call the method
        canvas.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()
    
    def test_drag_enter_without_files(self, canvas):
        """Test dragEnterEvent rejects non-file drops."""
        mime_data = QMimeData()
        mime_data.setText("just text")
        
        # Create a mock drag enter event
        event = Mock(spec=QDragEnterEvent)
        event.mimeData.return_value = mime_data
        
        # Call the method
        canvas.dragEnterEvent(event)
        event.ignore.assert_called_once()


class TestFileDropEvent:
    """Tests for file drop event handling on canvas."""
    
    def test_drop_event_emits_signal(self, canvas, small_test_image):
        """Test dropEvent emits fileDrop signal."""
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(small_test_image))])
        
        # Create a mock drop event
        event = Mock(spec=QDropEvent)
        event.mimeData.return_value = mime_data
        
        # Connect to signal and track emissions
        signal_data = []
        canvas.fileDrop.connect(lambda path: signal_data.append(path))
        
        # Call the method
        canvas.dropEvent(event)
        
        # Check signal was emitted with correct file path
        assert len(signal_data) == 1
        # Compare as Path objects to normalize path separators
        assert Path(small_test_image) == Path(signal_data[0])
        event.acceptProposedAction.assert_called_once()
    
    def test_drop_event_no_urls(self, canvas):
        """Test dropEvent ignores drops without URLs."""
        mime_data = QMimeData()
        mime_data.setText("just text")
        
        # Create a mock drop event
        event = Mock(spec=QDropEvent)
        event.mimeData.return_value = mime_data
        
        # Connect to signal
        signal_data = []
        canvas.fileDrop.connect(lambda path: signal_data.append(path))
        
        # Call the method
        canvas.dropEvent(event)
        
        # Signal should NOT be emitted
        assert len(signal_data) == 0
        event.ignore.assert_called_once()


class TestUnsupportedFiles:
    """Tests for handling unsupported file formats."""
    
    def test_unsupported_format_error(self, main_window_no_doc, temp_dir):
        """Test dropping unsupported file format shows error."""
        # Create an unsupported file type
        unsupported = temp_dir / "test.docx"
        unsupported.write_text("Not a real DOCX")
        
        with patch('signer.main_window.QMessageBox.critical') as mock_error:
            main_window_no_doc._on_file_drop(str(unsupported))
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "Unsupported" in str(call_args)
    
    def test_missing_file_error(self, main_window_no_doc, temp_dir):
        """Test dropping non-existent file shows error."""
        missing_file = temp_dir / "nonexistent.png"
        
        with patch('signer.main_window.QMessageBox.critical') as mock_error:
            main_window_no_doc._on_file_drop(str(missing_file))
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "not found" in str(call_args).lower()


class TestMultipleFileTypes:
    """Tests for various image formats."""
    
    @pytest.mark.parametrize("ext", [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"])
    def test_supported_image_formats(self, main_window_no_doc, temp_dir, ext):
        """Test that various image formats are recognized as images."""
        img = Image.new('RGB', (800, 600))
        img_path = temp_dir / f"test{ext}"
        img.save(img_path)
        
        # Should detect as image (not PDF)
        is_small = main_window_no_doc._is_small_image(str(img_path))
        assert is_small is True  # Small image
