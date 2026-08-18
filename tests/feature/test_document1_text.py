"""Feature test for text annotation workflow on document1.pdf.

This test verifies the text annotation functionality by:
1. Opening document1.pdf
2. Adding a text annotation
3. Moving the text annotation
4. Saving the document
5. Comparing pixel-perfect with reference image
"""

import json
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


class TestDocument1Text:
    """Test text annotation workflow on document1.pdf."""

    def test_text_annotation_pixel_perfect(self, main_window, temp_dir):
        """Test that text annotation renders correctly and matches reference."""
        actions_file = FIXTURES_DIR / "document1_text.json"
        expected_image = FIXTURES_DIR / "document1_text" / "document1-signed.png"
        output_image = temp_dir / "document1-signed.png"

        # Play actions with output path
        play_actions_from_file(main_window, actions_file, output_path=output_image)
        
        QApplication.processEvents()

        # Verify output matches reference (pixel-perfect)
        assert_images_equal_with_results(
            output_image,
            expected_image,
            test_name="document1_text",
            save_results=True
        )

    def test_actions_file_structure(self):
        """Verify actions JSON file has correct structure."""
        actions_file = FIXTURES_DIR / "document1_text.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    def test_actions_include_required_types(self):
        """Verify all actions have required 'type' field."""
        actions_file = FIXTURES_DIR / "document1_text.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        for i, action in enumerate(data.get("actions", [])):
            assert "type" in action, f"Action {i} missing 'type' field"
            assert isinstance(action["type"], str), f"Action {i} type must be string"

    def test_includes_text_annotation_action(self):
        """Verify test includes add_annotation action for text."""
        actions_file = FIXTURES_DIR / "document1_text.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        annotation_actions = [a for a in data.get("actions", []) if a.get("type") == "add_annotation"]
        assert len(annotation_actions) > 0, "Test must include at least one add_annotation action"
        
        # Verify annotation is text
        first_annotation = annotation_actions[0]
        assert "annotation_type" in first_annotation, "add_annotation missing annotation_type"
        assert first_annotation["annotation_type"] == "text", "Expected text annotation"

    def test_annotation_positions_are_valid(self):
        """Verify annotation positions are valid coordinates."""
        actions_file = FIXTURES_DIR / "document1_text.json"
        
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
            elif action.get("type") == "move_annotation":
                assert "x" in action, "move_annotation missing x coordinate"
                assert "y" in action, "move_annotation missing y coordinate"
                assert isinstance(action["x"], (int, float)), "x must be numeric"
                assert isinstance(action["y"], (int, float)), "y must be numeric"

    def test_reference_image_exists(self):
        """Verify reference image file exists."""
        expected_image = FIXTURES_DIR / "document1_text" / "document1-signed.png"
        assert expected_image.exists(), f"Reference image not found: {expected_image}"
