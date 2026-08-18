"""Feature test for checkmark annotation workflow."""

import json
from pathlib import Path

import pytest

from signer.main_window import MainWindow
from signer.settings import SettingsStore
from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


class TestDocument1Checkmark:
    """Test checkmark annotation workflow on document1.pdf."""

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

    def test_document1_checkmark_pixel_perfect(self, main_window, temp_dir):
        """Test that checkmark annotation renders correctly and matches reference."""
        actions_file = FIXTURES_DIR / "document1_checkmark.json"
        expected_image = FIXTURES_DIR / "document1_checkmark" / "document1-signed.png"
        output_image = temp_dir / "document1-signed.png"

        # Play actions with output path
        play_actions_from_file(main_window, actions_file, output_path=output_image)
        
        QApplication.processEvents()

        # Verify output matches reference (pixel-perfect)
        assert_images_equal_with_results(
            output_image,
            expected_image,
            test_name="document1_checkmark",
            tolerance=0,  # Pixel-perfect comparison
            save_results=True
        )

    def test_document1_checkmark_actions_file_structure(self):
        """Verify actions JSON file has correct structure."""
        actions_file = FIXTURES_DIR / "document1_checkmark.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    def test_document1_checkmark_actions_include_required_types(self):
        """Verify all actions have required 'type' field."""
        actions_file = FIXTURES_DIR / "document1_checkmark.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        for i, action in enumerate(data.get("actions", [])):
            assert "type" in action, f"Action {i} missing 'type' field"
            assert isinstance(action["type"], str), f"Action {i} type must be string"

    def test_annotation_positions_are_valid(self):
        """Verify annotation positions are valid coordinates."""
        actions_file = FIXTURES_DIR / "document1_checkmark.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        for action in data.get("actions", []):
            if action.get("type") == "add_annotation":
                assert "x" in action, "add_annotation missing x coordinate"
                assert "y" in action, "add_annotation missing y coordinate"
                assert isinstance(action["x"], (int, float)), "x must be numeric"
                assert isinstance(action["y"], (int, float)), "y must be numeric"
                assert action["x"] >= 0, "x must be non-negative"
                assert action["y"] >= 0, "y must be non-negative"
