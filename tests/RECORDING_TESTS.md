# Recording Feature Tests

This document explains how to record new feature tests for the Signer application.

## Overview

The test recording system allows developers to:
1. Perform actions manually in the application
2. Have those actions automatically recorded to a JSON file
3. Use the recorded actions to create automated feature tests

## Enabling Recording

Set the environment variable `SIGNER_RECORD_ACTIONS=1` before running the application:

```bash
# Linux/macOS
export SIGNER_RECORD_ACTIONS=1
python -m signer

# Windows PowerShell
$env:SIGNER_RECORD_ACTIONS=1
python -m signer

# Windows CMD
set SIGNER_RECORD_ACTIONS=1
python -m signer
```

## What Gets Recorded

The following actions are automatically captured:

| Action | Recorded Data |
|--------|---------------|
| Open document | File path |
| Open signature | File path |
| Add annotation (vector) | Type, position (x,y), page |
| Add text annotation | Text content, position, page |
| Move annotation | Object ID, new position (x,y) |
| Resize annotation | Object ID, new size (width,height), handle used |
| Change color | Object ID, color hex value |
| Change page | Page index |
| Save document | Output file path |

## Recording Workflow

1. **Start the application with recording enabled**
   ```bash
   SIGNER_RECORD_ACTIONS=1 python -m signer
   ```

2. **Perform your test scenario**
   - Open a document
   - Add signatures, checkmarks, text, arrows
   - Move and resize annotations
   - Change colors
   - Navigate between pages
   - Save the document

3. **Close the application**
   - The recorded actions will be printed to stdout
   - A JSON file will be saved to `tests/recorded_actions/recorded_actions_<timestamp>.json`

4. **Create the reference image**
   - The saved output from step 2 becomes your reference image
   - Copy it to `examples/<name>-expected.jpg`

5. **Create the feature test**
   - Use the recorded actions JSON as a guide
   - Write a test in `tests/feature/` that reproduces the steps
   - Use `assert_images_equal()` to compare output with reference

## Recorded Actions Format

```json
{
  "version": "1.0",
  "actions": [
    {
      "type": "open_document",
      "path": "/path/to/document.pdf",
      "timestamp": 1234567890.123
    },
    {
      "type": "open_signature",
      "path": "/path/to/signature.png",
      "timestamp": 1234567891.456
    },
    {
      "type": "add_annotation",
      "annotation_type": "checkmark",
      "x": 400.0,
      "y": 300.0,
      "page": 0,
      "object_id": 0,
      "timestamp": 1234567892.789
    },
    {
      "type": "move_annotation",
      "object_id": 0,
      "x": 300.0,
      "y": 400.0,
      "timestamp": 1234567893.012
    },
    {
      "type": "resize_annotation",
      "object_id": 0,
      "width": 250.0,
      "height": 250.0,
      "handle": 7,
      "timestamp": 1234567894.345
    },
    {
      "type": "change_color",
      "object_id": 0,
      "color": "#ff0000",
      "timestamp": 1234567895.678
    },
    {
      "type": "change_page",
      "page": 1,
      "timestamp": 1234567896.901
    },
    {
      "type": "save_document",
      "path": "/path/to/output.jpg",
      "timestamp": 1234567897.234
    }
  ]
}
```

## Creating a Feature Test from Recording

### 1. Copy the recorded actions to a test file

```python
# tests/feature/test_my_new_feature.py
import pytest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QFileDialog

from signer.main_window import MainWindow
from signer.objects import AnnotationType
from tests.utils.image_comparison import assert_images_equal

class TestMyNewFeature:
    @pytest.fixture
    def main_window(self, qapp, temp_dir):
        # ... setup code from conftest.py ...
    
    def test_my_feature(self, main_window, sample_pdf, sample_signature, temp_dir):
        reference_image = Path(__file__).parent.parent / "examples" / "my-feature-expected.jpg"
        
        if not reference_image.exists():
            pytest.skip(f"Reference image not found: {reference_image}")
        
        output_path = temp_dir / "my-feature-test.jpg"
        diff_path = temp_dir / "my-feature-diff.jpg"
        
        # Reproduce recorded actions
        main_window.open_document(str(sample_pdf))
        main_window._load_signature_file(str(sample_signature), at_default_position=True)
        
        sig_obj = main_window.canvas.selected
        sig_obj.x = 300.0  # from recorded action
        sig_obj.y = 400.0
        main_window.canvas.objectChanged.emit()
        
        sig_obj.set_scaled_size(250.0, 250.0)  # from recorded action
        main_window.canvas.objectChanged.emit()
        
        main_window._add_vector(AnnotationType.CHECKMARK)
        check_obj = main_window.canvas.selected
        check_obj.x = 150.0
        check_obj.y = 200.0
        main_window.canvas.objectChanged.emit()
        
        check_obj.set_scaled_size(120.0, 120.0)
        main_window.canvas.objectChanged.emit()
        
        with patch.object(QFileDialog, 'getSaveFileName', 
                         return_value=(str(output_path), "JPEG files (*.jpg *.jpeg)")):
            main_window.save_signed_document()
        
        assert_images_equal(output_path, reference_image, tolerance=0, diff_output_path=diff_path)
```

### 2. Create the reference image

Run the test once (it will fail), then copy the generated output to the examples folder:

```bash
# Run test (will fail because reference doesn't exist)
pytest tests/feature/test_my_new_feature.py -v

# Copy the generated output as reference
cp /tmp/.../my-feature-test.jpg examples/my-feature-expected.jpg

# Run test again (should pass)
pytest tests/feature/test_my_new_feature.py -v
```

## Best Practices

1. **Use descriptive test names**: `test_document1_signature_checkmark_pixel_perfect`
2. **Keep tests focused**: One test per feature scenario
3. **Use fixtures**: Leverage `conftest.py` fixtures for common setup
4. **Handle missing references gracefully**: Use `pytest.skip()` when reference image doesn't exist
5. **Save diff images**: Always provide `diff_output_path` for debugging failures
6. **Test pixel-perfect by default**: Use `tolerance=0` for exact matching
7. **Document the scenario**: Add docstrings explaining what the test verifies

## Troubleshooting

### Recording not working?
- Ensure `SIGNER_RECORD_ACTIONS=1` is set BEFORE starting the application
- Check that the `tests` package is importable (run from project root)
- Verify the application imports `setup_recording_if_enabled` in `app.py`

### Actions not captured?
- Some actions may not be hooked yet (file an issue or add the hook)
- Check the console for "ACTION RECORDING ENABLED" message
- Verify the patched methods are being called

### Test fails with image mismatch?
- Check the diff image at `diff_output_path`
- Verify the reference image is correct
- Ensure the test reproduces the exact same steps
- Check for non-deterministic behavior (random positions, timestamps)

## Extending the Recorder

To record additional actions:

1. Add a new `record_*` method to `ActionRecorder` in `tests/utils/test_helpers.py`
2. Add the corresponding patch in `patch_main_window_for_recording` in `tests/recording/action_recorder.py`
3. Update the action type documentation above

## Disabling Recording

Simply don't set the environment variable, or set it to anything other than "1":

```bash
# Normal run without recording
python -m signer

# Explicitly disable
SIGNER_RECORD_ACTIONS=0 python -m signer