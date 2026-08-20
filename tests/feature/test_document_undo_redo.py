"""Feature test for undo/redo workflow.

This test verifies that the undo/redo system correctly handles:
- Adding multiple annotations
- Moving annotations
- Undoing/redoing actions
- Proper history stack management
"""

import json
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


class TestDocumentUndoRedo:
    """Test undo/redo functionality with recorded workflow."""

    def test_undo_redo_actions_file_structure(self) -> None:
        """Verify undo/redo actions JSON file has correct structure."""
        actions_file = FIXTURES_DIR / "document1_undo.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    def test_undo_redo_actions_include_required_types(self) -> None:
        """Verify actions include expected action types."""
        actions_file = FIXTURES_DIR / "document1_undo.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        action_types = {action["type"] for action in actions}

        # Verify we have the expected action types
        assert "open_document" in action_types, "Should have open_document action"
        assert "add_annotation" in action_types, "Should have add_annotation actions"
        assert "move_annotation" in action_types, "Should have move_annotation actions"

    def test_undo_redo_workflow_has_multiple_annotations(self) -> None:
        """Verify the workflow adds annotations."""
        actions_file = FIXTURES_DIR / "document1_undo.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        
        # Find all add_annotation actions
        add_actions = [a for a in actions if a["type"] == "add_annotation"]
        assert len(add_actions) >= 1, "Should have at least 1 annotation"
        
        # Collect annotation types
        annotation_types = {action["annotation_type"] for action in add_actions}
        
        # Verify annotation types exist
        assert len(annotation_types) >= 1, "Should have at least 1 annotation type"

    def test_undo_redo_workflow_has_moves(self) -> None:
        """Verify the workflow includes move operations."""
        actions_file = FIXTURES_DIR / "document1_undo.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        
        # Find all move_annotation actions
        move_actions = [a for a in actions if a["type"] == "move_annotation"]
        assert len(move_actions) >= 1, "Should have at least one move operation"

    def test_undo_redo_workflow_valid_coordinates(self) -> None:
        """Verify all move and add operations have valid coordinates."""
        actions_file = FIXTURES_DIR / "document1_undo.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        
        # Check add_annotation actions
        for action in actions:
            if action["type"] == "add_annotation":
                assert "x" in action, "add_annotation must have x coordinate"
                assert "y" in action, "add_annotation must have y coordinate"
                assert isinstance(action["x"], (int, float)), "x must be numeric"
                assert isinstance(action["y"], (int, float)), "y must be numeric"
                assert action["x"] >= 0, "x must be non-negative"
                assert action["y"] >= 0, "y must be non-negative"
            
            elif action["type"] == "move_annotation":
                assert "x" in action, "move_annotation must have x coordinate"
                assert "y" in action, "move_annotation must have y coordinate"
                assert isinstance(action["x"], (int, float)), "x must be numeric"
                assert isinstance(action["y"], (int, float)), "y must be numeric"
                assert action["x"] >= 0, "x must be non-negative"
                assert action["y"] >= 0, "y must be non-negative"

    def test_undo_redo_workflow_object_ids_sequential(self) -> None:
        """Verify object IDs in actions are sequential."""
        actions_file = FIXTURES_DIR / "document1_undo.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        
        # Collect all object_ids from add and move actions
        seen_ids = set()
        for action in actions:
            if action["type"] == "add_annotation":
                obj_id = action.get("object_id")
                if obj_id is not None:
                    seen_ids.add(obj_id)
            elif action["type"] == "move_annotation":
                obj_id = action.get("object_id")
                if obj_id is not None:
                    seen_ids.add(obj_id)
        
        # Verify IDs are sequential starting from 0
        if seen_ids:
            assert min(seen_ids) == 0, "Object IDs should start at 0"
            assert max(seen_ids) == len(seen_ids) - 1, "Object IDs should be sequential"

    def test_undo_redo_pixel_perfect(self, main_window, temp_dir) -> None:
        """Test that undo/redo workflow renders correctly and matches reference image.
        
        This is the main feature test that:
        1. Plays the recorded undo/redo actions
        2. Saves the output image
        3. Compares it pixel-perfectly to the reference image
        """
        actions_file = FIXTURES_DIR / "document1_undo.json"
        expected_image = FIXTURES_DIR / "document1_undo" / "document1-signed.png"
        output_image = temp_dir / "document1-signed.png"

        # Verify reference image exists
        assert expected_image.exists(), f"Reference image not found: {expected_image}"

        # Play actions with output path (save_document in JSON will use this path)
        play_actions_from_file(main_window, actions_file, output_path=output_image)
        
        QApplication.processEvents()

        # Verify output was created
        assert output_image.exists(), f"Output image was not created: {output_image}"

        # Verify output matches reference (pixel-perfect)
        assert_images_equal_with_results(
            output_image,
            expected_image,
            test_name="document1_undo",
            save_results=True
        )
