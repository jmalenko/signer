"""Feature test for signature annotation workflow."""

import json
from pathlib import Path

import pytest

from signer.main_window import MainWindow
from signer.settings import SettingsStore
from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


class TestDocument1Signature:
    """Test signature annotation workflow on document1.pdf."""

    @pytest.fixture
    def main_window(self, qapp, temp_dir):
        """Create isolated main_window for testing."""
        # Create isolated settings (no user config)
        settings_store = SettingsStore(app_name="SignerTest")
        settings_store._settings_path = temp_dir / "config_never_exists.json"
        
        # Load default settings (won't exist, so returns defaults)
        settings = settings_store.load()
        
        # Create main window with isolated settings
        window = MainWindow(settings_store=settings_store, settings=settings)
        window.show()
        yield window
        window.close()

    def test_document1_signature_pixel_perfect(self, main_window, temp_dir):
        """Test that signature annotation renders correctly and matches reference."""
        actions_file = FIXTURES_DIR / "document1_signature.json"
        expected_image = FIXTURES_DIR / "document1_signature" / "document1-signed.png"
        output_image = temp_dir / "document1-signed.png"

        # Play actions with output path
        play_actions_from_file(main_window, actions_file, output_path=output_image)
        
        QApplication.processEvents()

        # Verify output matches reference (pixel-perfect)
        assert_images_equal_with_results(
            output_image,
            expected_image,
            test_name="document1_signature",
            save_results=True
        )

    def test_document1_signature_actions_file_structure(self):
        """Verify the actions file has the expected structure."""
        actions_file = FIXTURES_DIR / "document1_signature.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"
        
        with open(actions_file) as f:
            data = json.load(f)
        
        assert "actions" in data
        assert isinstance(data["actions"], list)
        assert len(data["actions"]) > 0

    def test_document1_signature_actions_include_required_types(self):
        """Verify actions include required action types."""
        actions_file = FIXTURES_DIR / "document1_signature.json"
        with open(actions_file) as f:
            data = json.load(f)
        
        action_types = [action["type"] for action in data["actions"]]
        
        # Signature tests require: open_document, add_signature, save_document
        assert "open_document" in action_types
        assert "add_signature" in action_types
        assert "save_document" in action_types

    def test_annotation_positions_are_valid(self):
        """Verify annotation positions are numeric and reasonable."""
        actions_file = FIXTURES_DIR / "document1_signature.json"
        with open(actions_file) as f:
            data = json.load(f)
        
        for action in data["actions"]:
            if action["type"] == "move_annotation":
                # Verify x, y are numeric
                assert isinstance(action["x"], (int, float))
                assert isinstance(action["y"], (int, float))
                
                # Verify within reasonable bounds (canvas is typically 300 DPI render)
                # Signature can be placed anywhere on page
                assert 0 <= action["x"] <= 3000, f"x out of bounds: {action['x']}"
                assert 0 <= action["y"] <= 3000, f"y out of bounds: {action['y']}"
