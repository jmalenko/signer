"""Feature tests for document1.pdf annotation workflows.

This module consolidates tests for arrow, checkmark, crossmark, and signature
annotations using parametrization to avoid code duplication.

Each test fixture represents a recorded workflow:
- document1_arrow: Arrow annotation workflow
- document1_checkmark: Checkmark annotation workflow
- document1_crossmark: Crossmark annotation workflow
- document1_signature: Signature annotation workflow
"""

import json
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


# Parametrization: annotation_type, fixture_name, expected_annotation_prefix
ANNOTATION_TEST_CASES = [
    ("arrow", "document1_arrow", "arrow_"),
    ("checkmark", "document1_checkmark", "checkmark"),
    ("crossmark", "document1_crossmark", "crossmark"),
    ("text", "document1_text", "text"),
    ("signature", "document1_signature", "add_signature"),  # Signatures use add_signature action
]


class TestDocument1Annotations:
    """Test annotation workflows on document1.pdf using recorded actions."""

    @pytest.mark.parametrize("annotation_type,fixture_name,annotation_prefix", ANNOTATION_TEST_CASES)
    def test_annotation_pixel_perfect(self, annotation_type, fixture_name, annotation_prefix, main_window, temp_dir):
        """Test that annotation renders correctly and matches reference image.
        
        Args:
            annotation_type: Type of annotation (arrow, checkmark, etc.)
            fixture_name: Base name of the fixture (e.g., document1_arrow)
            annotation_prefix: Expected action type or annotation type prefix
            main_window: Pytest fixture providing isolated MainWindow
            temp_dir: Temporary directory for test outputs
        """
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        expected_image = FIXTURES_DIR / fixture_name / "document1-signed.png"
        output_image = temp_dir / "document1-signed.png"

        # Play actions with output path
        play_actions_from_file(main_window, actions_file, output_path=output_image)
        
        QApplication.processEvents()

        # Verify output matches reference (pixel-perfect)
        assert_images_equal_with_results(
            output_image,
            expected_image,
            test_name=fixture_name,
            save_results=True
        )

    @pytest.mark.parametrize("annotation_type,fixture_name,annotation_prefix", ANNOTATION_TEST_CASES)
    def test_actions_file_structure(self, annotation_type, fixture_name, annotation_prefix):
        """Verify actions JSON file has correct structure."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    @pytest.mark.parametrize("annotation_type,fixture_name,annotation_prefix", ANNOTATION_TEST_CASES)
    def test_actions_include_required_types(self, annotation_type, fixture_name, annotation_prefix):
        """Verify all actions have required 'type' field."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        for i, action in enumerate(data.get("actions", [])):
            assert "type" in action, f"Action {i} missing 'type' field"
            assert isinstance(action["type"], str), f"Action {i} type must be string"

    @pytest.mark.parametrize("annotation_type,fixture_name,annotation_prefix", ANNOTATION_TEST_CASES)
    def test_includes_correct_annotation_action(self, annotation_type, fixture_name, annotation_prefix):
        """Verify test includes the correct annotation action type."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        # Check for the appropriate action type based on annotation
        if annotation_prefix == "add_signature":
            # Signature tests use add_signature action
            action_types = [a.get("type") for a in data.get("actions", [])]
            assert "add_signature" in action_types, "Test must include add_signature action"
        else:
            # Vector annotations (arrow, checkmark, crossmark) use add_annotation
            annotation_actions = [a for a in data.get("actions", []) if a.get("type") == "add_annotation"]
            assert len(annotation_actions) > 0, "Test must include at least one add_annotation action"
            
            # Verify annotation matches expected type
            first_annotation = annotation_actions[0]
            assert "annotation_type" in first_annotation, "add_annotation missing annotation_type"
            assert first_annotation["annotation_type"].startswith(annotation_prefix), \
                f"Expected {annotation_prefix} annotation, got {first_annotation['annotation_type']}"

    @pytest.mark.parametrize("annotation_type,fixture_name,annotation_prefix", ANNOTATION_TEST_CASES)
    def test_annotation_positions_are_valid(self, annotation_type, fixture_name, annotation_prefix):
        """Verify annotation positions are valid coordinates."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        
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
            elif action.get("type") == "move_annotation" and annotation_prefix == "add_signature":
                # Signature movement positions
                assert isinstance(action["x"], (int, float))
                assert isinstance(action["y"], (int, float))
                assert 0 <= action["x"] <= 3000, f"x out of bounds: {action['x']}"
                assert 0 <= action["y"] <= 3000, f"y out of bounds: {action['y']}"

    @pytest.mark.parametrize("annotation_type,fixture_name,annotation_prefix", ANNOTATION_TEST_CASES)
    def test_reference_image_exists(self, annotation_type, fixture_name, annotation_prefix):
        """Verify reference image file exists."""
        expected_image = FIXTURES_DIR / fixture_name / "document1-signed.png"
        assert expected_image.exists(), f"Reference image not found: {expected_image}"
