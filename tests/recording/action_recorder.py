"""Action recorder for capturing user interactions during test creation.

This module integrates with the Signer application to record user actions
when the SIGNER_RECORD_ACTIONS environment variable is set.
"""

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from tests.utils.test_helpers import ActionRecorder, get_recorder


class ApplicationActionRecorder(QObject):
    """Qt-integrated action recorder that connects to application signals."""
    
    # Signal emitted when an action is recorded (for UI feedback)
    actionRecorded = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._recorder = get_recorder()
        self._connected = False
    
    def connect_to_application(self, main_window) -> None:
        """Connect to the main window's signals to record actions."""
        if self._connected:
            return
        
        canvas = main_window.canvas
        
        # Connect to canvas signals
        canvas.objectChanged.connect(self._on_object_changed)
        canvas.pageChanged.connect(self._on_page_changed)
        
        # Connect to main window actions
        # We'll need to wrap or connect to specific methods
        self._main_window = main_window
        self._connected = True
    
    def disconnect_from_application(self) -> None:
        """Disconnect from application signals."""
        if not self._connected:
            return
        
        canvas = self._main_window.canvas
        try:
            canvas.objectChanged.disconnect(self._on_object_changed)
            canvas.pageChanged.disconnect(self._on_page_changed)
        except TypeError:
            pass  # Already disconnected
        
        self._connected = False
    
    def _on_object_changed(self) -> None:
        """Called when an object is added, moved, resized, or removed."""
        # This is a generic signal - we need more specific tracking
        # The actual recording is done by wrapping the specific methods
        pass
    
    def _on_page_changed(self, current: int, total: int) -> None:
        """Called when the page changes."""
        if self._recorder.is_enabled():
            self._recorder.record_change_page(current)
            self.actionRecorded.emit({
                "type": "change_page",
                "page": current
            })
    
    def record_open_document(self, path: str) -> None:
        """Record opening a document."""
        self._recorder.record_open_document(path)
        self.actionRecorded.emit({
            "type": "open_document",
            "path": path
        })
    
    def record_open_signature(self, path: str) -> None:
        """Record opening a signature."""
        self._recorder.record_open_signature(path)
        self.actionRecorded.emit({
            "type": "open_signature",
            "path": path
        })
    
    def record_add_annotation(self, annotation_type: str, x: float, y: float, page: int, obj=None) -> None:
        """Record adding an annotation."""
        self._recorder.record_add_annotation(annotation_type, x, y, page, obj)
        self.actionRecorded.emit({
            "type": "add_annotation",
            "annotation_type": annotation_type,
            "x": x,
            "y": y,
            "page": page
        })
    
    def record_move_annotation(self, obj, x: float, y: float) -> None:
        """Record moving an annotation."""
        self._recorder.record_move_annotation(obj, x, y)
        self.actionRecorded.emit({
            "type": "move_annotation",
            "object_id": id(obj),
            "x": x,
            "y": y
        })
    
    def record_resize_annotation(self, obj, width: float, height: float, handle: int) -> None:
        """Record resizing an annotation."""
        self._recorder.record_resize_annotation(obj, width, height, handle)
        self.actionRecorded.emit({
            "type": "resize_annotation",
            "object_id": id(obj),
            "width": width,
            "height": height,
            "handle": handle
        })
    
    def record_change_color(self, obj, color: QColor) -> None:
        """Record changing color."""
        color_str = color.name()
        self._recorder.record_change_color(obj, color_str)
        self.actionRecorded.emit({
            "type": "change_color",
            "object_id": id(obj) if obj else "default",
            "color": color_str
        })
    
    def record_save_document(self, path: str) -> None:
        """Record saving a document."""
        self._recorder.record_save_document(path)
        self.actionRecorded.emit({
            "type": "save_document",
            "path": path
        })
    
    def record_set_text(self, obj, text: str) -> None:
        """Record set_text input to a text annotation."""
        self._recorder.record_set_text(obj, text)
        self.actionRecorded.emit({
            "type": "set_text",
            "text": text
        })
    
    def get_recorded_actions(self) -> List[Dict[str, Any]]:
        """Get all recorded actions."""
        return self._recorder.get_actions()
    
    def export_to_file(self, output_path: str | Path) -> None:
        """Export recorded actions to a JSON file."""
        self._recorder.export_json(output_path)
    
    def clear(self) -> None:
        """Clear recorded actions."""
        self._recorder.disable()
        self._recorder.enable()


def create_recorder_for_main_window(main_window) -> ApplicationActionRecorder:
    """Create and connect an action recorder to the main window."""
    recorder = ApplicationActionRecorder(main_window)
    recorder.connect_to_application(main_window)
    return recorder


