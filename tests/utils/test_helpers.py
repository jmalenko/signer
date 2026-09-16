"""Common test helpers for Signer tests."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor


def create_mock_canvas_object(x: float = 100, y: float = 100, width: float = 200, height: float = 200):
    """Create a mock canvas object for testing."""
    mock = MagicMock()
    mock.x = x
    mock.y = y
    mock.scaled_width = width
    mock.scaled_height = height
    mock.page = 0
    mock.color = QColor("#cc0000")
    return mock


def simulate_mouse_drag(canvas, obj, start_x: float, start_y: float, end_x: float, end_y: float):
    """Simulate a mouse drag operation on an object."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt
    
    # This is a helper for feature tests to simulate user interactions
    pass


def wait_for_signal(signal, timeout: int = 1000):
    """Wait for a Qt signal to be emitted."""
    from PySide6.QtTest import QSignalSpy
    spy = QSignalSpy(signal)
    assert spy.wait(timeout), f"Signal not emitted within {timeout}ms"
    return spy


def create_test_annotation_data(annotation_type: str, x: float, y: float, page: int = 0, **kwargs) -> Dict[str, Any]:
    """Create a dictionary representing an annotation for test recording."""
    return {
        "type": "add_annotation",
        "annotation_type": annotation_type,
        "x": x,
        "y": y,
        "page": page,
        **kwargs
    }


def create_test_move_data(object_id: int, x: float, y: float) -> Dict[str, Any]:
    """Create a dictionary representing a move action for test recording."""
    return {
        "type": "move_annotation",
        "object_id": object_id,
        "x": x,
        "y": y
    }


def create_test_resize_data(object_id: int, width: float, height: float, handle: int) -> Dict[str, Any]:
    """Create a dictionary representing a width/height resize action."""
    return {
        "type": "resize_annotation",
        "object_id": object_id,
        "width": width,
        "height": height,
        "handle": handle
    }


def create_test_endpoint_resize_data(object_id: int, handle: int, x: float, y: float) -> Dict[str, Any]:
    """Create a dictionary representing an endpoint-handle resize action."""
    return {
        "type": "resize_annotation",
        "object_id": object_id,
        "handle": handle,
        "x": x,
        "y": y,
    }


def save_recorded_actions(actions: List[Dict[str, Any]], output_path: str | Path) -> None:
    """Save recorded actions to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "actions": actions
    }
    output_path.write_text(json.dumps(data, indent=2))


def load_recorded_actions(input_path: str | Path) -> List[Dict[str, Any]]:
    """Load recorded actions from a JSON file."""
    input_path = Path(input_path)
    data = json.loads(input_path.read_text())
    return data.get("actions", [])


class ActionRecorder:
    """Records user actions for test creation."""
    
    def __init__(self):
        self.actions: List[Dict[str, Any]] = []
        self._enabled = False
        self._object_id_counter = 0
        self._object_map: Dict[int, int] = {}  # object -> id mapping
    
    def enable(self):
        """Enable recording."""
        self._enabled = True
        self.actions = []
        self._object_id_counter = 0
        self._object_map = {}
    
    def disable(self):
        """Disable recording."""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def _get_object_id(self, obj) -> int:
        """Get or assign an ID to an object."""
        obj_id = id(obj)
        if obj_id not in self._object_map:
            self._object_map[obj_id] = self._object_id_counter
            self._object_id_counter += 1
        return self._object_map[obj_id]
    
    def record_open_document(self, path: str):
        if not self._enabled:
            return
        self.actions.append({
            "type": "open_document",
            "path": path
        })
    
    def record_open_signature(self, path: str):
        if not self._enabled:
            return
        self.actions.append({
            "type": "open_signature",
            "path": path
        })
    
    def record_add_annotation(self, annotation_type: str, x: float, y: float, page: int, obj=None):
        if not self._enabled:
            return
        obj_id = self._get_object_id(obj) if obj else None
        self.actions.append({
            "type": "add_annotation",
            "annotation_type": annotation_type,
            "x": x,
            "y": y,
            "page": page,
            "object_id": obj_id
        })
    
    def record_move_annotation(self, obj, x: float, y: float):
        if not self._enabled:
            return
        obj_id = self._get_object_id(obj)
        self.actions.append({
            "type": "move_annotation",
            "object_id": obj_id,
            "x": x,
            "y": y
        })
    
    def record_resize_annotation(self, obj, width: float, height: float, handle: int):
        if not self._enabled:
            return
        obj_id = self._get_object_id(obj)
        self.actions.append({
            "type": "resize_annotation",
            "object_id": obj_id,
            "width": width,
            "height": height,
            "handle": handle
        })

    def record_resize_annotation_endpoint(self, obj, handle: int, x: float, y: float):
        """Record endpoint-handle resize for LINE/ARROW."""
        if not self._enabled:
            return
        obj_id = self._get_object_id(obj)
        self.actions.append({
            "type": "resize_annotation",
            "object_id": obj_id,
            "handle": handle,
            "x": x,
            "y": y,
        })
    
    def record_change_color(self, obj, color: str):
        if not self._enabled:
            return
        if obj is None:
            obj_id = "default"
        else:
            obj_id = self._get_object_id(obj)
        self.actions.append({
            "type": "change_color",
            "object_id": obj_id,
            "color": color
        })
    
    def record_change_page(self, page_index: int):
        if not self._enabled:
            return
        self.actions.append({
            "type": "change_page",
            "page": page_index
        })

    def record_copy_annotation(self, obj):
        if not self._enabled:
            return
        self.actions.append({
            "type": "copy_annotation",
            "object_id": self._get_object_id(obj),
        })

    def record_paste_annotations(self):
        if not self._enabled:
            return
        self.actions.append({
            "type": "paste_annotations",
        })
    
    def record_save_document(self, path: str):
        if not self._enabled:
            return
        self.actions.append({
            "type": "save_document",
            "path": path
        })
    
    def record_set_text(self, obj, text: str):
        """Record set_text input to a text annotation."""
        if not self._enabled:
            return
        obj_id = self._get_object_id(obj) if obj else None
        self.actions.append({
            "type": "set_text",
            "object_id": obj_id,
            "text": text
        })
    
    def get_actions(self) -> List[Dict[str, Any]]:
        return self.actions.copy()
    
    def export_json(self, output_path: str | Path):
        save_recorded_actions(self.actions, output_path)


# Global recorder instance
_global_recorder = ActionRecorder()


def get_recorder() -> ActionRecorder:
    """Get the global action recorder instance."""
    return _global_recorder


def enable_recording():
    """Enable global action recording."""
    _global_recorder.enable()


def disable_recording():
    """Disable global action recording."""
    _global_recorder.disable()


def is_recording_enabled() -> bool:
    """Check if recording is enabled."""
    return _global_recorder.is_enabled()