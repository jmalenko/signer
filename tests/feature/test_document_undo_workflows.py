"""Parameterized feature tests for undo/redo workflows.

This test suite uses pytest.mark.parametrize to test multiple undo workflow
fixtures with identical test logic, eliminating code duplication.
"""

import json
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results
from PySide6.QtWidgets import QApplication


# Test parameters: fixture name, fixture path, expected image path, test name
UNDO_FIXTURES = [
    (
        "document1_undo",
        FIXTURES_DIR / "document1_undo.json",
        FIXTURES_DIR / "document1_undo" / "document1-signed.png",
        "document1_undo",
    ),
    (
        "document1_undo_2",
        FIXTURES_DIR / "document1_undo_2.json",
        FIXTURES_DIR / "document1_undo_2" / "document1-signed.png",
        "document1_undo_2",
    ),
    (
        "document1_undo_multiple",
        FIXTURES_DIR / "document1_undo_multiple.json",
        FIXTURES_DIR / "document1_undo_multiple" / "document1-signed.png",
        "document1_undo_multiple",
    ),
]


class TestUndoWorkflows:
    """Parameterized tests for undo/redo workflows."""

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_actions_file_structure(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify undo actions JSON file has correct structure."""
        assert actions_file.exists(), f"Actions file not found: {actions_file}"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify structure
        assert "actions" in data, "Missing 'actions' key in JSON"
        assert isinstance(data["actions"], list), "'actions' must be a list"
        assert len(data["actions"]) > 0, "Actions list cannot be empty"

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_actions_include_required_types(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify actions include expected action types."""
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        action_types = {action["type"] for action in actions}

        # Verify we have the expected action types
        assert "open_document" in action_types, "Should have open_document action"
        assert "add_annotation" in action_types, "Should have add_annotation actions"
        assert "move_annotation" in action_types, "Should have move_annotation actions"
        assert "undo" in action_types, "Should have undo actions"

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_workflow_has_annotations(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify workflow creates >= 1 annotation."""
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        add_actions = [a for a in actions if a["type"] == "add_annotation"]

        assert len(add_actions) >= 1, f"Should have >= 1 annotation, got {len(add_actions)}"

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_workflow_has_undos(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify workflow has >= 1 undo operation."""
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        undo_actions = [a for a in actions if a["type"] == "undo"]

        assert len(undo_actions) >= 1, f"Should have >= 1 undo operation, got {len(undo_actions)}"

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_workflow_has_moves(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify workflow has >= 1 move operation."""
        with open(actions_file) as f:
            data = json.load(f)

        actions = data["actions"]
        move_actions = [a for a in actions if a["type"] == "move_annotation"]

        assert len(move_actions) >= 1, f"Should have >= 1 move operation, got {len(move_actions)}"

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_workflow_valid_coordinates(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify all coordinates are numeric and non-negative."""
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

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_workflow_object_ids_sequential(
        self, fixture_name: str, actions_file: Path, expected_image: Path, test_name: str
    ) -> None:
        """Verify object IDs are sequential (0, 1, 2, ...)."""
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

    @pytest.mark.parametrize(
        "fixture_name,actions_file,expected_image,test_name",
        UNDO_FIXTURES,
        ids=[f[0] for f in UNDO_FIXTURES],
    )
    def test_pixel_perfect(
        self,
        fixture_name: str,
        actions_file: Path,
        expected_image: Path,
        test_name: str,
        main_window,
        temp_dir,
    ) -> None:
        """Verify undo workflow produces expected output (pixel-perfect comparison)."""
        output_image = temp_dir / "document1-signed.png"

        # Play actions with output path (save_document in JSON will use this path)
        play_actions_from_file(main_window, actions_file, output_path=output_image)

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
            output_image, expected_image, test_name=test_name, save_results=True
        )
