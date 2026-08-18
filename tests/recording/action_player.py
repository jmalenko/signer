"""Action player for replaying recorded actions in feature tests."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import QFileDialog, QMessageBox

from signer.main_window import MainWindow
from signer.objects import AnnotationType, CanvasObject


class ActionPlayer:
    """Plays back recorded actions against a MainWindow instance."""

    def __init__(self, main_window: MainWindow, output_path: Optional[Path] = None):
        self.main_window = main_window
        self.canvas = main_window.canvas
        self._object_map: Dict[int, CanvasObject] = {}
        self._next_object_id = 0
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
        elif action_type == "change_page":
            self._execute_change_page(action)
        elif action_type == "save_document":
            self._execute_save_document(action)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def _execute_open_document(self, action: Dict[str, Any]) -> None:
        """Open a document."""
        path = action["path"]
        result = self.main_window.open_document(path)
        if not result:
            raise RuntimeError(f"Failed to open document: {path}")

    def _execute_open_signature(self, action: Dict[str, Any]) -> None:
        """Load a signature file."""
        path = action["path"]
        result = self.main_window._load_signature_file(path, at_default_position=True)
        if not result:
            raise RuntimeError(f"Failed to load signature: {path}")
        
        # Track the created object
        if self.canvas.selected:
            self._register_object(0, self.canvas.selected)

    def _execute_add_annotation(self, action: Dict[str, Any]) -> None:
        """Add a vector annotation."""
        ann_type_str = action["annotation_type"]
        x = action["x"]
        y = action["y"]
        page = action.get("page", 0)

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
            self.canvas.objectChanged.emit()
            self.canvas.update()
            
            # Track the created object
            obj_id = action.get("object_id", self._next_object_id)
            self._register_object(obj_id, self.canvas.selected)

    def _execute_move_annotation(self, action: Dict[str, Any]) -> None:
        """Move an annotation."""
        obj_id = action["object_id"]
        x = action["x"]
        y = action["y"]

        obj = self._get_object(obj_id)
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found")

        # Select the object first
        self.canvas._selected = obj
        self.canvas.objectChanged.emit()

        # Move to new position
        obj.x = x
        obj.y = y
        self.canvas.objectChanged.emit()
        self.canvas.update()

    def _execute_resize_annotation(self, action: Dict[str, Any]) -> None:
        """Resize an annotation."""
        obj_id = action["object_id"]
        width = action["width"]
        height = action["height"]
        handle = action.get("handle", 7)  # Default to bottom-right handle

        obj = self._get_object(obj_id)
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found")

        # Select the object first
        self.canvas._selected = obj
        self.canvas.objectChanged.emit()

        # Resize using set_scaled_size (proportional resize for vector annotations)
        obj.set_scaled_size(width, height)
        self.canvas.objectChanged.emit()
        self.canvas.update()

    def _execute_select_annotation(self, action: Dict[str, Any]) -> None:
        """Select an annotation."""
        obj_id = action["object_id"]
        obj = self._get_object(obj_id)
        if obj is None:
            raise RuntimeError(f"Object with id {obj_id} not found")

        self.canvas._selected = obj
        self.canvas.objectChanged.emit()

    def _execute_change_color(self, action: Dict[str, Any]) -> None:
        """Change color of an annotation or default color."""
        obj_id = action["object_id"]
        color_str = action["color"]

        from PySide6.QtGui import QColor
        color = QColor(color_str)

        if obj_id == "default":
            self.main_window._current_color = color
        else:
            obj = self._get_object(obj_id)
            if obj is None:
                raise RuntimeError(f"Object with id {obj_id} not found")
            obj.color = color
            self.canvas.objectChanged.emit()
            self.canvas.update()

    def _execute_change_page(self, action: Dict[str, Any]) -> None:
        """Change the current page."""
        page = action["page"]
        self.canvas.goto_page(page)

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

    def _register_object(self, obj_id: int, obj: CanvasObject) -> None:
        """Register an object with an ID."""
        self._object_map[obj_id] = obj
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