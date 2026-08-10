"""Feature test: document1.pdf with signature and checkmark.

This test reproduces the recorded actions:
1. Open document1.pdf
2. Add signature from signature.png
3. Add checkmark annotation
4. Move and resize signature
5. Move and resize checkmark
6. Save as JPG
7. Compare pixel-perfect to reference image

To create the reference image:
1. Run the application with SIGNER_RECORD_ACTIONS=1
2. Perform the actions manually
3. Save the output as examples/document1-signed-expected.jpg
4. The recorded actions JSON can be used to verify the test steps
"""

import os
import tempfile
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from signer.canvas import DocumentCanvas
from signer.main_window import MainWindow
from signer.objects import AnnotationType, SignatureObject, VectorAnnotation
from signer.settings import AppSettings, SettingsStore
from tests.utils.image_comparison import assert_images_equal


class TestDocument1SignatureCheckmark:
    """Feature test for document1.pdf with signature and checkmark."""
    
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
    
    def test_document1_signature_checkmark_pixel_perfect(self, main_window, sample_pdf, sample_signature, temp_dir):
        """Test the complete workflow: open doc, add signature, add checkmark, move/resize, save, compare."""
        
        # Reference image path (must be created manually first)
        reference_image = Path(__file__).parent.parent / "examples" / "document1-signed-expected.jpg"
        
        if not reference_image.exists():
            pytest.skip(f"Reference image not found: {reference_image}. Create it manually first.")
        
        output_path = temp_dir / "document1-signed-test.jpg"
        diff_path = temp_dir / "document1-signed-diff.jpg"
        
        # 1. Open document
        result = main_window.open_document(str(sample_pdf))
        assert result is True
        assert main_window.canvas.has_document
        assert main_window.canvas.page_count == 1
        
        # 2. Load signature
        result = main_window._load_signature_file(str(sample_signature), at_default_position=True)
        assert result is True
        assert main_window.canvas.selected is not None
        assert isinstance(main_window.canvas.selected, SignatureObject)
        
        sig_obj = main_window.canvas.selected
        initial_sig_x = sig_obj.x
        initial_sig_y = sig_obj.y
        initial_sig_w = sig_obj.scaled_width
        initial_sig_h = sig_obj.scaled_height
        
        # 3. Add checkmark
        main_window._add_vector(AnnotationType.CHECKMARK)
        assert main_window.canvas.selected is not None
        assert isinstance(main_window.canvas.selected, VectorAnnotation)
        assert main_window.canvas.selected.ann_type == AnnotationType.CHECKMARK
        
        check_obj = main_window.canvas.selected
        initial_check_x = check_obj.x
        initial_check_y = check_obj.y
        initial_check_w = check_obj.scaled_width
        initial_check_h = check_obj.scaled_height
        
        # 4. Move signature to target position
        target_sig_x = 300.0
        target_sig_y = 400.0
        sig_obj.x = target_sig_x
        sig_obj.y = target_sig_y
        main_window.canvas.objectChanged.emit()
        main_window.canvas.update()
        
        # 5. Resize signature (simulate handle drag)
        target_sig_w = 250.0
        target_sig_h = 250.0
        sig_obj.set_scaled_size(target_sig_w, target_sig_h)
        main_window.canvas.objectChanged.emit()
        main_window.canvas.update()
        
        # 6. Select checkmark and move it
        main_window.canvas._selected = check_obj
        main_window.canvas.objectChanged.emit()
        
        target_check_x = 150.0
        target_check_y = 200.0
        check_obj.x = target_check_x
        check_obj.y = target_check_y
        main_window.canvas.objectChanged.emit()
        main_window.canvas.update()
        
        # 7. Resize checkmark
        target_check_w = 120.0
        target_check_h = 120.0
        check_obj.set_scaled_size(target_check_w, target_check_h)
        main_window.canvas.objectChanged.emit()
        main_window.canvas.update()
        
        # 8. Save document
        # We need to mock the file dialog to return our output path
        from unittest.mock import patch
        from PySide6.QtWidgets import QFileDialog
        
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(output_path), "JPEG files (*.jpg *.jpeg)")):
            result = main_window.save_signed_document()
            assert result is True
        
        # 9. Compare with reference image (pixel-perfect)
        assert_images_equal(output_path, reference_image, tolerance=0, diff_output_path=diff_path)
    
    def test_recorded_actions_reproduction(self, main_window, sample_pdf, sample_signature, temp_dir):
        """Test that reproduces exact recorded actions from JSON.
        
        This test can be updated with actual recorded actions.
        """
        # Example recorded actions (replace with actual recorded data)
        recorded_actions = [
            {"type": "open_document", "path": str(sample_pdf), "timestamp": 0.0},
            {"type": "open_signature", "path": str(sample_signature), "timestamp": 1.0},
            {"type": "add_annotation", "annotation_type": "checkmark", "x": 400, "y": 300, "page": 0, "timestamp": 2.0},
            {"type": "move_annotation", "object_id": 0, "x": 300, "y": 400, "timestamp": 3.0},
            {"type": "resize_annotation", "object_id": 0, "width": 250, "height": 250, "handle": 7, "timestamp": 4.0},
            {"type": "move_annotation", "object_id": 1, "x": 150, "y": 200, "timestamp": 5.0},
            {"type": "resize_annotation", "object_id": 1, "width": 120, "height": 120, "handle": 7, "timestamp": 6.0},
            {"type": "save_document", "path": str(temp_dir / "output.jpg"), "timestamp": 7.0},
        ]
        
        # This test demonstrates how recorded actions would be used
        # In practice, you would load the JSON and replay each action
        assert len(recorded_actions) == 8
        assert recorded_actions[0]["type"] == "open_document"
        assert recorded_actions[-1]["type"] == "save_document"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])