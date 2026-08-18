"""Feature test: document1.pdf with signature and checkmark.

This test reproduces the recorded actions:
1. Open document1.pdf
2. Add signature from signature.png
3. Add checkmark annotation
4. Move and resize signature
5. Move and resize checkmark
6. Save as PNG (path is optional - if omitted, app uses default)
7. Compare pixel-perfect to reference image

To create/update the reference image:
1. Run: pytest tests/feature/test_document1_signature_checkmark.py::TestDocument1SignatureCheckmark::test_generate_reference_image -v
2. This will create/update the reference image at tests/fixtures/document1_actions/document1-signed.png
3. Then the pixel-perfect test will use this as the baseline

Structure:
- tests/fixtures/document1_actions.json: List of actions (open_document specifies target document)
- tests/fixtures/document1_actions/: Directory containing expected outputs
- tests/fixtures/document1_actions/document1-signed.png: Reference image for comparison

Notes:
- save_document action can optionally include "path" field
- If "path" is omitted, the application's default save behavior is used
"""

import json
import tempfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog

from signer.main_window import MainWindow
from signer.objects import AnnotationType, SignatureObject, VectorAnnotation
from signer.settings import AppSettings, SettingsStore
from tests.utils.image_comparison import assert_images_equal_with_results
from tests.conftest import FIXTURES_DIR, EXAMPLES_DIR
from tests.recording.action_player import play_actions_from_file


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

    def test_generate_reference_image(self, main_window, temp_dir):
        """Generate the reference image for this test.
        
        Run this test once to generate the reference image:
            pytest tests/feature/test_document1_signature_checkmark.py::TestDocument1SignatureCheckmark::test_generate_reference_image -v
        """
        
        actions_file = FIXTURES_DIR / "document1_actions.json"
        reference_image = FIXTURES_DIR / "document1_actions" / "document1-signed.png"
        output_path = reference_image
        
        if not actions_file.exists():
            pytest.skip(f"Actions file not found: {actions_file}")

        # Load actions
        with open(actions_file) as f:
            actions_data = json.load(f)
        
        # Create a temporary actions file with the reference output path
        temp_actions = temp_dir / "actions_with_ref_path.json"
        for action in actions_data.get("actions", []):
            if action.get("type") == "save_document":
                action["path"] = str(output_path)
                break
        
        with open(temp_actions, "w") as f:
            json.dump(actions_data, f, indent=2)

        # Play the recorded actions
        try:
            play_actions_from_file(main_window, temp_actions)
        except Exception as e:
            pytest.fail(f"Failed to execute actions: {e}")
        
        # Verify reference image was created
        assert output_path.exists(), f"Reference image not created at {output_path}"
        print(f"✓ Reference image generated: {output_path}")

    def test_document1_signature_checkmark_pixel_perfect(self, main_window, temp_dir):
        """Test the complete workflow using recorded actions with pixel-perfect verification."""
        
        # Reference image and actions file paths
        reference_image = FIXTURES_DIR / "document1_actions" / "document1-signed.png"
        actions_file = FIXTURES_DIR / "document1_actions.json"
        output_path = temp_dir / "document1-signed.png"

        if not reference_image.exists():
            pytest.skip(
                f"Reference image not found: {reference_image}\n"
                f"Generate it first by running:\n"
                f"  pytest {__file__}::TestDocument1SignatureCheckmark::test_generate_reference_image -v"
            )
        if not actions_file.exists():
            pytest.skip(f"Actions file not found: {actions_file}")

        # Load actions and update save path
        with open(actions_file) as f:
            actions_data = json.load(f)
        
        # Modify the save_document action to use our temp output path
        for action in actions_data.get("actions", []):
            if action.get("type") == "save_document":
                action["path"] = str(output_path)
                break

        # Write modified actions to a temp file
        temp_actions = temp_dir / "actions_test.json"
        with open(temp_actions, "w") as f:
            json.dump(actions_data, f, indent=2)

        # Play the recorded actions
        try:
            play_actions_from_file(main_window, temp_actions)
        except Exception as e:
            pytest.fail(f"Failed to execute actions: {e}")

        # Verify output was created
        assert output_path.exists(), f"Output image not created at {output_path}"

        # Compare with reference image (pixel-perfect) - saves to test-results/
        assert_images_equal_with_results(
            output_path, 
            reference_image, 
            test_name="document1_actions",
            tolerance=0,
            save_results=True
        )

    def test_actions_file_structure(self):
        """Verify the actions file has the expected structure."""
        actions_file = FIXTURES_DIR / "document1_actions.json"
        assert actions_file.exists(), "Actions file should exist"

        with open(actions_file) as f:
            data = json.load(f)

        # Verify actions array exists (document field is optional and may not be present)
        assert "actions" in data, "Actions file must contain 'actions' key"
        assert len(data["actions"]) >= 5, "Must have at least 5 actions (open_doc, open_sig, add_ann, move, resize, save)"

        # Verify first action is open_document
        assert data["actions"][0]["type"] == "open_document", "First action should be open_document"
        assert "document1.pdf" in data["actions"][0]["path"], "Document path should contain document1.pdf"

        # Verify last action is save_document
        assert data["actions"][-1]["type"] == "save_document", "Last action should be save_document"
        # Note: save_document path is optional
        
        # Verify no timestamp or version fields in actions
        for action in data["actions"]:
            assert "timestamp" not in action, f"Action {action['type']} should not have timestamp"
        assert "version" not in data, "Actions data should not have version field"

    def test_actions_include_required_types(self):
        """Verify the actions include the required action types."""
        actions_file = FIXTURES_DIR / "document1_actions.json"
        if not actions_file.exists():
            pytest.skip(f"Actions file not found: {actions_file}")

        with open(actions_file) as f:
            data = json.load(f)

        action_types = {action["type"] for action in data["actions"]}
        
        # Should have these action types
        required_types = {"open_document", "open_signature", "add_annotation", "save_document"}
        assert required_types.issubset(action_types), f"Missing required actions: {required_types - action_types}"

    def test_annotation_positions_are_valid(self):
        """Verify that annotation positions in the actions are valid."""
        actions_file = FIXTURES_DIR / "document1_actions.json"
        if not actions_file.exists():
            pytest.skip(f"Actions file not found: {actions_file}")

        with open(actions_file) as f:
            data = json.load(f)

        for action in data["actions"]:
            if action["type"] == "add_annotation":
                x = action.get("x")
                y = action.get("y")
                page = action.get("page")
                assert x is not None, "add_annotation must have x coordinate"
                assert y is not None, "add_annotation must have y coordinate"
                assert page is not None, "add_annotation must have page"
                assert isinstance(x, (int, float)), "x must be numeric"
                assert isinstance(y, (int, float)), "y must be numeric"
                assert x >= 0, "x must be >= 0"
                assert y >= 0, "y must be >= 0"
                assert page >= 0, "page must be >= 0"