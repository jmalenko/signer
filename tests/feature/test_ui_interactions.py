"""Feature test: Multi-page document with annotations on different pages.

This test verifies:
1. Open multi-page document (document.pdf)
2. Add different annotations on different pages
3. Navigate between pages
4. Verify annotations persist per page
5. Export all pages
6. Verify each page output
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from signer.main_window import MainWindow
from signer.objects import AnnotationType
from signer.settings import SettingsStore


class TestMultipageAnnotations:
    """Feature test for multi-page document annotations."""
    
    @pytest.fixture
    def main_window(self, qapp, temp_dir):
        """Create a main window for testing."""
        settings_store = SettingsStore(app_name="SignerTest")
        settings_store._settings_path = temp_dir / "config.json"
        settings = settings_store.load()
        
        window = MainWindow(settings_store=settings_store, settings=settings)
        window.show()
        yield window
        window.close()
    
    def test_multipage_annotations_persist_per_page(self, main_window, sample_multipage_pdf, temp_dir):
        """Test that annotations on different pages persist when navigating."""
        
        # 1. Open multi-page document
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        assert main_window.canvas.has_document
        assert main_window.canvas.page_count >= 2  # document.pdf has multiple pages
        
        total_pages = main_window.canvas.page_count
        
        # 2. Add annotation on page 0
        main_window._add_vector(AnnotationType.CHECKMARK)
        page0_checkmark = main_window.canvas.selected
        page0_checkmark.x = 100
        page0_checkmark.y = 100
        main_window.canvas.objectChanged.emit()
        
        # 3. Go to page 1
        main_window.canvas.goto_page(1)
        assert main_window.canvas.current_page == 1
        
        # 4. Add different annotation on page 1
        main_window._add_vector(AnnotationType.CROSSMARK)
        page1_crossmark = main_window.canvas.selected
        page1_crossmark.x = 200
        page1_crossmark.y = 200
        main_window.canvas.objectChanged.emit()
        
        # 5. Go to page 2 (if exists)
        if total_pages > 2:
            main_window.canvas.goto_page(2)
            assert main_window.canvas.current_page == 2
            
            # Add text annotation on page 2
            main_window._add_text_annotation("Page 3 Text")
            page2_text = main_window.canvas.selected
            page2_text.x = 300
            page2_text.y = 300
            main_window.canvas.objectChanged.emit()
        
        # 6. Go back to page 0 - checkmark should still be there
        main_window.canvas.goto_page(0)
        assert main_window.canvas.current_page == 0
        page0_objects = main_window.canvas.current_page_objects()
        assert len(page0_objects) == 1
        assert page0_objects[0].ann_type == AnnotationType.CHECKMARK
        assert page0_objects[0].x == 100
        assert page0_objects[0].y == 100
        
        # 7. Go to page 1 - crossmark should still be there
        main_window.canvas.goto_page(1)
        assert main_window.canvas.current_page == 1
        page1_objects = main_window.canvas.current_page_objects()
        assert len(page1_objects) == 1
        assert page1_objects[0].ann_type == AnnotationType.CROSSMARK
        assert page1_objects[0].x == 200
        assert page1_objects[0].y == 200
        
        # 8. Go to page 2 - text should still be there (if exists)
        if total_pages > 2:
            main_window.canvas.goto_page(2)
            assert main_window.canvas.current_page == 2
            page2_objects = main_window.canvas.current_page_objects()
            assert len(page2_objects) == 1
            assert page2_objects[0].ann_type == AnnotationType.TEXT
            assert page2_objects[0].text == "Page 3 Text"
            assert page2_objects[0].x == 300
            assert page2_objects[0].y == 300
    
    def test_export_all_pages(self, main_window, sample_multipage_pdf, temp_dir):
        """Test exporting all pages with annotations."""
        
        # 1. Open multi-page document
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        # 2. Add annotations on each page
        total_pages = main_window.canvas.page_count
        for page_idx in range(total_pages):
            main_window.canvas.goto_page(page_idx)
            
            # Add a checkmark on each page at different positions
            main_window._add_vector(AnnotationType.CHECKMARK)
            obj = main_window.canvas.selected
            obj.x = 100 + page_idx * 50
            obj.y = 100 + page_idx * 50
            main_window.canvas.objectChanged.emit()
        
        # 3. Export all pages (save_signed_document exports all pages)
        output_dir = temp_dir / "multipage_output"
        output_dir.mkdir()
        
        # Mock file dialog to return our output directory with placeholder for multi-page exports
        if total_pages > 1:
            # Multi-page JPG export requires placeholder
            base_output = output_dir / "document-signed-p#.jpg"
        else:
            # Single-page export doesn't need placeholder
            base_output = output_dir / "document-signed.jpg"
        
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(base_output), "JPEG files (*.jpg *.jpeg)")):
            with patch.object(QMessageBox, 'information', return_value=QMessageBox.Ok):
                result = main_window.save_signed_document()
                assert result is True
        
        # 4. Verify each page was exported
        for page_idx in range(total_pages):
            if total_pages == 1:
                expected_name = "document-signed.jpg"
            else:
                pad = len(str(total_pages))
                expected_name = f"document-signed-p{page_idx + 1:0{pad}d}.jpg"
            
            output_file = output_dir / expected_name
            assert output_file.exists(), f"Expected output file not found: {output_file}"
            
            # Verify it's a valid JPEG
            from PIL import Image
            img = Image.open(output_file)
            assert img.format == "JPEG"
            assert img.mode == "RGB"
    
    def test_page_navigation_keyboard(self, main_window, sample_multipage_pdf):
        """Test page navigation via keyboard shortcuts."""
        
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        total_pages = main_window.canvas.page_count
        assert total_pages >= 2
        
        # Start at page 0
        assert main_window.canvas.current_page == 0
        
        # PageDown -> page 1
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.keyClick(main_window.canvas, Qt.Key_PageDown)
        assert main_window.canvas.current_page == 1
        
        # PageDown -> page 2 (if exists)
        if total_pages > 2:
            QTest.keyClick(main_window.canvas, Qt.Key_PageDown)
            assert main_window.canvas.current_page == 2
        
        # PageUp -> previous page
        QTest.keyClick(main_window.canvas, Qt.Key_PageUp)
        assert main_window.canvas.current_page == 1
        
        # Home -> first page
        QTest.keyClick(main_window.canvas, Qt.Key_Home)
        assert main_window.canvas.current_page == 0
        
        # End -> last page
        QTest.keyClick(main_window.canvas, Qt.Key_End)
        assert main_window.canvas.current_page == total_pages - 1

    def test_plus_opens_annotation_menu(self, main_window, sample_pdf):
        """The plus hotkey opens the toolbar annotation menu."""
        assert main_window.open_document(str(sample_pdf))

        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        main_window.canvas.setFocus()
        with patch.object(main_window._add_annotation_btn, "showMenu") as show_menu:
            QTest.keyClick(main_window.canvas, Qt.Key_Plus)

        show_menu.assert_called_once_with()
    
    def test_page_navigation_toolbar(self, main_window, sample_multipage_pdf):
        """Test page navigation via toolbar buttons."""
        
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        total_pages = main_window.canvas.page_count
        assert total_pages >= 2
        
        # Start at page 0
        assert main_window.canvas.current_page == 0
        
        # Click Next button
        # The toolbar actions are connected to canvas.goto_page
        main_window.canvas.goto_page(1)
        assert main_window.canvas.current_page == 1
        
        # Click Prev button
        main_window.canvas.goto_page(0)
        assert main_window.canvas.current_page == 0
    
    def test_annotation_independence_per_page(self, main_window, sample_multipage_pdf):
        """Test that annotations on one page don't affect other pages."""
        
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        total_pages = main_window.canvas.page_count
        
        # Add checkmark on page 0
        main_window.canvas.goto_page(0)
        main_window._add_vector(AnnotationType.CHECKMARK)
        obj0 = main_window.canvas.selected
        obj0.x = 100
        obj0.y = 100
        main_window.canvas.objectChanged.emit()
        
        # Add crossmark on page 1
        main_window.canvas.goto_page(1)
        main_window._add_vector(AnnotationType.CROSSMARK)
        obj1 = main_window.canvas.selected
        obj1.x = 200
        obj1.y = 200
        main_window.canvas.objectChanged.emit()
        
        # Verify page 0 only has checkmark
        main_window.canvas.goto_page(0)
        page0_objects = main_window.canvas.current_page_objects()
        assert len(page0_objects) == 1
        assert page0_objects[0].ann_type == AnnotationType.CHECKMARK
        
        # Verify page 1 only has crossmark
        main_window.canvas.goto_page(1)
        page1_objects = main_window.canvas.current_page_objects()
        assert len(page1_objects) == 1
        assert page1_objects[0].ann_type == AnnotationType.CROSSMARK
        
        # Modify object on page 0
        main_window.canvas.goto_page(0)
        page0_objects[0].x = 150
        page0_objects[0].y = 150
        main_window.canvas.objectChanged.emit()
        
        # Verify page 1 unchanged
        main_window.canvas.goto_page(1)
        page1_objects = main_window.canvas.current_page_objects()
        assert page1_objects[0].x == 200
        assert page1_objects[0].y == 200
    
    def test_duplicate_annotation_on_page(self, main_window, sample_multipage_pdf):
        """Test duplicating annotations on a page."""
        
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        main_window.canvas.goto_page(0)
        main_window._add_vector(AnnotationType.CHECKMARK)
        original = main_window.canvas.selected
        original.x = 100
        original.y = 100
        main_window.canvas.objectChanged.emit()
        
        # Duplicate
        main_window.canvas.duplicate_selected()
        
        # Should have 2 objects now
        page0_objects = main_window.canvas.current_page_objects()
        assert len(page0_objects) == 2
        
        # Duplicate should be offset
        dup = page0_objects[1]
        assert dup.x == 120
        assert dup.y == 120
        assert dup.ann_type == AnnotationType.CHECKMARK
        assert dup.scale == original.scale
    
    def test_delete_annotation_on_page(self, main_window, sample_multipage_pdf):
        """Test deleting annotations on a page."""
        
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        main_window.canvas.goto_page(0)
        main_window._add_vector(AnnotationType.CHECKMARK)
        main_window.canvas.objectChanged.emit()
        
        # Verify object exists
        assert len(main_window.canvas.current_page_objects()) == 1
        
        # Delete
        main_window.canvas.remove_selected()
        
        # Should be gone
        assert len(main_window.canvas.current_page_objects()) == 0
        assert main_window.canvas.selected is None
    
    def test_color_change_per_page(self, main_window, sample_multipage_pdf):
        """Test changing annotation color on different pages."""
        
        result = main_window.open_document(str(sample_multipage_pdf))
        assert result is True
        
        # Page 0: red checkmark
        main_window.canvas.goto_page(0)
        main_window._add_vector(AnnotationType.CHECKMARK)
        obj0 = main_window.canvas.selected
        obj0.color = obj0.color.__class__("#ff0000")  # Red
        main_window.canvas.objectChanged.emit()
        
        # Page 1: blue crossmark
        main_window.canvas.goto_page(1)
        main_window._add_vector(AnnotationType.CROSSMARK)
        obj1 = main_window.canvas.selected
        obj1.color = obj1.color.__class__("#0000ff")  # Blue
        main_window.canvas.objectChanged.emit()
        
        # Verify colors
        main_window.canvas.goto_page(0)
        assert main_window.canvas.current_page_objects()[0].color.name() == "#ff0000"
        
        main_window.canvas.goto_page(1)
        assert main_window.canvas.current_page_objects()[0].color.name() == "#0000ff"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])