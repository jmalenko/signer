"""Action classes for undo/redo history and action recording.

Action Format (Dual Support):
- Partial format: Only target state (used by action recorder for tests)
  Example: {"type": "move_annotation", "object_id": 0, "x": 300, "y": 400}
- Full format: Initial + target state (used by undo/redo history)
  Example: {"type": "move_annotation", "object_id": 0, "from_x": 100, "from_y": 100, "to_x": 300, "to_y": 400}

The system handles both seamlessly: record_action() merges partial-format actions
by updating the target state of the last stack element.

Who produces which format:
- The action recorder/player (tests/recording/) only ever writes partial format,
  since it replays a scripted end state and never needs to undo.
- Live user interaction (canvas.py drag handlers) writes full format: the first
  mouse-move of a drag records the initial state, subsequent moves record
  partial-format updates that get merged (`HistoryStack.record_action` calls
  `MergeableAction.merge()`) into that first action's target state in place.

Calling `undo()` on a `MergeableAction` (Move/Resize) that only has partial
format (no initial state) raises `ValueError` - this should not happen for
actions reached via the live undo stack, since those always start from a
full-format action; it can only happen if a fixture/recorded partial-format
action is fed directly into `undo()`, which the action player never does.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class Action(ABC):
    """Base class for all actions in the undo/redo system."""

    _registry: dict[str, type["Action"]] = {}

    def __init__(self, action_type: str, data: dict[str, Any] | None = None) -> None:
        """Initialize an action.
        
        Args:
            action_type: Identifier for the action type (e.g., "move_annotation")
            data: Dictionary of action data (supports partial or full format)
        """
        self.action_type = action_type
        self.data = data or {}

    @abstractmethod
    def execute(self, canvas: Any) -> None:
        """Execute the action (apply forward/redo)."""

    @abstractmethod
    def undo(self, canvas: Any) -> None:
        """Undo the action (restore to previous state)."""

    def serialize(self) -> dict[str, Any]:
        """Serialize action to dictionary for JSON storage."""
        return {
            "type": self.action_type,
            **self.data,
        }

    @staticmethod
    def find_object(canvas: Any, object_id: int) -> Any | None:
        """Resolve an object ID, retaining the legacy list-index fallback.

        The `_object_map` dict (stable id -> object) is the source of truth;
        the list-index fallback exists only for older serialized actions/fixtures
        recorded before every producer assigned a stable object_id, and is
        expected to be exercised rarely in current code paths.
        """
        object_map = getattr(canvas, "_object_map", None)
        if isinstance(object_map, dict) and object_id in object_map:
            return object_map[object_id]

        objects = canvas.current_page_objects()
        if isinstance(object_id, int) and 0 <= object_id < len(objects):
            logger.warning(
                "Action object_id %r was not found in _object_map; "
                "using legacy page-list index fallback",
                object_id,
            )
            return objects[object_id]
        logger.warning("Action object_id %r could not be resolved", object_id)
        return None

    @classmethod
    def register(cls, action_type: str):
        """Class decorator: register a concrete Action subclass under `action_type`
        so `deserialize()` can find it without a central if/elif chain. Applied
        immediately below each class definition, e.g. `@Action.register("move_annotation")`.
        """
        def decorator(subcls: type["Action"]) -> type["Action"]:
            cls._registry[action_type] = subcls
            return subcls
        return decorator

    @staticmethod
    def deserialize(data: dict[str, Any]) -> Action:
        """Deserialize action from dictionary."""
        action_type = data.get("type")
        subcls = Action._registry.get(action_type)
        if subcls is None:
            raise ValueError(f"Unknown action type: {action_type}")
        return subcls.from_data(data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.data})"


class CompositeAction(Action):
    """Groups multiple sub-actions into a single undo/redo unit.

    Used for multi-select operations (delete, duplicate) so that a single
    Ctrl+Z/Ctrl+Y undoes/redoes all affected objects at once, instead of one
    object at a time. Sub-actions execute in construction order and undo in
    reverse order (like a transaction log).

    Not serializable via from_data(); it's only ever built live by canvas.py,
    never recorded in the action-recorder fixture format.
    """

    def __init__(self, actions: list[Action]) -> None:
        super().__init__("composite", {})
        self._actions = actions

    def execute(self, canvas: Any) -> None:
        for action in self._actions:
            action.execute(canvas)

    def undo(self, canvas: Any) -> None:
        for action in reversed(self._actions):
            action.undo(canvas)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({len(self._actions)} sub-actions)"


class MergeableAction(Action):
    """Mixin for actions that support coalescing (merging consecutive actions)."""

    def merge(self, other: MergeableAction) -> None:
        """Merge another action into this one by updating the target state.
        
        This is called when consecutive move/resize operations on the same object
        occur. We keep the initial state (if present) and update only the target.
        
        Args:
            other: The new action to merge into this one
        """
        # Get the target state from the incoming action
        other_target = other.get_target_state()
        
        # Update our target state
        self.set_target_state(other_target)

    def has_initial_state(self) -> bool:
        """Check if this action has initial state (full format)."""
        # For move: from_x and from_y indicate full format
        # For resize: from_width and from_height indicate full format
        return any(key in self.data for key in ["from_x", "from_y", "from_width", "from_height"])

    def get_target_state(self) -> dict[str, Any]:
        """Get the target state from this action.
        
        Returns:
            Dictionary with target position/size keys (x, y, width, height, etc.)
        """
        raise NotImplementedError("Subclasses must implement get_target_state")

    def set_target_state(self, target: dict[str, Any]) -> None:
        """Update the target state in this action.
        
        Args:
            target: Dictionary with target position/size keys
        """
        raise NotImplementedError("Subclasses must implement set_target_state")


@Action.register("move_annotation")
class MoveAnnotationAction(MergeableAction):
    """Action: Move an annotation to a new position.
    
    Partial format: {type, object_id, x, y}
    Full format: {type, object_id, from_x, from_y, to_x, to_y}
    """

    def __init__(
        self,
        object_id: int,
        x: float | None = None,
        y: float | None = None,
        from_x: float | None = None,
        from_y: float | None = None,
        to_x: float | None = None,
        to_y: float | None = None,
    ) -> None:
        """Initialize move action.
        
        Partial format (from action recorder):
            MoveAnnotationAction(object_id=0, x=300, y=400)
        
        Full format (from canvas drag):
            MoveAnnotationAction(object_id=0, from_x=100, from_y=100, to_x=300, to_y=400)
        """
        data: dict[str, Any] = {"object_id": object_id}
        
        if from_x is not None and from_y is not None and to_x is not None and to_y is not None:
            # Full format: capture initial state
            data.update({"from_x": from_x, "from_y": from_y, "to_x": to_x, "to_y": to_y})
        elif x is not None and y is not None:
            # Partial format: only target
            data.update({"x": x, "y": y})
        else:
            raise ValueError("MoveAnnotationAction requires either (x, y) or (from_x, from_y, to_x, to_y)")
        
        super().__init__("move_annotation", data)

    def execute(self, canvas: Any) -> None:
        """Move annotation to target position."""
        obj_id = self.data["object_id"]
        target = self.get_target_state()
        
        obj = self.find_object(canvas, obj_id)
        if obj is not None:
            obj.x = target["x"]
            obj.y = target["y"]
        
        # Emit signal to update canvas (required for render to work properly)
        canvas.objectChanged.emit()

    def undo(self, canvas: Any) -> None:
        """Move annotation back to initial position."""
        if not self.has_initial_state():
            raise ValueError("Cannot undo move without initial state")
        
        obj_id = self.data["object_id"]
        
        obj = self.find_object(canvas, obj_id)
        if obj is not None:
            obj.x = self.data["from_x"]
            obj.y = self.data["from_y"]
        canvas.objectChanged.emit()

    def get_target_state(self) -> dict[str, Any]:
        """Get target position (x, y)."""
        if self.has_initial_state():
            return {"x": self.data["to_x"], "y": self.data["to_y"]}
        else:
            return {"x": self.data["x"], "y": self.data["y"]}

    def set_target_state(self, target: dict[str, Any]) -> None:
        """Update target position."""
        if self.has_initial_state():
            self.data["to_x"] = target["x"]
            self.data["to_y"] = target["y"]
        else:
            self.data["x"] = target["x"]
            self.data["y"] = target["y"]

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> MoveAnnotationAction:
        """Create action from serialized data."""
        return cls(
            object_id=data["object_id"],
            x=data.get("x"),
            y=data.get("y"),
            from_x=data.get("from_x"),
            from_y=data.get("from_y"),
            to_x=data.get("to_x"),
            to_y=data.get("to_y"),
        )


@Action.register("resize_annotation")
class ResizeAnnotationAction(MergeableAction):
    """Action: Resize an annotation.
    
    Partial format: {type, object_id, width, height, handle (optional)}
    Full format: {type, object_id, from_width, from_height, to_width, to_height, handle (optional)}
    
    For endpoint-based shapes (arrows/lines) with handle 0 or 1, the non-dragged endpoint
    is kept fixed at its original position.
    """

    def __init__(
        self,
        object_id: int,
        width: float | None = None,
        height: float | None = None,
        from_width: float | None = None,
        from_height: float | None = None,
        to_width: float | None = None,
        to_height: float | None = None,
        handle: int | None = None,
    ) -> None:
        """Initialize resize action."""
        data: dict[str, Any] = {"object_id": object_id}
        
        if from_width is not None and from_height is not None and to_width is not None and to_height is not None:
            # Full format
            data.update({"from_width": from_width, "from_height": from_height, "to_width": to_width, "to_height": to_height})
        elif width is not None and height is not None:
            # Partial format
            data.update({"width": width, "height": height})
        else:
            raise ValueError("ResizeAnnotationAction requires either (width, height) or (from_width, from_height, to_width, to_height)")
        
        if handle is not None:
            data["handle"] = handle
        
        super().__init__("resize_annotation", data)

    def _resize_to_size(self, obj: Any, handle: int | None, width: float, height: float) -> None:
        """Resize obj to (width, height), preserving the fixed endpoint's position
        if obj is an endpoint-based shape (line/arrow) being resized via handle 0/1.
        Shared by execute() and undo(), which only differ in which size to resize to.
        """
        if handle is not None and handle in (0, 1) and hasattr(obj, 'supports_endpoint_handles') and obj.supports_endpoint_handles():
            # Get the fixed endpoint position before resizing
            old_endpoints = obj.endpoint_points_doc()
            if len(old_endpoints) == 2:
                fixed_idx = 1 - handle  # If dragging handle 1, keep 0 fixed; if dragging 0, keep 1 fixed
                fixed_endpoint_doc = old_endpoints[fixed_idx]

                obj.set_scaled_size(width, height)

                # Get the new endpoint positions after resizing
                new_endpoints = obj.endpoint_points_doc()
                if len(new_endpoints) == 2:
                    new_fixed_endpoint = new_endpoints[fixed_idx]

                    # Adjust object position to keep the fixed endpoint at its original location
                    dx = fixed_endpoint_doc.x() - new_fixed_endpoint.x()
                    dy = fixed_endpoint_doc.y() - new_fixed_endpoint.y()
                    obj.x += dx
                    obj.y += dy
            else:
                obj.set_scaled_size(width, height)
        else:
            obj.resize_to_bounds(width, height)

    def execute(self, canvas: Any) -> None:
        """Resize annotation to target size.
        
        For endpoint-based shapes (arrows/lines), keeps the non-dragged endpoint fixed.
        """
        obj_id = self.data["object_id"]
        handle = self.data.get("handle")
        target = self.get_target_state()
        
        obj = self.find_object(canvas, obj_id)
        if obj is None:
            canvas.objectChanged.emit()
            return

        self._resize_to_size(obj, handle, target["width"], target["height"])
        canvas.objectChanged.emit()

    def undo(self, canvas: Any) -> None:
        """Resize annotation back to initial size."""
        obj_id = self.data["object_id"]
        if not self.has_initial_state():
            raise ValueError("Cannot undo resize without initial state")
        
        from_w = self.data["from_width"]
        from_h = self.data["from_height"]
        handle = self.data.get("handle")
        
        obj = self.find_object(canvas, obj_id)
        if obj is None:
            canvas.objectChanged.emit()
            return

        self._resize_to_size(obj, handle, from_w, from_h)
        canvas.objectChanged.emit()

    def get_target_state(self) -> dict[str, Any]:
        """Get target size (width, height)."""
        if self.has_initial_state():
            return {"width": self.data["to_width"], "height": self.data["to_height"]}
        else:
            return {"width": self.data["width"], "height": self.data["height"]}

    def set_target_state(self, target: dict[str, Any]) -> None:
        """Update target size."""
        if self.has_initial_state():
            self.data["to_width"] = target["width"]
            self.data["to_height"] = target["height"]
        else:
            self.data["width"] = target["width"]
            self.data["height"] = target["height"]

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> ResizeAnnotationAction:
        """Create action from serialized data."""
        return cls(
            object_id=data["object_id"],
            width=data.get("width"),
            height=data.get("height"),
            from_width=data.get("from_width"),
            from_height=data.get("from_height"),
            to_width=data.get("to_width"),
            to_height=data.get("to_height"),
            handle=data.get("handle"),
        )


@Action.register("add_annotation")
class AddAnnotationAction(Action):
    """Action: Add a new annotation."""

    def __init__(self, annotation_data: dict[str, Any] | None = None) -> None:
        """Initialize add action.
        
        Args:
            annotation_data: Serialized annotation data
        """
        super().__init__("add_annotation", annotation_data or {})
        self._added_object = None  # Store reference to the object we added

    def execute(self, canvas: Any) -> None:
        """Add annotation to current page."""
        from ..constants import DPI_SCALE
        from ..objects import (
            LARGE_DEFAULT_TYPES,
            AnnotationType,
            VectorAnnotation,
            canvas_object_from_dict,
        )
        
        # Convert annotation_type to VectorAnnotation format
        data_for_creation = dict(self.data)  # Copy to avoid modifying original
        
        # If we have "annotation_type" (from action recorder), convert to proper format
        if "annotation_type" in data_for_creation and "ann_type" not in data_for_creation:
            data_for_creation["ann_type"] = data_for_creation["annotation_type"]
            
        # Ensure we have the required fields for VectorAnnotation creation
        obj = None
        if "ann_type" in data_for_creation:
            # Use VectorAnnotation.from_dict if we have the right format
            try:
                # Determine default base size for annotations created from
                # minimal action payloads. Match VectorAnnotation.__init__:
                # - 80 PDF points (333 px) for LARGE_DEFAULT_TYPES (arrow, line, rectangle, ellipse)
                # - 20 PDF points (83 px) for others (checkmark, crossmark)
                ann_type_str = data_for_creation["ann_type"]
                try:
                    ann_type = AnnotationType(ann_type_str)
                except ValueError:
                    ann_type = None
                
                # Add default values for any missing fields
                if ann_type in LARGE_DEFAULT_TYPES:
                    default_base_size_points = 80.0
                else:
                    default_base_size_points = 20.0
                default_base_size_scaled = default_base_size_points * DPI_SCALE
                
                if "base_width" not in data_for_creation:
                    data_for_creation["base_width"] = default_base_size_scaled
                if "base_height" not in data_for_creation:
                    data_for_creation["base_height"] = default_base_size_scaled
                    
                if "scale" not in data_for_creation:
                    data_for_creation["scale"] = 1.0
                if "color" not in data_for_creation:
                    data_for_creation["color"] = "#FF0000"  # Red default
                if "font_family" not in data_for_creation:
                    data_for_creation["font_family"] = "Arial"
                if "font_size_pt" not in data_for_creation:
                    data_for_creation["font_size_pt"] = 12
                obj = VectorAnnotation.from_dict(data_for_creation)
            except (KeyError, ValueError, TypeError):
                # Fallback: try canvas_object_from_dict
                obj = None
        
        # Fallback if VectorAnnotation creation failed
        if obj is None:
            obj = canvas_object_from_dict(data_for_creation)
            
        if obj:
            if obj.page not in canvas._page_objects:
                canvas._page_objects[obj.page] = []
            canvas._page_objects[obj.page].append(obj)
            self._added_object = obj  # Store reference for later undo
            
            # Sync to canvas's object map if object_id is present in data
            obj_id = self.data.get("object_id")
            if obj_id is not None and hasattr(canvas, '_object_map'):
                canvas._object_map[obj_id] = obj
            
            canvas.objectChanged.emit()

    def undo(self, canvas: Any) -> None:
        """Remove the added annotation.

        Tries several strategies in order of reliability to find the exact
        object this action added, since older serialized actions may lack a
        stable object_id. Each `_undo_via_*` helper returns True if it found
        and removed the object (and emitted objectChanged), stopping the chain.
        """
        page = self.data.get("page", canvas.current_page)
        obj_id = self.data.get("object_id")

        if self._undo_via_direct_reference(canvas, page, obj_id):
            return
        if self._undo_via_object_map(canvas, page, obj_id):
            return
        if self._undo_via_property_match(canvas, page, obj_id):
            return
        self._undo_via_lifo_fallback(canvas, page, obj_id)

    def _undo_via_direct_reference(self, canvas: Any, page: int, obj_id: int | None) -> bool:
        """Most reliable: remove the exact object reference captured when it was added."""
        if not self._added_object:
            return False
        objects_on_page = canvas._page_objects.get(page)
        if objects_on_page is not None:
            try:
                objects_on_page.remove(self._added_object)
            except ValueError:
                # Tracked reference is no longer on this page; use the same logged
                # LIFO fallback as the last-resort strategy below instead of
                # silently popping an unrelated object here.
                self._undo_via_lifo_fallback(canvas, page, obj_id)
                return True
        if obj_id is not None and hasattr(canvas, '_object_map'):
            canvas._object_map.pop(obj_id, None)
        canvas.objectChanged.emit()
        return True

    def _undo_via_object_map(self, canvas: Any, page: int, obj_id: int | None) -> bool:
        """Look up the object by its stable id in canvas._object_map."""
        if obj_id is None or not hasattr(canvas, '_object_map') or obj_id not in canvas._object_map:
            return False
        obj_to_remove = canvas._object_map[obj_id]
        if page in canvas._page_objects:
            try:
                canvas._page_objects[page].remove(obj_to_remove)
            except ValueError:
                pass  # Object not on this page
        canvas._object_map.pop(obj_id, None)
        canvas.objectChanged.emit()
        return True

    def _undo_via_property_match(self, canvas: Any, page: int, obj_id: int | None) -> bool:
        """Fallback: match by type/position. With every producer now assigning a
        stable object_id (see canvas.py's _stable_id_for), this should not normally
        trigger; logs a warning so any remaining gaps are visible instead of
        silently mutating the wrong object.
        """
        objects_on_page = canvas._page_objects.get(page)
        if not objects_on_page:
            return False
        target_x = self.data.get("x")
        target_y = self.data.get("y")
        target_type = self.data.get("annotation_type")

        # Search backwards to find a matching object (likely the most recently added)
        for i in range(len(objects_on_page) - 1, -1, -1):
            obj = objects_on_page[i]
            # Check if this object matches the annotation we added
            # Support both annotation_type and ann_type attributes
            obj_type = getattr(obj, 'annotation_type', None) or getattr(obj, 'ann_type', None)
            if (target_type and obj_type == target_type and
                    target_x is not None and target_y is not None and
                    abs(obj.x - target_x) < 0.1 and abs(obj.y - target_y) < 0.1):
                logger.warning(
                    "AddAnnotationAction.undo(): object_id %r not found; "
                    "fell back to property matching (type/position)", obj_id,
                )
                objects_on_page.pop(i)
                if obj_id is not None and hasattr(canvas, '_object_map'):
                    canvas._object_map.pop(obj_id, None)
                canvas.objectChanged.emit()
                return True
        return False

    def _undo_via_lifo_fallback(self, canvas: Any, page: int, obj_id: int | None) -> None:
        """Last resort: remove the last object on the page (Last In First Out).
        May remove the wrong object if none of the more targeted strategies matched.
        """
        objects_on_page = canvas._page_objects.get(page)
        if not objects_on_page:
            return
        logger.warning(
            "AddAnnotationAction.undo(): object_id %r not found and no property "
            "match; falling back to removing the last object on the page (LIFO), "
            "which may remove the wrong object", obj_id,
        )
        objects_on_page.pop()
        if obj_id is not None and hasattr(canvas, '_object_map'):
            canvas._object_map.pop(obj_id, None)
        canvas.objectChanged.emit()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> AddAnnotationAction:
        """Create action from serialized data."""
        return cls(data)


@Action.register("delete_annotation")
class DeleteAnnotationAction(Action):
    """Action: Delete an annotation.

    `object_id` is the object's stable id (key in `canvas._object_map`), not
    a list position — list positions shift whenever other objects are
    added/removed and would silently target the wrong object otherwise.
    The producer (canvas.py) also sets `_deleted_object`/`_deleted_index`
    directly (mirroring `AddAnnotationAction._added_object`) so undo restores
    the exact same object at its original z-order position.
    """

    def __init__(self, object_id: int, object_data: dict[str, Any] | None = None) -> None:
        """Initialize delete action.
        
        Args:
            object_id: Stable id of the object to delete
            object_data: Serialized object data for undo (fallback if no direct reference)
        """
        data = {"object_id": object_id}
        if object_data:
            data["object_data"] = object_data
        super().__init__("delete_annotation", data)
        self._deleted_object: Any = None  # Direct reference, set by canvas or execute()
        self._deleted_index: int | None = None  # Position to restore to on undo

    def execute(self, canvas: Any) -> None:
        """Delete annotation from current page (used to redo a previously-undone delete)."""
        obj_id = self.data["object_id"]
        obj = self._deleted_object
        if obj is None and hasattr(canvas, "_object_map"):
            obj = canvas._object_map.get(obj_id)
        objects = canvas.current_page_objects()
        if obj is None and 0 <= obj_id < len(objects):
            # Legacy fallback: object_id is an array index rather than a stable id.
            obj = objects[obj_id]
        if obj is not None and obj in objects:
            self._deleted_index = objects.index(obj)
            objects.remove(obj)
            self._deleted_object = obj
            if hasattr(canvas, "_object_map"):
                canvas._object_map.pop(obj_id, None)
            canvas.objectChanged.emit()

    def undo(self, canvas: Any) -> None:
        """Restore the deleted annotation at its original position."""
        obj = self._deleted_object
        if obj is None and "object_data" in self.data:
            from ..objects import canvas_object_from_dict
            obj = canvas_object_from_dict(self.data["object_data"])
        if obj is not None:
            objects = canvas.current_page_objects()
            index = self._deleted_index if self._deleted_index is not None else len(objects)
            index = max(0, min(index, len(objects)))
            objects.insert(index, obj)
            obj_id = self.data["object_id"]
            if hasattr(canvas, "_object_map"):
                canvas._object_map[obj_id] = obj
            canvas.objectChanged.emit()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> DeleteAnnotationAction:
        """Create action from serialized data."""
        return cls(
            object_id=data["object_id"],
            object_data=data.get("object_data"),
        )


class PropertyChangeAction(Action):
    """Shared base for "set one attribute on an annotation" actions (color, line
    width, font size, font family - see the four concrete subclasses below).

    All four historically had near-identical `execute`/`undo`/`from_data` bodies
    that only differed in the attribute name and data dict keys involved; this
    base implements that shared shape once. Subclasses configure it via class
    attributes and small optional hooks:
      - `action_type_str` / `data_key` / `from_data_key`: the serialized "type"
        string and the dict keys for the new/previous value (must match the
        historical names - they're part of the on-disk/fixture format).
      - `attr_name`: the attribute set on the annotation object.
      - `calls_canvas_update`: whether to call `canvas.update()` in addition to
        `canvas.objectChanged.emit()` (matches each action's original behavior).
      - `_convert(value)`: override to convert the stored value before setting
        it on the object (e.g. `str` -> `QColor` for color).
      - `_post_set(obj)`: override to run a side effect after setting the value
        (e.g. `obj.fit_text_box()` for font changes).
    Subclasses keep their own `__init__` (preserving their historical keyword
    argument names for API compatibility) which calls `_init_property_data()`.
    """

    action_type_str: str = ""
    data_key: str = ""
    from_data_key: str = ""
    attr_name: str = ""
    calls_canvas_update: bool = True

    def _init_property_data(
        self,
        object_id: int | None,
        value: Any,
        from_value: Any,
        include_from: bool | None = None,
        always_include_object_id: bool = False,
    ) -> None:
        data: dict[str, Any] = {self.data_key: value}
        if object_id is not None or always_include_object_id:
            data["object_id"] = object_id
        if include_from is None:
            include_from = from_value is not None
        if include_from:
            data[self.from_data_key] = from_value
        super().__init__(self.action_type_str, data)

    def _convert(self, value: Any) -> Any:
        return value

    def _post_set(self, obj: Any) -> None:
        pass

    def _apply_value(self, canvas: Any, key: str) -> None:
        if key in self.data and "object_id" in self.data:
            obj = self.find_object(canvas, self.data["object_id"])
            if obj is not None and hasattr(obj, self.attr_name):
                setattr(obj, self.attr_name, self._convert(self.data[key]))
                self._post_set(obj)
        if self.calls_canvas_update:
            canvas.update()
        canvas.objectChanged.emit()

    def execute(self, canvas: Any) -> None:
        self._apply_value(canvas, self.data_key)

    def undo(self, canvas: Any) -> None:
        self._apply_value(canvas, self.from_data_key)


@Action.register("change_color")
class ChangeColorAction(PropertyChangeAction):
    """Action: Change annotation or default color."""

    action_type_str = "change_color"
    data_key = "color"
    from_data_key = "from_color"
    attr_name = "color"
    calls_canvas_update = False

    def __init__(self, object_id: int | None = None, color: str = "", from_color: str | None = None) -> None:
        """Initialize color change action.
        
        Args:
            object_id: ID of object (None for default color)
            color: New color (hex string)
            from_color: Previous color (for undo)
        """
        self._init_property_data(object_id, color, from_color, include_from=bool(from_color))

    def _convert(self, value: str) -> Any:
        from PySide6.QtGui import QColor
        return QColor(value)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> ChangeColorAction:
        """Create action from serialized data."""
        return cls(
            object_id=data.get("object_id"),
            color=data.get("color", ""),
            from_color=data.get("from_color"),
        )


@Action.register("set_text")
class SetTextAnnotationAction(Action):
    """Action: Change text of a text annotation."""

    def __init__(self, object_id: int, text: str = "", from_text: str | None = None) -> None:
        """Initialize set text action.
        
        Args:
            object_id: Stable id of the text object (see canvas._stable_id_for)
            text: New text content
            from_text: Previous text (for undo)
        """
        data = {"object_id": object_id, "text": text}
        if from_text is not None:
            data["from_text"] = from_text
        super().__init__("set_text", data)

    @staticmethod
    def _find_object(canvas: Any, obj_id: int) -> Any:
        return Action.find_object(canvas, obj_id)

    def execute(self, canvas: Any) -> None:
        """Set text on annotation."""
        obj = self._find_object(canvas, self.data["object_id"])
        if obj is not None:
            obj.text = self.data["text"]
            if hasattr(obj, 'fit_text_box'):
                obj.fit_text_box()
        canvas.objectChanged.emit()

    def undo(self, canvas: Any) -> None:
        """Restore previous text."""
        if "from_text" in self.data:
            obj = self._find_object(canvas, self.data["object_id"])
            if obj is not None:
                obj.text = self.data["from_text"]
                if hasattr(obj, 'fit_text_box'):
                    obj.fit_text_box()
        canvas.objectChanged.emit()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> SetTextAnnotationAction:
        """Create action from serialized data."""
        return cls(
            object_id=data["object_id"],
            text=data.get("text", ""),
            from_text=data.get("from_text"),
        )


@Action.register("paste_annotation")
class PasteAnnotationAction(Action):
    """Action: Paste annotation from clipboard."""

    def __init__(self, pasted_objects_data: list[dict[str, Any]] | None = None) -> None:
        """Initialize paste action.
        
        Args:
            pasted_objects_data: Serialized data of pasted objects
        """
        data = {}
        if pasted_objects_data:
            data["pasted_objects_data"] = pasted_objects_data
        super().__init__("paste_annotation", data)
        self._pasted_objects: list[Any] = []  # Direct references, set by canvas at paste time

    def execute(self, canvas: Any) -> None:
        """Paste annotations (used to redo a previously-undone paste)."""
        objects = canvas.current_page_objects()
        if self._pasted_objects:
            for index, obj in enumerate(self._pasted_objects):
                if obj not in objects:
                    objects.append(obj)
                if hasattr(canvas, "_object_map") and isinstance(canvas._object_map, dict):
                    object_data = self.data.get("pasted_objects_data", [])
                    object_id = object_data[index].get("object_id") if index < len(object_data) else None
                    if object_id is not None:
                        canvas._object_map[object_id] = obj
            canvas.objectChanged.emit()
        elif "pasted_objects_data" in self.data:
            from ..objects import canvas_object_from_dict
            recreated = []
            for obj_data in self.data["pasted_objects_data"]:
                obj = canvas_object_from_dict(obj_data)
                if obj:
                    objects.append(obj)
                    recreated.append(obj)
                    object_id = obj_data.get("object_id")
                    if hasattr(canvas, "_object_map") and isinstance(canvas._object_map, dict):
                        if object_id is None:
                            object_id = canvas._register_object(obj)
                        else:
                            canvas._object_map[object_id] = obj
                            canvas._next_object_id = max(canvas._next_object_id, object_id + 1)
            self._pasted_objects = recreated
            canvas.objectChanged.emit()

    def undo(self, canvas: Any) -> None:
        """Remove exactly the pasted annotations, not merely the last N objects."""
        if self._pasted_objects:
            objects = canvas.current_page_objects()
            for obj in self._pasted_objects:
                if obj in objects:
                    objects.remove(obj)
                if hasattr(canvas, "_object_map") and isinstance(canvas._object_map, dict):
                    for object_id, mapped_obj in list(canvas._object_map.items()):
                        if mapped_obj is obj:
                            del canvas._object_map[object_id]
            canvas.objectChanged.emit()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> PasteAnnotationAction:
        """Create action from serialized data."""
        return cls(pasted_objects_data=data.get("pasted_objects_data"))


@Action.register("change_page")
class ChangePageAction(Action):
    """Action: Navigate to a different page."""

    def __init__(self, to_page: int, from_page: int | None = None) -> None:
        """Initialize page change action.
        
        Args:
            to_page: Target page number (0-indexed)
            from_page: Previous page number (for undo)
        """
        data = {"to_page": to_page}
        if from_page is not None:
            data["from_page"] = from_page
        super().__init__("change_page", data)

    def execute(self, canvas: Any) -> None:
        """Navigate to target page."""
        canvas.goto_page(self.data["to_page"])

    def undo(self, canvas: Any) -> None:
        """Return to previous page."""
        if "from_page" in self.data:
            canvas.goto_page(self.data["from_page"])

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> ChangePageAction:
        """Create action from serialized data."""
        return cls(
            to_page=data["to_page"],
            from_page=data.get("from_page"),
        )


@Action.register("rotate_page")
class RotatePageAction(Action):
    """Action: Rotate a page."""

    def __init__(self, page: int, to_rotation: int, from_rotation: int | None = None) -> None:
        """Initialize rotate action.
        
        Args:
            page: Page to rotate (0-indexed, -1 for all pages)
            to_rotation: Target rotation (0, 90, 180, 270)
            from_rotation: Previous rotation (for undo)
        """
        data = {"page": page, "to_rotation": to_rotation}
        if from_rotation is not None:
            data["from_rotation"] = from_rotation
        super().__init__("rotate_page", data)

    def execute(self, canvas: Any) -> None:
        """Rotate page."""
        if self.data["page"] == -1:
            # Rotate all pages
            for page_idx in range(canvas.page_count):
                canvas._page_rotations[page_idx] = self.data["to_rotation"]
        else:
            canvas._page_rotations[self.data["page"]] = self.data["to_rotation"]
        canvas.update()

    def undo(self, canvas: Any) -> None:
        """Restore previous rotation."""
        if "from_rotation" in self.data:
            if self.data["page"] == -1:
                for page_idx in range(canvas.page_count):
                    canvas._page_rotations[page_idx] = self.data["from_rotation"]
            else:
                canvas._page_rotations[self.data["page"]] = self.data["from_rotation"]
            canvas.update()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> RotatePageAction:
        """Create action from serialized data."""
        return cls(
            page=data["page"],
            to_rotation=data["to_rotation"],
            from_rotation=data.get("from_rotation"),
        )


@Action.register("rotate_annotation")
class RotateAnnotationAction(Action):
    """Rotate and reposition one annotation as part of an object/group rotation."""

    def __init__(
        self,
        object_id: int,
        from_x: float,
        from_y: float,
        from_rotation: float,
        to_x: float,
        to_y: float,
        to_rotation: float,
    ) -> None:
        super().__init__(
            "rotate_annotation",
            {
                "object_id": object_id,
                "from_x": from_x,
                "from_y": from_y,
                "from_rotation": from_rotation,
                "to_x": to_x,
                "to_y": to_y,
                "to_rotation": to_rotation,
            },
        )

    def _apply(self, canvas: Any, prefix: str) -> None:
        object_id = self.data["object_id"]
        obj = self.find_object(canvas, object_id)
        if obj is None:
            return
        obj.x = self.data[f"{prefix}_x"]
        obj.y = self.data[f"{prefix}_y"]
        obj.rotation = self.data[f"{prefix}_rotation"] % 360.0
        canvas.objectChanged.emit()
        canvas.update()

    def execute(self, canvas: Any) -> None:
        self._apply(canvas, "to")

    def undo(self, canvas: Any) -> None:
        self._apply(canvas, "from")

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> RotateAnnotationAction:
        return cls(
            object_id=data["object_id"],
            from_x=data["from_x"],
            from_y=data["from_y"],
            from_rotation=data["from_rotation"],
            to_x=data["to_x"],
            to_y=data["to_y"],
            to_rotation=data["to_rotation"],
        )


# v1.2.22: New action classes for annotation properties

@Action.register("change_line_width")
class ChangeLineWidthAction(PropertyChangeAction):
    """Action: Change line width of vector annotations."""

    action_type_str = "change_line_width"
    data_key = "line_width_pt"
    from_data_key = "from_line_width_pt"
    attr_name = "_line_width_pt"

    def __init__(self, object_id: int | None = None, line_width_pt: float = 1.5, from_line_width_pt: float | None = None) -> None:
        """Initialize line width change action.
        
        Args:
            object_id: ID of object
            line_width_pt: New line width in points
            from_line_width_pt: Previous line width (for undo)
        """
        self._init_property_data(object_id, line_width_pt, from_line_width_pt, always_include_object_id=True)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> ChangeLineWidthAction:
        """Create action from serialized data."""
        return cls(
            object_id=data.get("object_id"),
            line_width_pt=data.get("line_width_pt", 1.5),
            from_line_width_pt=data.get("from_line_width_pt"),
        )


@Action.register("change_font_size")
class ChangeFontSizeAction(PropertyChangeAction):
    """Action: Change font size of text annotations."""

    action_type_str = "change_font_size"
    data_key = "font_size_pt"
    from_data_key = "from_font_size_pt"
    attr_name = "_font_size_pt"

    def __init__(self, object_id: int | None = None, font_size_pt: int = 11, from_font_size_pt: int | None = None) -> None:
        """Initialize font size change action.
        
        Args:
            object_id: ID of object
            font_size_pt: New font size in points
            from_font_size_pt: Previous font size (for undo)
        """
        self._init_property_data(object_id, font_size_pt, from_font_size_pt, always_include_object_id=True)

    def _post_set(self, obj: Any) -> None:
        if hasattr(obj, 'fit_text_box'):
            obj.fit_text_box()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> ChangeFontSizeAction:
        """Create action from serialized data."""
        return cls(
            object_id=data.get("object_id"),
            font_size_pt=data.get("font_size_pt", 11),
            from_font_size_pt=data.get("from_font_size_pt"),
        )


@Action.register("change_font_family")
class ChangeFontFamilyAction(PropertyChangeAction):
    """Action: Change font family of text annotations."""

    action_type_str = "change_font_family"
    data_key = "font_family"
    from_data_key = "from_font_family"
    attr_name = "_font_family"

    def __init__(self, object_id: int | None = None, font_family: str = "Arial", from_font_family: str | None = None) -> None:
        """Initialize font family change action.
        
        Args:
            object_id: ID of object
            font_family: New font family name
            from_font_family: Previous font family (for undo)
        """
        self._init_property_data(
            object_id, font_family, from_font_family,
            include_from=bool(from_font_family), always_include_object_id=True,
        )

    def _post_set(self, obj: Any) -> None:
        if hasattr(obj, 'fit_text_box'):
            obj.fit_text_box()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> ChangeFontFamilyAction:
        """Create action from serialized data."""
        return cls(
            object_id=data.get("object_id"),
            font_family=data.get("font_family", "Arial"),
            from_font_family=data.get("from_font_family"),
        )
