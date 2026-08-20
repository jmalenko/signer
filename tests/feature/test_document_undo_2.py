"""Feature test for undo operations (second variant).

This test verifies that the undo system correctly handles:
- Multiple consecutive undos
- Undo after multiple operations
- Complex workflows with multiple annotations
"""

import json
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


class TestDocumentUndo2:
    """Test undo operations (second variant) with recorded workflow."""

    def test_undo_2_actions_file_structure(self) -> None:
        """Verify undo_2 actions JSON file has correct structure."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    def test_undo_2_actions_include_required_types(self) -> None:
        """Verify actions include expected action types."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        action_types = {action["type"] for action in actions}

        # Verify we have the expected action types
        assert "open_document" in action_types, "Should have open_document action"
        assert "add_annotation" in action_types, "Should have add_annotation actions"
        assert "move_annotation" in action_types, "Should have move_annotation actions"
        assert "undo" in action_types, "Should have undo actions"

    def test_undo_2_workflow_has_multiple_annotations(self) -> None:
        """Verify workflow creates >= 2 annotations."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        add_actions = [a for a in actions if a["type"] == "add_annotation"]

        assert len(add_actions) >= 2, f"Should have >= 2 annotations, got {len(add_actions)}"

    def test_undo_2_workflow_has_multiple_undos(self) -> None:
        """Verify workflow has >= 2 undo operations."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        undo_actions = [a for a in actions if a["type"] == "undo"]

        assert len(undo_actions) >= 2, f"Should have >= 2 undo operations, got {len(undo_actions)}"

    def test_undo_2_workflow_has_moves(self) -> None:
        """Verify workflow has >= 2 move operations."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        move_actions = [a for a in actions if a["type"] == "move_annotation"]

        assert len(move_actions) >= 2, f"Should have >= 2 move operations, got {len(move_actions)}"

    def test_undo_2_workflow_valid_coordinates(self) -> None:
        """Verify all coordinates are numeric and non-negative."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        
        # Check add_annotation and move_annotation coordinates
        for action in actions:
            if action["type"] == "add_annotation":
                x, y = action.get("x"), action.get("y")
                assert isinstance(x, (int, float)), f"x must be numeric, got {type(x)}"
                assert isinstance(y, (int, float)), f"y must be numeric, got {type(y)}"
                assert x >= 0 and y >= 0, f"Coordinates must be non-negative: ({x}, {y})"
            elif action["type"] == "move_annotation":
                x, y = action.get("x"), action.get("y")
                assert isinstance(x, (int, float)), f"x must be numeric, got {type(x)}"
                assert isinstance(y, (int, float)), f"y must be numeric, got {type(y)}"
                assert x >= 0 and y >= 0, f"Coordinates must be non-negative: ({x}, {y})"

    def test_undo_2_workflow_object_ids_sequential(self) -> None:
        """Verify object IDs are sequential (0, 1, 2, ...)."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        object_ids = set()
        
        # Collect all object IDs from add_annotation actions
        for action in actions:
            if action["type"] == "add_annotation":
                obj_id = action.get("object_id")
                object_ids.add(obj_id)
        
        # Verify IDs are sequential starting from 0
        if object_ids:
            max_id = max(object_ids)
            expected_ids = set(range(max_id + 1))
            assert object_ids == expected_ids, f"IDs not sequential: {sorted(object_ids)}"

    def test_undo_2_pixel_perfect(self, main_window, temp_dir) -> None:
        """Verify undo_2 workflow produces expected output (pixel-perfect comparison)."""
        actions_file = FIXTURES_DIR / "document1_undo_2.json"
        expected_image = FIXTURES_DIR / "document1_undo_2" / "document1-signed.png"
        output_image = temp_dir / "document1-signed.png"
        
        # Play actions with output path (save_document in JSON will use this path)
        play_actions_from_file(main_window, actions_file, output_path=output_image)
        
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Verify output was created
        assert output_image.exists(), f"Output image was not created: {output_image}"
        
        # If reference image doesn't exist, copy output as reference (first generation)
        if not expected_image.exists():
            import shutil
            expected_image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(output_image, expected_image)
            pytest.skip("Reference image generated on first run")
        
        # Verify output matches reference (pixel-perfect)
        assert_images_equal_with_results(
            output_image,
            expected_image,
            test_name="document1_undo_2",
            save_results=True
        )
