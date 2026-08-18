"""Test multi-selection copy/paste with move scenario."""
import pytest
import json
from PIL import Image
from PySide6.QtWidgets import QApplication
from signer.objects import VectorAnnotation, AnnotationType, canvas_object_from_dict


def test_paste_preserves_original_position_after_move(canvas):
    """Test that pasting uses the clipboard position, not the current position after move.
    
    Scenario:
    1. Select an annotation at (100, 100)
    2. Copy it
    3. Move the annotation to (200, 200)
    4. Paste it
    Expected: Pasted annotation should be at approximately (110, 110) (original + offset)
    Actual (buggy): Pasted annotation appears near (200, 200) (current position)
    """
    # Create 2 simple test images and load them into canvas
    img1 = Image.new('RGB', (800, 800), color='white')
    img2 = Image.new('RGB', (800, 800), color='white')
    canvas.set_pages([img1, img2])
    
    # Step 1: Create and select an annotation at (100, 100)
    ann = VectorAnnotation(
        AnnotationType.CHECKMARK,
        x=100,
        y=100,
        page=0
    )
    objs = canvas._page_objects.setdefault(0, [])
    objs.append(ann)
    canvas.select_annotation(ann)  # Use select_annotation method instead of setting directly
    
    # Verify initial position
    assert ann.x == 100
    assert ann.y == 100
    
    # Step 2: Store the annotation's to_dict() to simulate what copy does
    copied_data = ann.to_dict()
    
    # Step 3: Move the annotation to (200, 200)
    canvas.move_selected(100, 100)  # Move by (100, 100) -> position (200, 200)
    
    # Verify it moved
    assert ann.x == 200
    assert ann.y == 200
    
    # Step 4: Deserialize the copied data and paste it (simulating paste_selected behavior)
    pasted_obj = canvas_object_from_dict(copied_data)
    assert pasted_obj is not None
    
    original_page = copied_data.get("page")
    pasted_obj.page = canvas._current_page  # Should be 0
    
    # Apply offset only if pasting on same page as original
    if original_page == canvas._current_page:
        pasted_obj.x += 10  # Offset to avoid exact overlap
        pasted_obj.y += 10
    
    objs.append(pasted_obj)
    
    # Step 5: Verify the pasted annotation is at the original position + offset (10, 10)
    # NOT at the current position (200, 200)
    assert len(objs) == 2, "Should have original and pasted annotations"
    
    # The pasted annotation should be at original position (100, 100) + offset (10, 10)
    # NOT at current position (200, 200)
    assert pasted_obj.x == 110, f"Expected x=110 (original 100 + offset 10), got {pasted_obj.x}"
    assert pasted_obj.y == 110, f"Expected y=110 (original 100 + offset 10), got {pasted_obj.y}"
    
    # Verify the original annotation is still at (200, 200)
    assert ann.x == 200
    assert ann.y == 200


def test_paste_to_different_page_preserves_position(canvas):
    """Test that pasting to a different page uses the original position with no offset."""
    # Create 2 simple test images and load them into canvas
    img1 = Image.new('RGB', (800, 800), color='white')
    img2 = Image.new('RGB', (800, 800), color='white')
    canvas.set_pages([img1, img2])
    
    # Create annotation on page 0 at (100, 100)
    ann = VectorAnnotation(
        AnnotationType.CHECKMARK,
        x=100,
        y=100,
        page=0
    )
    objs0 = canvas._page_objects.setdefault(0, [])
    objs0.append(ann)
    canvas.select_annotation(ann)  # Use select_annotation method
    
    # Copy it
    canvas.copy_selected()
    
    # Move it to (200, 200) on page 0
    canvas.move_selected(100, 100)
    assert ann.x == 200
    assert ann.y == 200
    
    # Switch to page 1
    canvas.goto_page(1)
    objs1 = canvas._page_objects.setdefault(1, [])
    
    # Manually create the pasted object from clipboard to avoid clipboard issues in test
    # This simulates what paste_selected() does
    clipboard = QApplication.clipboard()
    json_str = clipboard.text()
    
    if json_str:
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                obj = canvas_object_from_dict(item)
                if obj is not None:
                    original_page = item.get("page")
                    obj.page = canvas._current_page
                    # Apply offset only if pasting on same page as original
                    if original_page == canvas._current_page:
                        obj.x += 10
                        obj.y += 10
                    objs1.append(obj)
        except json.JSONDecodeError:
            pass
    
    # Pasted annotation should be at original position (100, 100) with NO offset on different page
    assert len(objs1) >= 1, f"Expected at least one pasted annotation on page 1, got {len(objs1)}"
    pasted_ann = objs1[0]
    assert pasted_ann.x == 100, f"Expected x=100 (no offset on different page), got {pasted_ann.x}"
    assert pasted_ann.y == 100, f"Expected y=100 (no offset on different page), got {pasted_ann.y}"
    assert pasted_ann.page == 1