def patch_main_window_for_recording(main_window) -> None:
    """Patch the main window to record actions when recording is enabled.
    
    This wraps key methods to capture user actions.
    """
    recorder = get_recorder()
    
    if not recorder.is_enabled():
        return
    
    # Store original methods
    original_open_document = main_window.open_document
    original_load_signature = main_window._load_signature_file
    original_add_vector = main_window._add_vector
    original_add_text = main_window._add_text_annotation
    original_save = main_window.save_signed_document
    
    # Wrap open_document
    def recorded_open_document(path=None):
        result = original_open_document(path)
        if result and recorder.is_enabled():
            actual_path = path or main_window.document_path
            if actual_path:
                recorder.record_open_document(actual_path)
        return result
    
    # Wrap _load_signature_file
    def recorded_load_signature(path, at_default_position):
        result = original_load_signature(path, at_default_position)
        if result and recorder.is_enabled():
            recorder.record_open_signature(path)
        return result
    
    # Wrap _add_vector
    def recorded_add_vector(ann_type):
        original_add_vector(ann_type)
        if recorder.is_enabled() and main_window.canvas.selected:
            obj = main_window.canvas.selected
            from signer.objects import AnnotationType
            ann_type_str = ann_type.value if isinstance(ann_type, AnnotationType) else str(ann_type)
            recorder.record_add_annotation(
                ann_type_str, obj.x, obj.y, obj.page, obj
            )
    
    # Wrap _add_text_annotation
    def recorded_add_text(preset_text):
        original_add_text(preset_text)
        if recorder.is_enabled() and main_window.canvas.selected:
            obj = main_window.canvas.selected
            recorder.record_add_annotation(
                "text", obj.x, obj.y, obj.page, obj
            )
    
    # Wrap save_signed_document
    def recorded_save():
        result = original_save()
        if result and recorder.is_enabled():
            # Get the actual save path from the file dialog
            # This is tricky since the path is chosen in the dialog
            # We'll record it after the fact if possible
            pass
        return result
    
    # Apply patches
    main_window.open_document = recorded_open_document
    main_window._load_signature_file = recorded_load_signature
    main_window._add_vector = recorded_add_vector
    main_window._add_text_annotation = recorded_add_text
    main_window.save_signed_document = recorded_save
    
    # Also patch canvas for move/resize
    canvas = main_window.canvas
    original_mouse_move = canvas.mouseMoveEvent
    original_mouse_release = canvas.mouseReleaseEvent
    
    def recorded_mouse_move(event):
        original_mouse_move(event)
        # Track that a drag operation is happening
        if canvas._dragging and canvas._selected:
            canvas._was_dragging = True
    
    def recorded_mouse_release(event):
        original_mouse_release(event)
        # Record the final position only when mouse is released
        if recorder.is_enabled() and canvas._selected:
            obj = canvas._selected
            # Check if this was a drag operation that just ended
            if hasattr(canvas, '_was_dragging') and canvas._was_dragging:
                if canvas._drag_handle == -1:
                    # Move operation - record final position
                    recorder.record_move_annotation(obj, obj.x, obj.y)
                else:
                    # Resize operation - record final size
                    recorder.record_resize_annotation(
                        obj, obj.scaled_width, obj.scaled_height, canvas._drag_handle
                    )
                canvas._was_dragging = False
    
    canvas.mouseMoveEvent = recorded_mouse_move
    canvas.mouseReleaseEvent = recorded_mouse_release
    
    # Patch color picker
    original_pick_color = main_window._pick_color
    
    def recorded_pick_color():
        selected_before = main_window.canvas.selected
        original_pick_color()
        if recorder.is_enabled():
            selected_after = main_window.canvas.selected
            color = main_window._current_color
            recorder.record_change_color(selected_after, color)
    
    main_window._pick_color = recorded_pick_color
    
    # Store original methods for potential restoration
    main_window._original_methods = {
        'open_document': original_open_document,
        '_load_signature_file': original_load_signature,
        '_add_vector': original_add_vector,
        '_add_text_annotation': original_add_text,
        'save_signed_document': original_save,
        '_pick_color': original_pick_color,
    }
    canvas._original_mouse_move = original_mouse_move
    canvas._original_mouse_release = original_mouse_release


def unpatch_main_window(main_window) -> None:
    """Restore original methods on main window."""
    if not hasattr(main_window, '_original_methods'):
        return
    
    for name, method in main_window._original_methods.items():
        setattr(main_window, name, method)
    
    canvas = main_window.canvas
    if hasattr(canvas, '_original_mouse_move'):
        canvas.mouseMoveEvent = canvas._original_mouse_move
    if hasattr(canvas, '_original_mouse_release'):
        canvas.mouseReleaseEvent = canvas._original_mouse_release
    
    del main_window._original_methods
    if hasattr(canvas, '_original_mouse_move'):
        del canvas._original_mouse_move
    if hasattr(canvas, '_original_mouse_release'):
        del canvas._original_mouse_release


def setup_recording_if_enabled(main_window) -> Optional[ApplicationActionRecorder]:
    """Set up action recording if the environment variable is set.
    
    Returns the recorder instance if recording is enabled, None otherwise.
    """
    if os.environ.get("SIGNER_RECORD_ACTIONS") != "1":
        return None
    
    # Enable the global recorder
    enable_recording()
    
    # Patch the main window
    patch_main_window_for_recording(main_window)
    
    # Create and return the Qt-integrated recorder
    recorder = create_recorder_for_main_window(main_window)
    
    # Print instructions
    print("\n" + "="*60)
    print("ACTION RECORDING ENABLED")
    print("="*60)
    print("Perform your test actions in the application.")
    print("When done, close the application.")
    print("Recorded actions will be saved to: tests/recorded_actions/")
    print("="*60 + "\n")
    
    # Hook into application aboutToQuit to export actions
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    
    def on_quit():
        actions = recorder.get_recorded_actions()
        if actions:
            # Save to file (no stdout printing to avoid duplication)
            output_dir = Path(__file__).parent.parent / "recorded_actions"
            output_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"recorded_actions_{timestamp}.json"
            recorder.export_to_file(output_file)
            print(f"\n✓ Actions saved to: {output_file}\n")
    
    app.aboutToQuit.connect(on_quit)
    
    return recorder


# Import the enable/disable functions from test_helpers
from tests.utils.test_helpers import enable_recording, disable_recording, is_recording_enabled