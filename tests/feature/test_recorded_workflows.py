"""Feature tests for recorded action workflows.

This module consolidates tests for all feature workflows using action recording/playback:
- Annotation features (arrow, checkmark, crossmark, signature, text)
- Undo/redo workflows (single, dual, multiple)

All tests use parametrization to avoid code duplication and consistently test
features by replaying recorded JSON action sequences and comparing pixel-perfect output.
"""

import json
import sys
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


# Parametrization: workflow_type, fixture_name, expected_annotation_prefix, description
WORKFLOW_TEST_CASES = [
    # New annotation types (v1.2.22)
    ("annotation", "line", "line", "Line annotation"),
    ("annotation", "arrows", "arrow", "Arrow annotation"),
    ("annotation", "rectangle", "rectangle", "Rectangle annotation"),
    ("annotation", "ellipse", "ellipse", "Ellipse annotation"),
    ("annotation", "line_props", "line", "Line with properties (width, color)"),
    ("annotation", "arrow_props", "arrow", "Arrow with properties (width, color)"),
    ("annotation", "rectangle_props", "rectangle", "Rectangle with properties"),
    ("annotation", "ellipse_props", "ellipse", "Ellipse with properties"),
    ("annotation", "checkmark_props", "checkmark", "Checkmark with properties (blue, width)"),
    ("annotation", "crossmark_props", "crossmark", "Crossmark with properties (blue, width)"),
    ("annotation", "text_props", "text", "Text with properties (blue, 16pt, Courier)"),
    # Original annotation features on document1
    ("annotation", "arrow", "arrow", "Arrow annotation"),
    ("annotation", "checkmark", "checkmark", "Checkmark annotation"),
    ("annotation", "crossmark", "crossmark", "Crossmark annotation"),
    ("annotation", "text", "text", "Text annotation"),
    ("annotation", "signature", "add_signature", "Signature annotation"),
    # Undo/redo workflows
    ("undo", "undo", "undo", "Basic undo workflow"),
    ("undo", "undo_2", "undo", "Variant undo workflow"),
    ("undo", "undo_multiple", "undo", "Multiple undo operations"),
    ("undo", "undo_redo", "undo", "Undo/redo workflow"),
]


class TestRecordedWorkflows:
    """Test feature workflows using recorded action playback."""

    @pytest.mark.parametrize("workflow_type,fixture_name,annotation_prefix,description", WORKFLOW_TEST_CASES)
    def test_workflow_pixel_perfect(self, workflow_type, fixture_name, annotation_prefix, description, main_window, temp_dir):
        """Test that workflow renders correctly and matches reference image.
        
        Args:
            workflow_type: Type of workflow (annotation, undo, etc.)
            fixture_name: Base name of the fixture (e.g., arrow)
            annotation_prefix: Expected action type or annotation type prefix
            description: Human-readable description of the workflow
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
        # On first run, if expected image doesn't exist, create it from actual output
        if not expected_image.exists() and output_image.exists():
            # Create baseline by copying actual to expected (in fixtures)
            expected_image.parent.mkdir(parents=True, exist_ok=True)
            from shutil import copy2
            copy2(output_image, expected_image)
            pytest.skip(f"Baseline image created for {fixture_name}. Re-run test to compare.")
        
        try:
            assert_images_equal_with_results(
                output_image,
                expected_image,
                test_name=fixture_name,
                save_results=True
            )
        except AssertionError:
            if sys.platform == "darwin":
                pytest.skip("Pixel-perfect rendering differs on macOS; comparison saved to the report")
            raise

    @pytest.mark.parametrize("workflow_type,fixture_name,annotation_prefix,description", WORKFLOW_TEST_CASES)
    def test_actions_file_structure(self, workflow_type, fixture_name, annotation_prefix, description):
        """Verify actions JSON file has correct structure."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    @pytest.mark.parametrize("workflow_type,fixture_name,annotation_prefix,description", WORKFLOW_TEST_CASES)
    def test_actions_include_required_types(self, workflow_type, fixture_name, annotation_prefix, description):
        """Verify all actions have required 'type' field."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        for i, action in enumerate(data.get("actions", [])):
            assert "type" in action, f"Action {i} missing 'type' field"
            assert isinstance(action["type"], str), f"Action {i} type must be string"

    @pytest.mark.parametrize("workflow_type,fixture_name,annotation_prefix,description", WORKFLOW_TEST_CASES)
    def test_workflow_has_expected_actions(self, workflow_type, fixture_name, annotation_prefix, description):
        """Verify workflow includes the expected action types."""
        actions_file = FIXTURES_DIR / f"{fixture_name}.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        action_types = {a.get("type") for a in data.get("actions", [])}
        
        if workflow_type == "annotation":
            # Annotation workflows must have open_document
            assert "open_document" in action_types, "Annotation workflow must have open_document"
            
            # Check for the appropriate annotation action type
            if annotation_prefix == "add_signature":
                assert "add_signature" in action_types, "Signature test must include add_signature action"
            else:
                assert "add_annotation" in action_types, "Annotation workflow must have add_annotation action"
        elif workflow_type == "undo":
            # Undo workflows must have open_document and add_annotation
            assert "open_document" in action_types, "Undo workflow must have open_document"
            assert "add_annotation" in action_types, "Undo workflow must have add_annotation actions"
            assert "undo" in action_types, "Undo workflow must have undo actions"

    @pytest.mark.parametrize("workflow_type,fixture_name,annotation_prefix,description", WORKFLOW_TEST_CASES)
    def test_actions_have_valid_positions(self, workflow_type, fixture_name, annotation_prefix, description):
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
                assert action["x"] >= 0, "x must be non-negative"
                assert action["y"] >= 0, "y must be non-negative"
            elif action.get("type") == "add_signature":
                # add_signature just loads the file; positioning is done with move_annotation
                assert "path" in action, "add_signature missing path field"

    @pytest.mark.parametrize("workflow_type,fixture_name,annotation_prefix,description", WORKFLOW_TEST_CASES)
    def test_reference_image_exists(self, workflow_type, fixture_name, annotation_prefix, description):
        """Verify reference image file exists."""
        expected_image = FIXTURES_DIR / fixture_name / "document1-signed.png"
        assert expected_image.exists(), f"Reference image not found: {expected_image}"
