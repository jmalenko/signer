"""Action player for replaying recorded actions in feature tests."""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QFileDialog, QMessageBox

from signer.main_window import MainWindow
from signer.objects import AnnotationType, CanvasObject
from signer.history import (
    AddAnnotationAction,
    MoveAnnotationAction,
)


def normalize_recorded_path(path: str | Path) -> str:
    """Normalize fixture paths written with either Windows or POSIX separators."""
    return str(path).replace("\\", "/")


class ActionPlayer:
    """Plays back recorded actions against a MainWindow instance."""

    def __init__(self, main_window: MainWindow, output_path: Optional[Path] = None):
        self.main_window = main_window
        self.canvas = main_window.canvas
        self._object_map: Dict[int, CanvasObject] = {}
        self._next_object_id = 0
        self._endpoint_state: Dict[int, list[QPointF]] = {}
        self.output_path = output_path

    def load_actions(self, actions_file: str | Path) -> List[Dict[str, Any]]:
        """Load actions from a JSON file."""
        path = Path(actions_file)
        data = json.loads(path.read_text())
        return data.get("actions", [])

    def play_actions(self, actions: List[Dict[str, Any]]) -> None:
        """Execute a list of recorded actions."""
        for action in actions:
            self._execute_action(action)

    def _execute_action(self, action: Dict[str, Any]) -> None:
        """Execute a single action."""
        action_type = action.get("type")

        if action_type == "open_document":
            self._execute_open_document(action)
        elif action_type == "open_signature":
            self._execute_open_signature(action)
        elif action_type == "add_signature":
            self._execute_add_signature(action)
        elif action_type == "add_annotation":
            self._execute_add_annotation(action)
        elif action_type == "move_annotation":
            self._execute_move_annotation(action)
        elif action_type == "resize_annotation":
            self._execute_resize_annotation(action)
        elif action_type == "select_annotation":
            self._execute_select_annotation(action)
        elif action_type == "change_color":
            self._execute_change_color(action)
        elif action_type == "set_color":
            self._execute_change_color(action)
        elif action_type == "change_page":
            self._execute_change_page(action)
        elif action_type == "copy_annotation":
            self._execute_copy_annotation(action)
        elif action_type == "paste_annotations":
            self.canvas.paste_selected()
        elif action_type == "set_text":
            self._execute_set_text(action)
        elif action_type == "set_font_size":
            self._execute_set_font_size(action)
        elif action_type == "set_font_family":
            self._execute_set_font_family(action)
        elif action_type == "set_line_width":
            self._execute_set_line_width(action)
        elif action_type == "undo":
            self._execute_undo(action)
        elif action_type == "redo":
            self._execute_redo(action)
        elif action_type == "save_document":
            self._execute_save_document(action)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def _execute_open_document(self, action: Dict[str, Any]) -> None:
        """Open a document."""
        path = normalize_recorded_path(action["path"])
        result = self.main_window.open_document(path)
        if not result:
            raise RuntimeError(f"Failed to open document: {path}")

    def _execute_open_signature(self, action: Dict[str, Any]) -> None:
        """Load a signature file."""
        path = normalize_recorded_path(action["path"])
        result = self.main_window._load_signature_file(path, at_default_position=True)
        if not result:
            raise RuntimeError(f"Failed to load signature: {path}")
        
        # Track the created object - use next available ID
        if self.canvas.selected:
            self._register_object(self._next_object_id, self.canvas.selected)

    def _execute_add_signature(self, action: Dict[str, Any]) -> None:
        """Add a signature file (same as open_signature)."""
        path = normalize_recorded_path(action["path"])
        result = self.main_window._load_signature_file(path, at_default_position=True)
        if not result:
            raise RuntimeError(f"Failed to load signature: {path}")
        
        # Track the created object - use next available ID
        if self.canvas.selected:
            self._register_object(self._next_object_id, self.canvas.selected)

    def _execute_add_annotation(self, action: Dict[str, Any]) -> None:
        """Add a vector annotation and record to history."""
        ann_type_str = action["annotation_type"]
        x = action["x"]
        y = action["y"]
        page = action.get("page", 0)
        text = action.get("text")  # Optional text content for text annotations

        # Convert string to enum
        ann_type = AnnotationType(ann_type_str)

        # Switch to the correct page if needed
        if page != self.canvas.current_page:
            self.canvas.goto_page(page)

        # Add the annotation at the specified position
        self.main_window._add_vector(ann_type)
        
        if self.canvas.selected:
            # Move to the recorded position
            self.canvas.selected.x = x
            self.canvas.selected.y = y
            
            # Set text content if this is a text annotation
            if text is not None and hasattr(self.canvas.selected, 'text'):
                self.canvas.selected.text = text
                # Resize annotation to fit the text
                if hasattr(self.canvas.selected, 'fit_text_box'):
                    self.canvas.selected.fit_text_box()
            
            self.canvas.objectChanged.emit()
            self.canvas.update()
            
            # Track the created object
            obj_id = action.get("object_id", self._next_object_id)
            self._register_object(obj_id, self.canvas.selected)
            if hasattr(self.canvas.selected, 'supports_endpoint_handles') and self.canvas.selected.supports_endpoint_handles():
                self._endpoint_state[obj_id] = self.canvas.selected.endpoint_points_doc()
            
            # Record to history by capturing object's current state
            # Build annotation data from the created object
            obj = self.canvas.selected
            annotation_data = {
                "annotation_type": ann_type_str,
                "x": obj.x,
                "y": obj.y,
                "page": page,
                "color": getattr(obj, 'color', None),
            }
            
            # Include object_id if present in the original action
            if "object_id" in action:
                annotation_data["object_id"] = action["object_id"]
            
            # Include text if present
            if hasattr(obj, 'text'):
                annotation_data["text"] = obj.text
            if hasattr(obj, 'width'):
                annotation_data["width"] = obj.width
            if hasattr(obj, 'height'):
                annotation_data["height"] = obj.height
            if hasattr(obj, 'rotation'):
                annotation_data["rotation"] = obj.rotation
            if hasattr(obj, 'thickness'):
                annotation_data["thickness"] = obj.thickness
            
            add_action = AddAnnotationAction(annotation_data)
            self.canvas.history.record_action(add_action)

    def _execute_move_annotation(self, action: Dict[str, Any]) -> None:
        """Move an annotation and record to history."""
        obj_id = action["object_id"]
        x = action["x"]
        y = action["y"]

        # First check if object is in the map
        obj = self._object_map.get(obj_id)
        
        # If not in map, try to find it by index in current page (for backward compat)
        if obj is None:
            page_objects = self.canvas.current_page_objects()
            if obj_id < len(page_objects):
                obj = page_objects[obj_id]
        
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found")

        # Capture current position as "from" state
        from_x = obj.x
        from_y = obj.y

        # Select the object first
        self.canvas._selected = obj
        self.canvas.objectChanged.emit()

        # Move to new position
        obj.x = x
        obj.y = y
        
        self.canvas.objectChanged.emit()
        self.canvas.update()
        
        # Record to history with full format (from_ and to_)
        move_action = MoveAnnotationAction(
            object_id=obj_id,
            from_x=from_x,
            from_y=from_y,
            to_x=x,
            to_y=y
        )
        self.canvas.history.record_action(move_action)

    def _execute_resize_annotation(self, action: Dict[str, Any]) -> None:
        """Resize an annotation and record to history."""
        obj_id = action["object_id"]
        handle = int(action.get("handle", 7))  # Default to bottom-right handle

        # First check if object is in the map
        obj = self._object_map.get(obj_id)
        
        # If not in map, try to find it by index in current page (for backward compat)
        if obj is None:
            page_objects = self.canvas.current_page_objects()
            if obj_id < len(page_objects):
                obj = page_objects[obj_id]
        
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found")

        # Capture current size as "from" state using the scaled_width/scaled_height properties
        from_width = obj.scaled_width
        from_height = obj.scaled_height

        # Select the object first
        self.canvas._selected = obj
        self.canvas.objectChanged.emit()

        # Handle endpoint-based resize (for LINE/ARROW with handle 0 or 1)
        if hasattr(obj, 'supports_endpoint_handles') and obj.supports_endpoint_handles() and handle in (0, 1):
            # Endpoint-handle resize: explicit x,y coordinates (from interactive drag)
            if "x" in action and "y" in action:
                points = self._endpoint_state.get(obj_id, obj.endpoint_points_doc())
                if len(points) != 2:
                    raise RuntimeError(f"Object with id {obj_id} does not expose exactly two endpoint handles")
                points[handle] = QPointF(float(action["x"]), float(action["y"]))
                self._apply_endpoint_resize(obj, points[0], points[1])
                self._endpoint_state[obj_id] = [QPointF(points[0]), QPointF(points[1])]
                width = obj.scaled_width
                height = obj.scaled_height
            # Endpoint-handle resize: width/height with handle specification (for fixture-based resize)
            elif "width" in action and "height" in action:
                # Get old endpoints to determine which one to preserve
                old_endpoints = self._endpoint_state.get(obj_id, obj.endpoint_points_doc())
                if len(old_endpoints) != 2:
                    raise RuntimeError(f"Object with id {obj_id} does not expose exactly two endpoint handles")
                
                # The non-dragged endpoint stays fixed
                fixed_idx = 1 - handle
                fixed_point = old_endpoints[fixed_idx]
                
                # Calculate new endpoint position based on new size and angle
                from signer.objects import AnnotationType
                new_width = action["width"]
                new_height = action["height"]
                ann_type = getattr(obj, 'ann_type', None)
                
                if ann_type == AnnotationType.ARROW:
                    # For arrows: distance = size * 0.66
                    dist = max(8.0, max(new_width, new_height)) * 0.66
                    # Use current angle or default
                    angle_deg = getattr(obj, '_angle', 0.0)
                    if angle_deg is None:
                        angle_deg = 0.0
                else:  # LINE
                    # For lines: distance = size
                    dist = max(8.0, max(new_width, new_height))
                    angle_deg = getattr(obj, '_angle', 0.0)
                    if angle_deg is None:
                        angle_deg = 0.0
                
                # Calculate the dragged endpoint position
                angle_rad = math.radians(angle_deg)
                dx = dist * math.cos(angle_rad)
                dy = -dist * math.sin(angle_rad) if ann_type == AnnotationType.ARROW else dist * math.sin(angle_rad)
                
                if handle == 0:  # Dragging tail
                    dragged_point = fixed_point
                    other_point = QPointF(fixed_point.x() + dx, fixed_point.y() + dy)
                else:  # Dragging tip (handle == 1)
                    other_point = fixed_point
                    dragged_point = QPointF(fixed_point.x() + dx, fixed_point.y() + dy)
                
                self._apply_endpoint_resize(obj, dragged_point if handle == 0 else other_point,
                                          other_point if handle == 0 else dragged_point)
                self._endpoint_state[obj_id] = [dragged_point if handle == 0 else other_point,
                                               other_point if handle == 0 else dragged_point]
                width = obj.scaled_width
                height = obj.scaled_height
            else:
                # No size or position info, just use legacy resize
                width = obj.scaled_width
                height = obj.scaled_height
        else:
            # Legacy resize format: width/height based.
            width = action.get("width", obj.scaled_width)
            height = action.get("height", obj.scaled_height)
            obj.set_scaled_size(width, height)

        self.canvas.objectChanged.emit()
        self.canvas.update()
        from signer.history.action import ResizeAnnotationAction
        resize_action = ResizeAnnotationAction(
            object_id=obj_id,
            from_width=from_width,
            from_height=from_height,
            to_width=width,
            to_height=height,
            handle=handle
        )
        self.canvas.history.record_action(resize_action)

    def _apply_endpoint_resize(self, obj: CanvasObject, p0: QPointF, p1: QPointF) -> None:
        """Apply endpoint-based resize for LINE and ARROW.

        Handle mapping:
        - 0: start/tail endpoint
        - 1: end/tip endpoint
        """
        dx = p1.x() - p0.x()
        dy = p1.y() - p0.y()
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return

        cx = (p0.x() + p1.x()) / 2.0
        cy = (p0.y() + p1.y()) / 2.0

        ann_type = getattr(obj, 'ann_type', None)
        if ann_type == AnnotationType.LINE:
            angle = math.degrees(math.atan2(dy, dx))
            size = max(8.0, dist)
        else:
            # For ARROW, endpoint distance is 2*shaft = 0.66*size.
            angle = math.degrees(math.atan2(-dy, dx))
            size = max(8.0, dist / 0.66)

        obj.set_scaled_size(size, size)
        obj.x = cx - size / 2.0
        obj.y = cy - size / 2.0
        if hasattr(obj, '_angle'):
            obj._angle = angle

    def _execute_select_annotation(self, action: Dict[str, Any]) -> None:
        """Select an annotation."""
        obj_id = action["object_id"]
        
        # First check if object is in the map
        obj = self._object_map.get(obj_id)
        
        # If not in map, try to find it by index in current page (for backward compat)
        if obj is None:
            page_objects = self.canvas.current_page_objects()
            if obj_id < len(page_objects):
                obj = page_objects[obj_id]
        
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found")
        
        self.canvas._selected = obj
        self.canvas.objectChanged.emit()

    def _execute_change_color(self, action: Dict[str, Any]) -> None:
        """Change color of an annotation or default color."""
        obj_id = action["object_id"]
        color_str = action["color"]

        from PySide6.QtGui import QColor
        from signer.history.action import ChangeColorAction
        
        color = QColor(color_str)

        if obj_id == "default":
            self.main_window._current_color = color
        else:
            # Use hybrid object lookup: check map first, then page index
            obj = self._object_map.get(obj_id)
            
            if obj is None:
                page_objects = self.canvas.current_page_objects()
                if obj_id < len(page_objects):
                    obj = page_objects[obj_id]
            
            if obj is None:
                raise RuntimeError(f"Object with id {obj_id} not found")
            
            # Capture current color as "from" state
            from_color = None
            if hasattr(obj, 'color'):
                current_color = obj.color
                if current_color:
                    from_color = current_color.name()  # Convert QColor to hex string
            
            obj.color = color
            self.canvas.objectChanged.emit()
            self.canvas.update()
            
            # Record to history
            change_color_action = ChangeColorAction(
                object_id=obj_id,
                color=color_str,
                from_color=from_color
            )
            self.canvas.history.record_action(change_color_action)

    def _execute_change_page(self, action: Dict[str, Any]) -> None:
        """Change the current page."""
        page = action["page"]
        self.canvas.goto_page(page)

    def _execute_copy_annotation(self, action: Dict[str, Any]) -> None:
        """Select and copy one recorded annotation."""
        obj = self._get_object(action["object_id"])
        if obj is None:
            raise RuntimeError(f"Object with id {action['object_id']} not found")
        self.canvas._selected_multiple.clear()
        self.canvas._selected = obj
        self.canvas.copy_selected()

    def _execute_save_document(self, action: Dict[str, Any]) -> None:
        """Save the document.
        
        If path is provided in the action, the file will be saved to that path.
        If path is omitted and output_path was set in constructor, use that.
        Otherwise, the application's default save dialog will be used.
        """
        path = action.get("path") or self.output_path
        
        from pathlib import Path
        from unittest.mock import patch
        
        if path:
            # Ensure it's a string path
            path_str = str(path)
            # Determine the file format from the path extension
            ext = Path(path_str).suffix.lower()
            
            # For multi-page documents with PNG/JPG/BMP, add placeholder if not present
            if self.canvas.page_count > 1 and ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                path_obj = Path(path_str)
                # Add -p# placeholder if not already present
                if '#' not in path_obj.stem:
                    path_str = str(path_obj.parent / f"{path_obj.stem}-p#{ext}")
            
            if ext == '.png':
                format_filter = "PNG files (*.png)"
            elif ext in ['.jpg', '.jpeg']:
                format_filter = "JPEG files (*.jpg *.jpeg)"
            else:
                format_filter = "JPEG files (*.jpg *.jpeg)"  # default
            
            # Mock the file dialog to use our path
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(path_str, format_filter)):
                with patch.object(QMessageBox, 'information', return_value=QMessageBox.Ok):
                    result = self.main_window.save_signed_document()
                    if not result:
                        raise RuntimeError(f"Failed to save document to: {path_str}")
        else:
            # No path specified and no output_path set - let the application use its default behavior
            # Mock only the message box, let the dialog proceed
            with patch.object(QMessageBox, 'information', return_value=QMessageBox.Ok):
                result = self.main_window.save_signed_document()
                if not result:
                    raise RuntimeError("Failed to save document")
    def _execute_set_text(self, action: Dict[str, Any]) -> None:
        """Execute set_text on a text annotation.
        
        This method simulates setting text on a text annotation.
        """
        obj_id = action.get("object_id")
        text = action.get("text", "")
        
        # If no object_id, use the last selected object (for setting text on current selection)
        if obj_id is not None:
            # Get object from canvas's current page objects by index
            page_objects = self.canvas.current_page_objects()
            if obj_id >= len(page_objects):
                raise RuntimeError(f"Object with id {obj_id} not found for set_text in current page")
            
            obj = page_objects[obj_id]
        else:
            # Use currently selected object if available
            obj = self.canvas.selected
            if obj is None:
                raise RuntimeError("No object selected for set_text")
        
        # Set the text content
        if hasattr(obj, 'text'):
            obj.text = text
            # Resize annotation to fit the text if available
            if hasattr(obj, 'fit_text_box'):
                obj.fit_text_box()
        
        self.canvas.objectChanged.emit()
        self.canvas.update()

    def _execute_set_font_size(self, action: Dict[str, Any]) -> None:
        """Execute set_font_size on a text annotation.
        
        This method sets the font size (in points) on a text annotation.
        """
        obj_id = action.get("object_id")
        font_size_px = action.get("font_size_px", 11)
        
        # If no object_id, use the last selected object
        if obj_id is not None:
            # Get object from canvas's current page objects by index
            page_objects = self.canvas.current_page_objects()
            if obj_id >= len(page_objects):
                raise RuntimeError(f"Object with id {obj_id} not found for set_font_size in current page")
            
            obj = page_objects[obj_id]
        else:
            # Use currently selected object if available
            obj = self.canvas.selected
            if obj is None:
                raise RuntimeError("No object selected for set_font_size")
        
        # Set the font size (directly set the private attribute)
        if hasattr(obj, '_font_size_px'):
            obj._font_size_px = font_size_px
            # Resize annotation to fit the text with new font size if available
            if hasattr(obj, 'fit_text_box'):
                obj.fit_text_box()
        
        self.canvas.objectChanged.emit()
        self.canvas.update()

    def _execute_set_font_family(self, action: Dict[str, Any]) -> None:
        """Set font family on a text annotation."""
        obj_id = action.get("object_id")
        font_family = action.get("font_family", "Arial")

        obj = self._object_map.get(obj_id)
        if obj is None:
            page_objects = self.canvas.current_page_objects()
            if obj_id is not None and obj_id < len(page_objects):
                obj = page_objects[obj_id]
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found for set_font_family")

        if hasattr(obj, '_font_family'):
            obj._font_family = font_family
            if hasattr(obj, 'fit_text_box'):
                obj.fit_text_box()
        self.canvas.objectChanged.emit()
        self.canvas.update()

    def _execute_set_line_width(self, action: Dict[str, Any]) -> None:
        """Set line width (in PDF points) on a vector annotation.
        
        Updates both _line_width_pt (used by LINE/RECT/ELLIPSE) and
        _line_width_factor (used by CHECKMARK/CROSSMARK/ARROW) to keep them in sync.
        """
        from signer.objects import CanvasObject
        obj_id = action.get("object_id")
        width_pt = float(action.get("width_pt", 1.5))

        obj = self._object_map.get(obj_id)
        if obj is None:
            page_objects = self.canvas.current_page_objects()
            if obj_id is not None and obj_id < len(page_objects):
                obj = page_objects[obj_id]
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found for set_line_width")

        if hasattr(obj, '_line_width_pt'):
            obj._line_width_pt = width_pt
        if hasattr(obj, '_line_width_factor'):
            obj._line_width_factor = width_pt / CanvasObject.DEFAULT_BASE_SIZE
        self.canvas.objectChanged.emit()
        self.canvas.update()

    def _execute_undo(self, action: Dict[str, Any]) -> None:
        """Execute an undo operation."""
        if self.canvas.can_undo():
            self.canvas.undo()
        else:
            raise RuntimeError("Cannot undo: no actions in undo stack")

    def _execute_redo(self, action: Dict[str, Any]) -> None:
        """Execute a redo operation."""
        if self.canvas.can_redo():
            self.canvas.redo()
        else:
            raise RuntimeError("Cannot redo: no actions in redo stack")

    def _register_object(self, obj_id: int, obj: CanvasObject) -> None:
        """Register an object with an ID."""
        self._object_map[obj_id] = obj
        # Also sync to canvas's object map so undo/redo can find the object
        if hasattr(self.canvas, '_object_map'):
            self.canvas._object_map[obj_id] = obj
        self._next_object_id = max(self._next_object_id, obj_id + 1)

    def _get_object(self, obj_id: int) -> Optional[CanvasObject]:
        """Get an object by its recorded ID."""
        return self._object_map.get(obj_id)


def play_actions_from_file(main_window: MainWindow, actions_file: str | Path, output_path: Optional[Path] = None) -> None:
    """Convenience function to play actions from a file.
    
    Args:
        main_window: The main window to play actions against
        actions_file: Path to JSON file containing actions
        output_path: Optional path to use when save_document action has no path
    """
    player = ActionPlayer(main_window, output_path=output_path)
    actions = player.load_actions(actions_file)
    player.play_actions(actions)