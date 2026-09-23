from __future__ import annotations

import copy
import json
import logging
import math

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QPainter,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QApplication, QWidget

from .history import (
    AddAnnotationAction,
    ChangeColorAction,
    ChangeFontFamilyAction,
    ChangeFontSizeAction,
    ChangeLineWidthAction,
    CompositeAction,
    DeleteAnnotationAction,
    HistoryStack,
    MoveAnnotationAction,
    PasteAnnotationAction,
    ResizeAnnotationAction,
    RotateAnnotationAction,
    RotatePageAction,
)
from .objects import (
    ANCHOR_HANDLE,
    DUPLICATE_OFFSET,
    FONT_SIZE_STEPS_PT,
    HANDLE_FX,
    HANDLE_FY,
    LINE_WIDTH_STEPS_PT,
    AnnotationType,
    CanvasObject,
    VectorAnnotation,
    canvas_object_from_dict,
    step_size,
)

# Group (multi-selection) rotation handle geometry, in view pixels.
GROUP_ROTATION_HANDLE_OFFSET: float = 24.0
GROUP_ROTATION_HANDLE_RADIUS: float = 6.0

logger = logging.getLogger(__name__)

# Arrow-key nudge distance for selected annotations, in document points.
KEYBOARD_MOVE_STEP_PT: float = 12.0
KEYBOARD_MOVE_FINE_STEP_PT: float = 1.0


def _normalize_page_rotation(angle: int) -> int:
    """Clamp a stored page rotation to the nearest of the four supported
    orientations (0/90/180/270) - the only values the coordinate-transform code
    understands. Guards against malformed/hand-edited project file data.
    """
    return round((angle % 360) / 90) % 4 * 90


class DocumentCanvas(QWidget):
    objectChanged = Signal()        # emitted on move/scale/add/remove
    pageChanged = Signal(int, int)  # (current_page_0indexed, total_pages)
    editRequested = Signal(object)  # CanvasObject — double-click
    fileDrop = Signal(str)          # emitted when file is dropped (file path)
    pasteIncomplete = Signal(int, int)  # (skipped_count, total_count) — some items couldn't be pasted

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)  # Enable drag-and-drop

        # History management
        self.history = HistoryStack()
        self._next_object_id: int = 0  # Auto-incrementing ID for stable object references

        self._pages: list[Image.Image] = []
        self._page_pixmaps: list[QPixmap] = []
        self._current_page: int = 0
        self._page_objects: dict[int, list[CanvasObject]] = {}
        self._object_map: dict[int, CanvasObject] = {}  # ID-based object lookup for stable references
        self._page_rotations: dict[int, int] = {}  # Track rotation angle (0, 90, 180, 270) per page

        self._selected: CanvasObject | None = None
        self._selected_multiple: set[CanvasObject] = set()  # Multi-selection
        self._dragging: bool = False
        self._drag_handle: int = -1
        self._cached_copy_data: list[dict] | None = None  # Cache copy data to preserve original positions

        self._drag_doc_offset_x: float = 0.0
        self._drag_doc_offset_y: float = 0.0

        # Track initial drag state for action recording (move/resize)
        self._drag_start_x: float = 0.0  # Initial position when drag starts
        self._drag_start_y: float = 0.0
        self._drag_start_w: float = 0.0  # Initial size when resize starts
        self._drag_start_h: float = 0.0
        self._action_recorded_this_drag: bool = False  # Track if action was recorded yet
        self._drag_endpoint_handles: bool = False
        self._rotating: bool = False
        self._rotation_drag_states: list[tuple[CanvasObject, float, float, float]] = []
        self._rotation_pivot_doc = QPointF()
        self._rotation_pivot_view = QPointF()
        self._rotation_start_pointer_angle: float = 0.0
        self._rotation_start_primary_angle: float = 0.0

        self._hdrag_anchor_doc: QPointF = QPointF()
        self._hdrag_anchor_fx: float = 0.0
        self._hdrag_anchor_fy: float = 0.0
        self._hdrag_start_w: float = 1.0
        self._hdrag_start_h: float = 1.0
        self._hdrag_rotation: float = 0.0
        self._hdrag_start_center_doc = QPointF()

        self._fit_scale: float = 1.0
        self._doc_offset_x: float = 0.0
        self._doc_offset_y: float = 0.0

    # ---------------------------------------------------------------- document API

    @property
    def has_document(self) -> bool:
        return bool(self._pages)

    @property
    def page_count(self) -> int:
        return len(self._pages)

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def current_page_image(self) -> Image.Image | None:
        return self._pages[self._current_page] if self._pages else None

    def current_page_objects(self) -> list[CanvasObject]:
        return self._page_objects.get(self._current_page, [])

    def page_image_at(self, index: int) -> Image.Image | None:
        if 0 <= index < len(self._pages):
            return self._pages[index]
        return None

    def page_objects_at(self, index: int) -> list[CanvasObject]:
        return self._page_objects.get(index, [])

    def page_objects_with_rotation_at(self, index: int) -> list[CanvasObject]:
        """Get objects for a page with coordinates transformed for rotation.
        
        For export: returns objects with centers and display angles adjusted for
        the rotated page orientation without mutating their persisted geometry.
        """
        objects = self._page_objects.get(index, [])
        rotation = self._page_rotations.get(index, 0)
        
        if rotation == 0:
            # No rotation, return objects as-is
            return objects
        
        if index < 0 or index >= len(self._pages):
            raise IndexError(
                f"page index {index} is out of range for a {len(self._pages)}-page document"
            )

        orig_width, orig_height = self._pages[index].size
        transformed = []
        
        for obj in objects:
            new_x, new_y = self._rotated_top_left_for_object(obj, rotation, orig_width, orig_height)
            
            # Create a shallow copy of the object with transformed coordinates
            obj_copy = copy.copy(obj)
            obj_copy.x = new_x
            obj_copy.y = new_y
            obj_copy.rotation = (obj.rotation - rotation) % 360.0
            transformed.append(obj_copy)
        
        return transformed

    def _reset_document_state(self) -> None:
        """Drop every piece of state that belongs to the document being replaced.

        All per-document state must be reset here, not inline in `set_pages`:
        `_page_rotations` was once missed there and leaked into the next opened
        document, drawing a freshly-loaded page stretched into a transposed rect.
        Anything deliberately kept across documents (the clipboard cache) stays
        in `set_pages` so the exception is visible.
        """
        self._current_page = 0
        self._page_objects = {}
        self._object_map = {}
        self._next_object_id = 0
        self._page_rotations = {}
        self._clear_selection_state()
        self._reset_drag_state()
        self.history.clear()

    def set_pages(self, pages: list[Image.Image]) -> None:
        if self._cached_copy_data is not None and self._pages:
            # The clipboard survives a document change; its page association doesn't.
            self._cached_copy_data = [
                {**item, "page": None} for item in self._cached_copy_data
            ]
        self._reset_document_state()
        self._pages = [p.convert("RGB") for p in pages]
        self._page_pixmaps = [QPixmap.fromImage(ImageQt(p)) for p in self._pages]
        self._recompute_fit()
        self.pageChanged.emit(0, len(self._pages))
        self._invalidate_display()

    def restore_objects(
        self,
        objects: list[CanvasObject],
        rotations: dict[int, int] | None = None,
        current_page: int = 0,
    ) -> None:
        """Restore serialized project objects without creating undo history."""
        self._page_objects = {}
        self._object_map = {}
        self._next_object_id = 0
        self._page_rotations = {
            int(page): _normalize_page_rotation(int(angle))
            for page, angle in (rotations or {}).items()
            if str(page).lstrip("-").isdigit()
        }
        self._refresh_rotated_pixmaps()
        for obj in objects:
            self._register_object(obj)
            self._page_objects.setdefault(obj.page, []).append(obj)
        self._current_page = max(0, min(current_page, len(self._pages) - 1)) if self._pages else 0
        self._clear_selection_state()
        self._recompute_fit()
        self.pageChanged.emit(self._current_page, len(self._pages))
        self._invalidate_display()

    def goto_page(self, page: int) -> None:
        if not self._pages:
            return
        page = max(0, min(page, len(self._pages) - 1))
        if page == self._current_page:
            return
        self._clear_selection_state()
        self._current_page = page
        self._recompute_fit()
        self.pageChanged.emit(self._current_page, len(self._pages))
        self._invalidate_display()

    def _get_rotated_page_image(self, page_index: int) -> Image.Image:
        """Get the PIL image for a page, applying rotation if set."""
        if page_index < 0 or page_index >= len(self._pages):
            raise IndexError(
                f"page index {page_index} is out of range for a {len(self._pages)}-page document"
            )

        original = self._pages[page_index]
        rotation = self._page_rotations.get(page_index, 0)
        
        if rotation == 0:
            return original
        elif rotation == 90:
            return original.rotate(90, expand=True)
        elif rotation == 180:
            return original.rotate(180, expand=True)
        elif rotation == 270:
            return original.rotate(270, expand=True)
        else:
            return original
    
    def _rotate_pages(self, pages: list[int] | range, delta: int) -> None:
        """Rotate the given page indices by `delta` degrees (90 or 270)."""
        from_rotations: dict[int, int] = {}
        to_rotations: dict[int, int] = {}
        for i in pages:
            from_rotations[i] = self._page_rotations.get(i, 0)
            self._page_rotations[i] = (from_rotations[i] + delta) % 360
            to_rotations[i] = self._page_rotations[i]
            self._update_rotated_pixmap(i)
        if to_rotations:
            self.history.record_action(RotatePageAction(from_rotations, to_rotations))
        self._recompute_fit()
        self._invalidate_display()

    def rotate_current_page_left(self) -> None:
        """Rotate current page 90 degrees counter-clockwise."""
        self._rotate_pages([self._current_page], 90)

    def rotate_current_page_right(self) -> None:
        """Rotate current page 90 degrees clockwise."""
        self._rotate_pages([self._current_page], 270)

    def rotate_all_pages_left(self) -> None:
        """Rotate all pages 90 degrees counter-clockwise."""
        self._rotate_pages(range(len(self._pages)), 90)

    def rotate_all_pages_right(self) -> None:
        """Rotate all pages 90 degrees clockwise."""
        self._rotate_pages(range(len(self._pages)), 270)
    
    def _update_rotated_pixmap(self, page_index: int) -> None:
        """Update the pixmap cache for a page after rotation."""
        if page_index < 0 or page_index >= len(self._page_pixmaps):
            return
        rotated_img = self._get_rotated_page_image(page_index)
        self._page_pixmaps[page_index] = QPixmap.fromImage(ImageQt(rotated_img))

    def _refresh_rotated_pixmaps(self) -> None:
        """Re-render every page whose stored rotation isn't reflected in its cached pixmap."""
        for page_index in self._page_rotations:
            self._update_rotated_pixmap(page_index)
    
    def get_page_image_with_rotation(self, page_index: int) -> Image.Image:
        """Get a PIL image for a page with rotation applied (for export)."""
        return self._get_rotated_page_image(page_index)

    # ---------------------------------------------------------------- undo/redo API

    def undo(self) -> bool:
        """Undo the last action.
        
        Returns:
            True if an action was undone, False if undo stack is empty
        """
        return self.history.undo(self)

    def redo(self) -> bool:
        """Redo the last undone action.
        
        Returns:
            True if an action was redone, False if redo stack is empty
        """
        return self.history.redo(self)

    def can_undo(self) -> bool:
        """Check if there are actions to undo."""
        return self.history.can_undo()

    def can_redo(self) -> bool:
        """Check if there are actions to redo."""
        return self.history.can_redo()

    def clear_history(self) -> None:
        """Clear undo/redo history (called when document is opened/closed)."""
        self.history.clear()

    # ---------------------------------------------------------------- object API

    @property
    def selected(self) -> CanvasObject | None:
        return self._selected

    def _register_object(self, obj: CanvasObject) -> int:
        """Assign a new stable history id to obj and register it in the object map."""
        obj_id = self._next_object_id
        self._next_object_id += 1
        self._object_map[obj_id] = obj
        return obj_id

    def _stable_id_for(self, obj: CanvasObject) -> int:
        """Return obj's stable history id used for undo/redo, registering it if needed.

        This must be used instead of a list index (`objs.index(obj)`) anywhere an
        Action needs an object_id: list indices shift when other objects are added
        or removed, silently pointing undo/redo at the wrong object.
        """
        for existing_id, existing_obj in self._object_map.items():
            if existing_obj is obj:
                return existing_id
        return self._register_object(obj)

    def _invalidate_display(self) -> None:
        """Notify listeners the canvas content changed and schedule a repaint."""
        self.objectChanged.emit()
        self.update()

    def _record_composite_action(self, actions: list) -> None:
        """Record a list of actions as one undo unit (a single Action if only one)."""
        if not actions:
            return
        self.history.record_action(actions[0] if len(actions) == 1 else CompositeAction(actions))

    def add_object(self, obj: CanvasObject) -> None:
        # Assign an auto-incrementing ID and register in _object_map
        obj_id = self._register_object(obj)

        self._page_objects.setdefault(self._current_page, []).append(obj)
        self._selected = obj
        self._invalidate_display()

        # Record the addition to history for undo support
        annotation_data = obj.to_dict()
        annotation_data["object_id"] = obj_id
        if hasattr(obj, 'ann_type'):
            annotation_data["ann_type"] = obj.ann_type.value
        action = AddAnnotationAction(annotation_data)
        action._added_object = obj  # So undo knows what to remove
        self.history.record_action(action)

    def remove_selected(self) -> None:
        """Remove selected annotation(s). Works with single or multi-selection."""
        if self.is_multi_selected():
            self.delete_selected()
        elif self._selected is None:
            return
        else:
            # Single selection - record delete action
            objs = self._page_objects.get(self._current_page, [])
            if self._selected in objs:
                obj_idx = objs.index(self._selected)
                obj_id = self._stable_id_for(self._selected)
                obj_data = self._selected.to_dict()
                objs.remove(self._selected)
                self._object_map.pop(obj_id, None)
                action = DeleteAnnotationAction(object_id=obj_id, object_data=obj_data)
                action._deleted_object = self._selected
                action._deleted_index = obj_idx
                self.history.record_action(action)
            self._selected = None
            self._invalidate_display()

    def duplicate_selected(self) -> None:
        """Duplicate selected annotation(s). Works with single or multi-selection."""
        if self.is_multi_selected():
            self.duplicate_selected_multi()
        elif self._selected is None:
            return
        else:
            # Single selection - original behavior
            dup = self._selected.duplicate()
            dup.page = self._current_page
            self.add_object(dup)

    # ---------------------------------------------------------------- multi-selection API

    def select_annotation(self, obj: CanvasObject, multi: bool = False) -> None:
        """Select an annotation.
        
        Args:
            obj: Annotation to select
            multi: If True, add/remove from multi-selection (Shift+click behavior).
                   If False, clear previous selection and select this one (click behavior).
        """
        if not multi:
            # Single selection mode
            self._selected = obj
            self._selected_multiple.clear()
        else:
            # Multi-selection mode (Shift+click)
            if self._selected is not None:
                self._selected_multiple.add(self._selected)
            if obj in self._selected_multiple:
                # Remove from selection
                self._selected_multiple.discard(obj)
                if obj is self._selected:
                    self._selected = next(iter(self._selected_multiple), None)
            else:
                # Add to selection
                self._selected_multiple.add(obj)
                # Keep _selected as primary for UI feedback
                if self._selected is None:
                    self._selected = obj
        self._invalidate_display()

    def _clear_selection_state(self) -> None:
        """Reset selection fields without emitting signals or repainting.

        Callers that already emit/update as part of a larger state change
        (e.g. `goto_page`, `restore_objects`) should use this instead of
        `clear_selection()` to avoid a redundant signal/repaint.
        """
        self._selected = None
        self._selected_multiple.clear()

    def clear_selection(self) -> None:
        """Clear all selections."""
        self._clear_selection_state()
        self._invalidate_display()

    def select_all_on_page(self) -> None:
        """Select all annotations on the current page."""
        objs = self.current_page_objects()
        if not objs:
            return
        self._selected_multiple.clear()
        self._selected_multiple.update(objs)
        if objs:
            self._selected = objs[0]  # Set first as primary
        self._invalidate_display()

    def get_selected_annotations(self) -> list[CanvasObject]:
        """Return all selected annotations (sorted for consistency)."""
        if self._selected_multiple:
            return sorted(self._selected_multiple, key=lambda o: (o.y, o.x))
        elif self._selected is not None:
            return [self._selected]
        return []

    def is_multi_selected(self) -> bool:
        """Check if multiple annotations are currently selected."""
        return len(self._selected_multiple) > 1

    def move_selected(self, dx: float, dy: float) -> None:
        """Move all selected annotations by (dx, dy) in document space.

        Recorded like a drag: consecutive nudges of the same single annotation
        coalesce into one undo entry, and any other action ends that run.
        """
        selected = self.get_selected_annotations()
        if not selected:
            return

        actions = []
        for obj in selected:
            from_x, from_y = obj.x, obj.y
            obj.x += dx
            obj.y += dy
            if self.current_page_image:
                pw, ph = self.current_page_image.size
                obj.clamp_to_page(pw, ph)
            actions.append(MoveAnnotationAction(
                object_id=self._stable_id_for(obj),
                from_x=from_x,
                from_y=from_y,
                to_x=obj.x,
                to_y=obj.y,
            ))

        self._record_composite_action(actions)
        self._invalidate_display()

    @staticmethod
    def _snap_rotation_angle(angle_deg: float, shift_pressed: bool) -> float:
        """Normalize an angle, snapping to 15-degree increments unless Shift is held (then 1-degree)."""
        step = 1.0 if shift_pressed else 15.0
        return DocumentCanvas._nearest_angle_step(angle_deg, step)

    def rotate_selected_to(self, angle_deg: float) -> None:
        """Rotate the selection as a group, using the primary object's angle as reference."""
        selected = self.get_selected_annotations()
        primary = self._selected
        if not selected or primary is None:
            return

        target = angle_deg % 360.0
        delta = (target - primary.rotation + 180.0) % 360.0 - 180.0
        if abs(delta) < 1e-9:
            return

        bounds = self._selection_doc_bounds(selected)
        pivot_x = bounds.center().x()
        pivot_y = bounds.center().y()
        radians = math.radians(delta)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        actions = []

        for obj in selected:
            center = self._object_center_doc(obj)
            center_x, center_y = center.x(), center.y()
            old_x, old_y, old_rotation = obj.x, obj.y, obj.rotation
            offset_x = center_x - pivot_x
            offset_y = center_y - pivot_y
            new_center_x = pivot_x + cos_a * offset_x - sin_a * offset_y
            new_center_y = pivot_y + sin_a * offset_x + cos_a * offset_y
            obj.x = new_center_x - obj.scaled_width / 2.0
            obj.y = new_center_y - obj.scaled_height / 2.0
            obj.rotation = (obj.rotation + delta) % 360.0
            actions.append(
                RotateAnnotationAction(
                    object_id=self._stable_id_for(obj),
                    from_x=old_x,
                    from_y=old_y,
                    from_rotation=old_rotation,
                    to_x=obj.x,
                    to_y=obj.y,
                    to_rotation=obj.rotation,
                )
            )

        self._record_composite_action(actions)
        self._invalidate_display()

    # v1.2.32: Adjust annotation properties (line width, font size) with keyboard,
    # stepping through a fixed list of "usual" sizes instead of a small increment.
    def _adjust_annotation_property(self, selected: list[CanvasObject], direction: str) -> None:
        """Adjust line width for vector annotations or font size for text annotations."""
        actions = []
        for obj in selected:
            if isinstance(obj, VectorAnnotation):
                obj_id = self._stable_id_for(obj)
                if obj.ann_type == AnnotationType.TEXT:
                    # Adjust font size for text
                    old_size = obj._font_size_pt
                    new_size = step_size(old_size, FONT_SIZE_STEPS_PT, direction)
                    obj._font_size_pt = new_size
                    obj.fit_text_box()
                    actions.append(ChangeFontSizeAction(
                        object_id=obj_id,
                        font_size_pt=new_size,
                        from_font_size_pt=old_size,
                    ))
                elif obj.ann_type not in {AnnotationType.TEXT}:
                    # Adjust line width for vector annotations (not TEXT)
                    old_width = obj._line_width_pt
                    new_width = step_size(old_width, LINE_WIDTH_STEPS_PT, direction)
                    obj._line_width_pt = new_width
                    actions.append(ChangeLineWidthAction(
                        object_id=obj_id,
                        line_width_pt=new_width,
                        from_line_width_pt=old_width,
                    ))

        self._record_composite_action(actions)
        self._invalidate_display()

    def delete_selected(self) -> None:
        """Delete all selected annotations. Single undo unit (one Ctrl+Z restores all)."""
        objs = self.current_page_objects()
        selected = self.get_selected_annotations()
        if not selected:
            return

        # Find indices and data for all selected objects before removing
        delete_entries = []
        for obj in selected:
            if obj in objs:
                obj_idx = objs.index(obj)
                obj_data = obj.to_dict()
                delete_entries.append((obj_idx, obj, obj_data))

        # Sort by index ascending, but remove from highest index to lowest so
        # earlier (lower) indices in this batch stay valid during the loop.
        delete_entries.sort(key=lambda entry: entry[0])

        sub_actions = []
        for obj_idx, obj, obj_data in reversed(delete_entries):
            obj_id = self._stable_id_for(obj)
            objs.remove(obj)
            self._object_map.pop(obj_id, None)
            action = DeleteAnnotationAction(object_id=obj_id, object_data=obj_data)
            action._deleted_object = obj
            action._deleted_index = obj_idx
            sub_actions.append(action)

        if sub_actions:
            self.history.record_action(CompositeAction(sub_actions))

        self.clear_selection()

    def duplicate_selected_multi(self) -> None:
        """Duplicate all selected annotations. Single undo unit (one Ctrl+Z removes all)."""
        objs = self.current_page_objects()
        selected = self.get_selected_annotations()
        if not selected:
            return
        
        new_objs = []
        sub_actions = []
        for obj in selected:
            dup = obj.duplicate()
            if self.current_page_image:
                pw, ph = self.current_page_image.size
                dup.clamp_to_page(pw, ph)
            objs.append(dup)
            new_objs.append(dup)

            obj_id = self._register_object(dup)
            annotation_data = dup.to_dict()
            annotation_data["object_id"] = obj_id
            if hasattr(dup, 'ann_type'):
                annotation_data["ann_type"] = dup.ann_type.value
            action = AddAnnotationAction(annotation_data)
            action._added_object = dup
            sub_actions.append(action)

        if sub_actions:
            self.history.record_action(CompositeAction(sub_actions))

        # Select new duplicates
        self._selected_multiple.clear()
        self._selected_multiple.update(new_objs)
        self._selected = new_objs[0] if new_objs else None
        self._invalidate_display()

    def copy_selected(self) -> None:
        """Copy selected annotations to clipboard as JSON.
        
        Also updates the internal cache so that new copy operations properly
        update what gets pasted. The cache persists across multiple pastes,
        preventing intermediate copy operations (like external programs) from
        corrupting the cached positions.
        """
        selected = self.get_selected_annotations()
        if not selected:
            return
        
        data = [obj.to_dict() for obj in selected]
        json_str = json.dumps(data, indent=2)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(json_str)
        
        # Update cache so new copy operations are reflected in pastes
        self._cached_copy_data = data

    def has_pasteable_data(self) -> bool:
        """Return True if there is annotation data available to paste (cached copy or clipboard)."""
        if self._cached_copy_data:
            return True
        text = QApplication.clipboard().text()
        if not text:
            return False
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return False
        return isinstance(data, (list, dict))

    def cut_selected(self) -> None:
        """Cut selected annotations (copy to clipboard, then delete)."""
        self.copy_selected()
        self.delete_selected()

    def paste_selected(self) -> None:
        """Paste annotations from clipboard onto current page.

        The duplicate offset is applied when pasting on the same page to avoid exact overlap.
        No offset is applied when pasting to a different page (already distinct location).
        """
        data = self._get_paste_data()
        if data is None:
            return

        # Use setdefault to ensure page list exists in _page_objects
        objs = self._page_objects.setdefault(self._current_page, [])
        pasted_objs = []
        skipped = 0
        for item in data:
            obj = self._paste_object(item, objs)
            if obj is None:
                skipped += 1
            else:
                pasted_objs.append(obj)

        # Select pasted annotations
        self._selected_multiple.clear()
        self._selected_multiple.update(pasted_objs)
        self._selected = pasted_objs[0] if pasted_objs else None
        self.objectChanged.emit()

        # Record paste action for undo support
        pasted_data = []
        for obj in pasted_objs:
            obj_data = obj.to_dict()
            obj_data["object_id"] = self._stable_id_for(obj)
            pasted_data.append(obj_data)
        if pasted_data:
            action = PasteAnnotationAction(pasted_objects_data=pasted_data)
            action._pasted_objects = pasted_objs
            self.history.record_action(action)

        if skipped:
            self.pasteIncomplete.emit(skipped, len(data))

        self.update()

    def _get_paste_data(self) -> list[dict] | None:
        """Return the annotation dicts to paste: the cached copy if present, else parsed clipboard JSON.

        Cache is set on the FIRST paste (when reading from clipboard) and then
        persists for all subsequent pastes, even if the clipboard is updated by
        intermediate copy operations. This ensures copy->paste->paste sequences
        always use the position from the original copy.
        """
        if self._cached_copy_data is not None:
            return self._cached_copy_data

        json_str = QApplication.clipboard().text()
        if not json_str:
            return None
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Clipboard doesn't contain valid annotation JSON; ignore
            return None
        if not isinstance(data, list):
            data = [data]
        # Cache this data for all future pastes until a new copy-paste cycle
        self._cached_copy_data = data
        return data

    def _paste_object(self, item: dict, objs: list[CanvasObject]) -> CanvasObject | None:
        """Deserialize one clipboard item, place it on the current page, and append it to objs.

        Applies the duplicate offset only when pasting onto the same page the
        item was copied from (a different page is already a distinct location).
        Returns None (without appending) if the item is invalid or unrecognized;
        `paste_selected` counts those and reports them via `pasteIncomplete`.
        """
        try:
            original_page = item.get("page")
            obj = canvas_object_from_dict(item)
            if obj is None:
                return None

            obj.page = self._current_page  # Ensure pasted on current page

            if original_page == self._current_page:
                obj.x += DUPLICATE_OFFSET
                obj.y += DUPLICATE_OFFSET

            if self.current_page_image:
                pw, ph = self.current_page_image.size
                obj.clamp_to_page(pw, ph)

            self._register_object(obj)
            objs.append(obj)
            return obj
        except (KeyError, ValueError, TypeError) as exc:
            # Caller counts these and emits pasteIncomplete so the user is told.
            logger.warning("Skipping unreadable annotation in pasted data: %s", exc)
            return None

    def set_color_selected(self, color: QColor) -> None:
        """Set color for all selected annotations."""
        selected = self.get_selected_annotations()
        if not selected:
            return

        actions = []
        for obj in selected:
            obj_id = self._stable_id_for(obj)
            from_color = obj.color.name()
            actions.append(ChangeColorAction(
                object_id=obj_id,
                color=color.name(),
                from_color=from_color,
            ))
            obj.color = color

        self._record_composite_action(actions)
        self._invalidate_display()

    def set_line_width_selected(self, width_pt: float) -> None:
        """Set line width in points for selected vector annotations."""

        selected = [
            obj for obj in self.get_selected_annotations()
            if isinstance(obj, VectorAnnotation) and obj.ann_type != AnnotationType.TEXT
        ]
        if not selected:
            return
        actions = []
        for obj in selected:
            old_width = obj._line_width_pt
            obj._line_width_pt = width_pt
            actions.append(ChangeLineWidthAction(
                object_id=self._stable_id_for(obj),
                line_width_pt=width_pt,
                from_line_width_pt=old_width,
            ))
        self._record_composite_action(actions)
        self._invalidate_display()

    def set_font_size_selected(self, font_size_pt: int) -> None:
        """Set font size for all selected text annotations as one undo unit."""
        selected = [
            obj for obj in self.get_selected_annotations()
            if isinstance(obj, VectorAnnotation) and obj.ann_type == AnnotationType.TEXT
        ]
        if not selected:
            return
        actions = []
        for obj in selected:
            old_size = obj._font_size_pt
            obj._font_size_pt = font_size_pt
            obj.fit_text_box()
            actions.append(ChangeFontSizeAction(
                object_id=self._stable_id_for(obj),
                font_size_pt=font_size_pt,
                from_font_size_pt=old_size,
            ))
        self._record_composite_action(actions)
        self._invalidate_display()

    def set_font_family_selected(self, family: str) -> None:
        """Set font family for all selected text annotations as one undo unit."""
        selected = [
            obj for obj in self.get_selected_annotations()
            if isinstance(obj, VectorAnnotation) and obj.ann_type == AnnotationType.TEXT
        ]
        if not selected:
            return
        actions = []
        for obj in selected:
            old_family = obj._font_family
            obj._font_family = family
            obj.fit_text_box()
            actions.append(ChangeFontFamilyAction(
                object_id=self._stable_id_for(obj),
                font_family=family,
                from_font_family=old_family,
            ))
        self._record_composite_action(actions)
        self._invalidate_display()

    # ---------------------------------------------------------------- coordinate helpers

    def _transform_doc_coords_by_rotation(self, x: float, y: float, rotation: int, page_width: float, page_height: float) -> tuple[float, float]:
        """Transform document coordinates based on page rotation.
        
        Maps original page coordinates to rotated page coordinates so annotation
        centers remain visually in the same location after rotation.
        """
        if rotation == 0:
            return x, y
        elif rotation == 90:
            # 90° CCW: new page dimensions are height × width
            # (x, y) on W×H → (y, W - x) on H×W
            return y, page_width - x
        elif rotation == 180:
            return page_width - x, page_height - y
        elif rotation == 270:
            # 270° CCW: new page dimensions are height × width
            # (x, y) on W×H → (H - y, x) on H×W
            return page_height - y, x
        else:
            return x, y
    
    def _transform_doc_coords_inverse(self, x: float, y: float, rotation: int, page_width: float, page_height: float) -> tuple[float, float]:
        """Inverse transformation: convert rotated coordinates back to original.
        
        Maps from rotated page coordinate system back to original page coordinates.
        """
        if rotation == 0:
            return x, y
        elif rotation == 90:
            # Inverse of (x, y) -> (y, W - x)
            # x' = y, y' = W - x => y = x', x = W - y'
            return page_width - y, x
        elif rotation == 180:
            return page_width - x, page_height - y
        elif rotation == 270:
            # Inverse of (x, y) -> (H - y, x)
            # x' = H - y, y' = x => y = H - x', x = y'
            return y, page_height - x
        else:
            return x, y

    def _object_center_doc(self, obj: CanvasObject) -> QPointF:
        """Return obj's center point in unrotated document coordinates."""
        return QPointF(obj.x + obj.scaled_width / 2.0, obj.y + obj.scaled_height / 2.0)

    def _rotated_top_left_for_object(
        self, obj: CanvasObject, rotation: int, page_width: float, page_height: float
    ) -> tuple[float, float]:
        """Return obj's top-left (x, y) transformed for a page rotation, keeping its
        visual center in the same place. Shared by the export coordinate transform
        (`page_objects_with_rotation_at`) and the live viewport rect (`_object_view_rect`).
        """
        center = self._object_center_doc(obj)
        new_center_x, new_center_y = self._transform_doc_coords_by_rotation(
            center.x(), center.y(), rotation, page_width, page_height
        )
        return new_center_x - obj.scaled_width / 2.0, new_center_y - obj.scaled_height / 2.0

    def _object_view_rect(self, obj: CanvasObject) -> QRectF:
        # Get original page dimensions
        orig_width, orig_height = self._pages[self._current_page].size
        rotation = self._page_rotations.get(self._current_page, 0)
        
        # Transform the object's top-left based on page rotation so its center
        # remains at the same visual location on the page.
        transformed_x, transformed_y = self._rotated_top_left_for_object(
            obj, rotation, orig_width, orig_height
        )
        
        return QRectF(
            self._doc_offset_x + transformed_x * self._fit_scale,
            self._doc_offset_y + transformed_y * self._fit_scale,
            obj.scaled_width * self._fit_scale,
            obj.scaled_height * self._fit_scale,
        )

    def _display_rotation(self, obj: CanvasObject) -> float:
        return (obj.rotation - self._page_rotations.get(self._current_page, 0)) % 360.0

    def _doc_point_to_view(self, point: QPointF) -> QPointF:
        orig_width, orig_height = self._pages[self._current_page].size
        rotation = self._page_rotations.get(self._current_page, 0)
        x, y = self._transform_doc_coords_by_rotation(
            point.x(), point.y(), rotation, orig_width, orig_height
        )
        return QPointF(
            self._doc_offset_x + x * self._fit_scale,
            self._doc_offset_y + y * self._fit_scale,
        )

    def _object_contains_view_point(self, obj: CanvasObject, pt: QPointF) -> bool:
        rect = self._object_view_rect(obj)
        return obj.contains_viewport_point(
            rect.x(), rect.y(), rect.width(), rect.height(), pt, self._display_rotation(obj)
        )

    def _selection_view_bounds(self) -> QRectF | None:
        points = []
        for obj in self.get_selected_annotations():
            rect = self._object_view_rect(obj)
            points.extend(obj.boundary_points_viewport(
                rect.x(), rect.y(), rect.width(), rect.height(), self._display_rotation(obj)
            ))
        if not points:
            return None
        left = min(point.x() for point in points)
        right = max(point.x() for point in points)
        top = min(point.y() for point in points)
        bottom = max(point.y() for point in points)
        return QRectF(left, top, right - left, bottom - top)

    @staticmethod
    def _selection_doc_bounds(selected: list[CanvasObject]) -> QRectF:
        points = []
        for obj in selected:
            points.extend(obj.boundary_points_viewport(
                obj.x,
                obj.y,
                obj.scaled_width,
                obj.scaled_height,
                obj.rotation,
            ))
        left = min(point.x() for point in points)
        right = max(point.x() for point in points)
        top = min(point.y() for point in points)
        bottom = max(point.y() for point in points)
        return QRectF(left, top, right - left, bottom - top)

    def _view_to_doc(self, pt: QPointF) -> QPointF:
        # Convert view coordinates to document coordinates
        doc_x = (pt.x() - self._doc_offset_x) / self._fit_scale
        doc_y = (pt.y() - self._doc_offset_y) / self._fit_scale
        
        # Apply inverse rotation transformation to get original page coordinates
        orig_width, orig_height = self._pages[self._current_page].size
        rotation = self._page_rotations.get(self._current_page, 0)
        doc_x, doc_y = self._transform_doc_coords_inverse(
            doc_x, doc_y, rotation, orig_width, orig_height
        )
        
        return QPointF(doc_x, doc_y)

    def _hit_test_object_at_point(self, pt: QPointF) -> CanvasObject | None:
        """Return the nearest annotation whose bounding box contains the point."""
        candidates = [
            obj
            for obj in reversed(self.current_page_objects())
            if self._object_contains_view_point(obj, pt)
        ]
        if len(candidates) == 1:
            return candidates[0]

        best_obj: CanvasObject | None = None
        best_distance: float | None = None

        for obj in candidates:
            r = self._object_view_rect(obj)
            distance = obj.distance_to_visible_pixel(
                r.x(), r.y(), r.width(), r.height(), pt, self._display_rotation(obj)
            )
            if best_distance is None or distance < best_distance - 1e-9:
                best_distance = distance
                best_obj = obj

        return best_obj

    def _recompute_fit(self) -> None:
        if not self._pages:
            self._fit_scale = 1.0
            self._doc_offset_x = 0.0
            self._doc_offset_y = 0.0
            return
        # Use rotated dimensions if rotation is applied
        dw, dh = self._pages[self._current_page].size
        rotation = self._page_rotations.get(self._current_page, 0)
        if rotation in (90, 270):
            dw, dh = dh, dw  # Swap dimensions for 90/270 degree rotations
        vw, vh = max(1, self.width()), max(1, self.height())
        self._fit_scale = min(vw / dw, vh / dh)
        self._doc_offset_x = (vw - dw * self._fit_scale) / 2
        self._doc_offset_y = (vh - dh * self._fit_scale) / 2

    def default_position_for(self, obj: CanvasObject) -> tuple[float, float]:
        """Default for annotations: center of current page."""
        if not self._pages:
            return 0.0, 0.0
        pw, ph = self._pages[self._current_page].size
        x = max(0.0, (pw - obj.scaled_width) / 2)
        y = max(0.0, (ph - obj.scaled_height) / 2)
        return x, y

    def default_signature_position_for(self, obj: CanvasObject) -> tuple[float, float]:
        if not self._pages:
            return 0.0, 0.0
        pw, ph = self._pages[self._current_page].size
        x = max(0.0, (pw - obj.scaled_width) / 2)
        y = max(0.0, 0.8 * ph - obj.scaled_height / 2)
        return x, y

    # ---------------------------------------------------------------- paint

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._recompute_fit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2f2f2f"))

        if not self._pages:
            return

        pm = self._page_pixmaps[self._current_page]
        # Use rotated dimensions if rotation is applied
        dw, dh = self._pages[self._current_page].size
        rotation = self._page_rotations.get(self._current_page, 0)
        if rotation in (90, 270):
            dw, dh = dh, dw  # Swap dimensions for 90/270 degree rotations
        target = QRectF(
            self._doc_offset_x, self._doc_offset_y,
            dw * self._fit_scale, dh * self._fit_scale,
        )
        painter.drawPixmap(target, pm, QRectF(pm.rect()))

        for obj in self.current_page_objects():
            r = self._object_view_rect(obj)
            display_rotation = self._display_rotation(obj)
            center = r.center()
            painter.save()
            painter.translate(center)
            painter.rotate(display_rotation)
            painter.translate(-center)
            obj.draw_in_viewport(painter, r.x(), r.y(), r.width(), r.height(), self._fit_scale)
            painter.restore()

            # Draw selection boundary for single or multi-selected objects
            is_selected = obj is self._selected or obj in self._selected_multiple
            if is_selected:
                painter.save()
                painter.setPen(QColor("#00a2ff"))
                painter.setBrush(Qt.NoBrush)
                if obj is self._selected and obj.supports_endpoint_handles():
                    pts = obj.endpoint_points_viewport(
                        r.x(), r.y(), r.width(), r.height(), display_rotation
                    )
                    if len(pts) == 2:
                        painter.drawLine(pts[0], pts[1])
                else:
                    painter.drawPolygon(QPolygonF(obj.boundary_points_viewport(
                        r.x(), r.y(), r.width(), r.height(), display_rotation
                    )))
                # Only draw resize handles for primary selected object
                if obj is self._selected and not self.is_multi_selected():
                    for hr in obj.handle_rects_viewport(
                        r.x(), r.y(), r.width(), r.height(), display_rotation
                    ):
                        painter.fillRect(hr, QColor("#00a2ff"))
                        painter.drawRect(hr)
                    handle_center = obj.rotation_handle_center_viewport(
                        r.x(), r.y(), r.width(), r.height(), display_rotation
                    )
                    top_center = obj._rotate_point(
                        QPointF(r.center().x(), r.top()), r.center(), display_rotation
                    )
                    painter.drawLine(top_center, handle_center)
                    painter.drawEllipse(obj.rotation_handle_rect_viewport(
                        r.x(), r.y(), r.width(), r.height(), display_rotation
                    ))
                painter.restore()

        if self.is_multi_selected():
            bounds = self._selection_view_bounds()
            if bounds is not None:
                painter.save()
                painter.setPen(QColor("#00a2ff"))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(bounds)
                handle_center = QPointF(bounds.center().x(), bounds.top() - GROUP_ROTATION_HANDLE_OFFSET)
                painter.drawLine(QPointF(bounds.center().x(), bounds.top()), handle_center)
                painter.drawEllipse(QRectF(
                    handle_center.x() - GROUP_ROTATION_HANDLE_RADIUS,
                    handle_center.y() - GROUP_ROTATION_HANDLE_RADIUS,
                    GROUP_ROTATION_HANDLE_RADIUS * 2.0,
                    GROUP_ROTATION_HANDLE_RADIUS * 2.0,
                ))
                painter.restore()

    # ---------------------------------------------------------------- mouse

    @staticmethod
    def _is_shift_pressed(event) -> bool:
        return bool(event.modifiers() & Qt.ShiftModifier)

    @staticmethod
    def _is_any_modifier_pressed(event) -> bool:
        return bool(event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier))

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or not self._pages:
            return
        # A press begins a new gesture: nothing recorded from here on should merge
        # into whatever the previous gesture (drag or keyboard nudge run) recorded.
        self.history.end_coalescing()
        # Re-assert activation/focus: some launch methods (e.g. an IDE debugger) can leave the window inactive between clicks.
        window = self.window()
        if window is not None:
            window.activateWindow()
        self.setFocus()
        pt = event.position()
        objects = self.current_page_objects()

        if self._selected is not None:
            rotation_handle = self._rotation_handle_rect_for_selection()
            if rotation_handle is not None and rotation_handle.contains(pt):
                self._start_rotation_drag(pt)
                return
            r = self._object_view_rect(self._selected)
            h_idx = self._selected.hit_test_handle(
                r.x(), r.y(), r.width(), r.height(), pt, self._display_rotation(self._selected)
            )
            if h_idx >= 0:
                self._start_handle_drag(h_idx, pt)
                return

        clicked_obj = self._hit_test_object_at_point(pt)
        if clicked_obj is not None:
            # Check for Shift+click (multi-select)
            if self._is_shift_pressed(event):
                self.select_annotation(clicked_obj, multi=True)
            else:
                # Regular click (single select)
                self.select_annotation(clicked_obj, multi=False)

            # Start dragging the clicked object
            self._dragging = True
            self._drag_handle = -1
            doc_pt = self._view_to_doc(pt)
            self._drag_doc_offset_x = doc_pt.x() - clicked_obj.x
            self._drag_doc_offset_y = doc_pt.y() - clicked_obj.y

            # Capture initial position for action recording
            self._drag_start_x = clicked_obj.x
            self._drag_start_y = clicked_obj.y
            self._action_recorded_this_drag = False
            return

        # Clicked on empty space
        if self._is_shift_pressed(event):
            # Shift+click on empty doesn't clear (no change)
            pass
        else:
            # Regular click on empty clears selection
            self.clear_selection()

    def _rotation_handle_rect_for_selection(self) -> QRectF | None:
        if self._selected is None:
            return None
        if self.is_multi_selected():
            bounds = self._selection_view_bounds()
            if bounds is None:
                return None
            center = QPointF(bounds.center().x(), bounds.top() - GROUP_ROTATION_HANDLE_OFFSET)
            return QRectF(
                center.x() - GROUP_ROTATION_HANDLE_RADIUS,
                center.y() - GROUP_ROTATION_HANDLE_RADIUS,
                GROUP_ROTATION_HANDLE_RADIUS * 2.0,
                GROUP_ROTATION_HANDLE_RADIUS * 2.0,
            )
        rect = self._object_view_rect(self._selected)
        return self._selected.rotation_handle_rect_viewport(
            rect.x(), rect.y(), rect.width(), rect.height(), self._display_rotation(self._selected)
        )

    def _start_rotation_drag(self, pt: QPointF) -> None:
        selected = self.get_selected_annotations()
        if not selected or self._selected is None:
            return
        self._rotation_pivot_doc = self._selection_doc_bounds(selected).center()
        self._rotation_pivot_view = self._doc_point_to_view(self._rotation_pivot_doc)
        self._rotation_start_pointer_angle = math.degrees(math.atan2(
            pt.y() - self._rotation_pivot_view.y(),
            pt.x() - self._rotation_pivot_view.x(),
        ))
        self._rotation_start_primary_angle = self._selected.rotation
        self._rotation_drag_states = [
            (obj, obj.x, obj.y, obj.rotation) for obj in selected
        ]
        self._dragging = True
        self._rotating = True
        self._drag_handle = -1

    def _apply_rotation_drag(self, pt: QPointF, shift_pressed: bool) -> None:
        """Rotate every object in `_rotation_drag_states` by the same delta around
        the shared pivot (`_rotation_pivot_doc`, the group/selection center).

        The pointer's angle relative to the pivot is compared against its angle
        at drag start (`_rotation_start_pointer_angle`) to get a raw rotation
        delta for the primary object; that delta (after snapping via
        `_snap_rotation_angle`) is then applied rigidly to every selected
        object's stored start position/rotation, rotating each object's center
        around the pivot and adding the same delta to its own rotation - this
        is what keeps relative positions/angles fixed within a multi-selection.
        """
        pointer_angle = math.degrees(math.atan2(
            pt.y() - self._rotation_pivot_view.y(),
            pt.x() - self._rotation_pivot_view.x(),
        ))
        raw_target = (
            self._rotation_start_primary_angle
            + pointer_angle
            - self._rotation_start_pointer_angle
        )
        target = self._snap_rotation_angle(raw_target, shift_pressed)
        delta = (target - self._rotation_start_primary_angle + 180.0) % 360.0 - 180.0
        radians = math.radians(delta)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        for obj, start_x, start_y, start_rotation in self._rotation_drag_states:
            center_x = start_x + obj.scaled_width / 2.0
            center_y = start_y + obj.scaled_height / 2.0
            offset_x = center_x - self._rotation_pivot_doc.x()
            offset_y = center_y - self._rotation_pivot_doc.y()
            new_center_x = self._rotation_pivot_doc.x() + cos_a * offset_x - sin_a * offset_y
            new_center_y = self._rotation_pivot_doc.y() + sin_a * offset_x + cos_a * offset_y
            obj.x = new_center_x - obj.scaled_width / 2.0
            obj.y = new_center_y - obj.scaled_height / 2.0
            obj.rotation = (start_rotation + delta) % 360.0

    def _start_handle_drag(self, h_idx: int, pt: QPointF) -> None:
        """Begin a resize/endpoint drag, recording the anchor point the drag is measured from.

        For endpoint handles (line/arrow tip/tail, h_idx 0/1), the anchor is
        simply the *other* endpoint in document coordinates - see the
        `_drag_endpoint_handles` branch of `mouseMoveEvent`.

        For regular resize handles, the anchor is the *opposite* handle's point,
        expressed both as a fixed fractional position (`_hdrag_anchor_fx/fy`,
        one of `HANDLE_FX`/`HANDLE_FY`) and as a document-space point rotated
        by the object's current rotation (`_hdrag_anchor_doc`). During the
        drag, `mouseMoveEvent` measures the new pointer position relative to
        this anchor (in the object's unrotated local space) to get a signed
        width/height extent: a negative extent means the pointer crossed past
        the anchor, so the box's anchor side flips and resizing continues from
        there. `_hdrag_start_w/h` record the pre-drag size, used both to
        preserve aspect ratio for non-freely-resizable types and to detect
        that flip.
        """
        obj = self._selected
        assert obj is not None

        if obj.supports_endpoint_handles() and h_idx in (0, 1):
            endpoints = obj.endpoint_points_doc()
            if len(endpoints) == 2:
                self._hdrag_anchor_doc = endpoints[1 - h_idx]
                self._hdrag_anchor_fx = 0.0
                self._hdrag_anchor_fy = 0.0
                self._hdrag_start_w = obj.scaled_width
                self._hdrag_start_h = obj.scaled_height
                self._dragging = True
                self._drag_handle = h_idx
                self._drag_endpoint_handles = True
                self._drag_start_w = obj.scaled_width
                self._drag_start_h = obj.scaled_height
                self._action_recorded_this_drag = False
                return

        anchor_h = ANCHOR_HANDLE[h_idx]
        self._hdrag_start_center_doc = QPointF(
            obj.x + obj.scaled_width / 2.0,
            obj.y + obj.scaled_height / 2.0,
        )
        local_anchor = QPointF(
            obj.x + HANDLE_FX[anchor_h] * obj.scaled_width,
            obj.y + HANDLE_FY[anchor_h] * obj.scaled_height,
        )
        self._hdrag_rotation = obj.rotation
        self._hdrag_anchor_doc = obj._rotate_point(
            local_anchor, self._hdrag_start_center_doc, self._hdrag_rotation
        )
        self._hdrag_anchor_fx = HANDLE_FX[anchor_h]
        self._hdrag_anchor_fy = HANDLE_FY[anchor_h]
        self._hdrag_start_w = obj.scaled_width
        self._hdrag_start_h = obj.scaled_height
        self._dragging = True
        self._drag_handle = h_idx
        self._drag_endpoint_handles = False
        
        # Capture initial size for resize action recording
        self._drag_start_w = obj.scaled_width
        self._drag_start_h = obj.scaled_height
        self._action_recorded_this_drag = False

    @staticmethod
    def _nearest_angle_step(angle_deg: float, step_deg: float) -> float:
        """Return the nearest multiple of step_deg to angle_deg, normalized to [0, 360)."""
        return (round((angle_deg % 360.0) / step_deg) * step_deg) % 360.0

    @staticmethod
    def _snap_rect_ellipse_size(new_w: float, new_h: float, handle: int, modifier_pressed: bool) -> tuple[float, float, bool]:
        """Apply square/circle snapping for rectangle/ellipse resizing.

        Snap is active when aspect ratio is within +/-20% of square
        (0.8..1.2 inclusive), unless any modifier key is pressed.
        """
        if modifier_pressed:
            return new_w, new_h, False

        ratio = new_w / new_h if new_h > 0 else 999.0
        near_square = 0.8 <= ratio <= 1.2
        if not near_square:
            return new_w, new_h, False

        if handle in (3, 4):
            # Left/right edge drag: keep height, snap width to height.
            return new_h, new_h, True
        if handle in (1, 6):
            # Top/bottom edge drag: keep width, snap height to width.
            return new_w, new_w, True

        # Corner drag: smooth snap near threshold.
        size = (new_w + new_h) / 2.0
        return size, size, True

    # Cardinal/intercardinal directions line/arrow endpoints snap to (§_snap_line_angle).
    _LINE_SNAP_ANGLES_DEG: tuple[float, ...] = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)
    _LINE_SNAP_TOLERANCE_DEG: float = 10.0

    @classmethod
    def _snap_line_angle(cls, angle_deg: float, modifier_pressed: bool) -> float:
        """Snap line/arrow angle to a cardinal/intercardinal direction if close enough.

        Snap is active when angle is within `_LINE_SNAP_TOLERANCE_DEG` of one of
        `_LINE_SNAP_ANGLES_DEG`, unless a modifier key (Shift/Ctrl/Alt) is pressed.

        Note: unlike `_snap_rotation_angle` (rotation handle drag, which always
        snaps to the nearest 15/1-degree step), this only snaps near a target and
        otherwise returns the angle unchanged — the two aren't merged into one
        function because their modifier-key behavior differs.
        """
        if modifier_pressed:
            return angle_deg

        normalized = angle_deg % 360.0
        for target in cls._LINE_SNAP_ANGLES_DEG:
            diff = abs(normalized - target)
            diff = min(diff, 360.0 - diff)
            if diff <= cls._LINE_SNAP_TOLERANCE_DEG:
                return target
        return angle_deg

    def mouseMoveEvent(self, event) -> None:
        pt = event.position()

        if self._dragging and self._selected is not None:
            if self._rotating:
                self._apply_rotation_drag(pt, self._is_shift_pressed(event))
            elif self._drag_handle == -1:
                self._handle_move_drag(pt)
            else:
                self._handle_resize_drag(pt, event)

            is_endpoint_drag = self._drag_endpoint_handles and self._selected.supports_endpoint_handles()
            if (
                not self._rotating
                and self.current_page_image
                and not self._selected.supports_free_resize()
                and not is_endpoint_drag
            ):
                pw, ph = self.current_page_image.size
                self._selected.clamp_to_page(pw, ph)
            self._invalidate_display()
            return

        self._update_hover_cursor(pt)

    def _record_drag_action(self, action_cls, initial_kwargs: dict, update_kwargs: dict) -> None:
        """Record a drag step: the first one carries the initial state, later ones
        are partial-format updates that `HistoryStack` merges into it.
        """
        obj_id = self._stable_id_for(self._selected)
        if not self._action_recorded_this_drag:
            self.history.record_action(action_cls(object_id=obj_id, **initial_kwargs))
            self._action_recorded_this_drag = True
        else:
            self.history.record_action(action_cls(object_id=obj_id, **update_kwargs))

    def _handle_move_drag(self, pt: QPointF) -> None:
        """Move the selected object to follow the pointer, recording a coalescing MoveAnnotationAction."""
        doc_pt = self._view_to_doc(pt)
        self._selected.x = doc_pt.x() - self._drag_doc_offset_x
        self._selected.y = doc_pt.y() - self._drag_doc_offset_y

        self._record_drag_action(
            MoveAnnotationAction,
            {
                "from_x": self._drag_start_x,
                "from_y": self._drag_start_y,
                "to_x": self._selected.x,
                "to_y": self._selected.y,
            },
            {"x": self._selected.x, "y": self._selected.y},
        )

    def _handle_resize_drag(self, pt: QPointF, event) -> None:
        """Resize/reshape the selected object per the active handle drag, then record
        a coalescing ResizeAnnotationAction (shared by both endpoint and corner/edge drags)."""
        doc_pt = self._view_to_doc(pt)

        if self._drag_endpoint_handles and self._selected.supports_endpoint_handles():
            self._apply_endpoint_drag(doc_pt, event)
        else:
            self._apply_corner_edge_resize_drag(doc_pt, event)

        self._record_drag_action(
            ResizeAnnotationAction,
            {
                "from_width": self._drag_start_w,
                "from_height": self._drag_start_h,
                "to_width": self._selected.scaled_width,
                "to_height": self._selected.scaled_height,
            },
            {"width": self._selected.scaled_width, "height": self._selected.scaled_height},
        )

    def _apply_endpoint_drag(self, doc_pt: QPointF, event) -> None:
        """Resize a line/arrow by dragging one endpoint, keeping the other endpoint fixed at its anchor."""
        anchor = self._hdrag_anchor_doc
        if self._drag_handle == 0:
            tail = doc_pt
            tip = anchor
        else:
            tail = anchor
            tip = doc_pt

        dx = tip.x() - tail.x()
        dy = tip.y() - tail.y()
        visual_len = max(8.0, math.hypot(dx, dy))

        if getattr(self._selected, 'ann_type', None).value == 'arrow':
            # Arrow tip/tail distance is 0.66 * bbox side in drawing code.
            side = visual_len / 0.66
        else:
            side = visual_len
        side = max(8.0, side)

        cx = (tail.x() + tip.x()) / 2.0
        cy = (tail.y() + tip.y()) / 2.0
        self._selected.set_scaled_size(side, side)
        self._selected.x = cx - self._selected.scaled_width / 2.0
        self._selected.y = cy - self._selected.scaled_height / 2.0

        if hasattr(self._selected, '_angle'):
            ann_type_val = getattr(getattr(self._selected, 'ann_type', None), 'value', None)
            if ann_type_val == 'line':
                raw_angle = math.degrees(math.atan2(dy, dx))
                # v1.2.23: Apply smart angle snapping to 8 cardinal/intercardinal directions
                modifier_pressed = self._is_any_modifier_pressed(event)
                effective_angle = self._snap_line_angle(raw_angle, modifier_pressed)
                self._selected._angle = effective_angle - self._selected.rotation
            elif ann_type_val == 'arrow':
                raw_angle = math.degrees(math.atan2(-dy, dx))
                # v1.2.23: Apply smart angle snapping to 8 cardinal/intercardinal directions
                modifier_pressed = self._is_any_modifier_pressed(event)
                effective_angle = self._snap_line_angle(raw_angle, modifier_pressed)
                self._selected._angle = effective_angle + self._selected.rotation
            else:
                self._selected._angle = math.degrees(math.atan2(-dy, dx))

        # Keep the non-dragged endpoint exactly fixed at the anchor.
        # This avoids visible drift caused by floating-point roundoff
        # while repeatedly recomputing size/angle from endpoint vectors.
        pts = self._selected.endpoint_points_doc()
        if len(pts) == 2:
            fixed_idx = 1 if self._drag_handle == 0 else 0
            fixed_pt = pts[fixed_idx]
            self._selected.x += anchor.x() - fixed_pt.x()
            self._selected.y += anchor.y() - fixed_pt.y()

    def _apply_corner_edge_resize_drag(self, doc_pt: QPointF, event) -> None:
        """Resize via a corner/edge handle relative to the fixed opposite anchor.

        See `_start_handle_drag`'s docstring for the anchor/signed-extent model.
        """
        ax = self._hdrag_anchor_doc.x()
        ay = self._hdrag_anchor_doc.y()
        h = self._drag_handle
        fx = HANDLE_FX[h]
        fy = HANDLE_FY[h]
        local_doc_pt = self._selected._rotate_point(
            doc_pt, self._hdrag_anchor_doc, -self._hdrag_rotation
        )

        # Signed extents from the fixed anchor. A negative extent means
        # the handle was dragged past the anchor: the box flips to the
        # other side and the drag keeps resizing from there.
        if fx != self._hdrag_anchor_fx:
            signed_w = (
                local_doc_pt.x() - ax
                if fx > self._hdrag_anchor_fx
                else ax - local_doc_pt.x()
            )
            signed_w /= abs(fx - self._hdrag_anchor_fx)
        else:
            signed_w = self._hdrag_start_w
        if fy != self._hdrag_anchor_fy:
            signed_h = (
                local_doc_pt.y() - ay
                if fy > self._hdrag_anchor_fy
                else ay - local_doc_pt.y()
            )
            signed_h /= abs(fy - self._hdrag_anchor_fy)
        else:
            signed_h = self._hdrag_start_h

        anchor_fx = 1.0 - self._hdrag_anchor_fx if signed_w < 0 else self._hdrag_anchor_fx
        anchor_fy = 1.0 - self._hdrag_anchor_fy if signed_h < 0 else self._hdrag_anchor_fy
        new_w = abs(signed_w)
        new_h = abs(signed_h)

        if self._selected.supports_free_resize():
            new_w = max(8.0, new_w)
            new_h = max(8.0, new_h)
        else:
            sx = new_w / max(1.0, self._hdrag_start_w)
            sy = new_h / max(1.0, self._hdrag_start_h)
            if fx == self._hdrag_anchor_fx:
                factor = sy
            elif fy == self._hdrag_anchor_fy:
                factor = sx
            else:
                factor = max(sx, sy)
            factor = max(0.05, min(10.0, factor))
            new_w = self._hdrag_start_w * factor
            new_h = self._hdrag_start_h * factor

        # Square/circle snap: if ratio is within +/-20%, snap to 1:1.
        # Modifier keys (Shift/Ctrl/Alt) disable snapping.
        ann_type_val = getattr(getattr(self._selected, 'ann_type', None), 'value', None)
        is_rect_ellipse = ann_type_val in ('rectangle', 'ellipse')
        modifier_pressed = self._is_any_modifier_pressed(event)
        if is_rect_ellipse:
            new_w, new_h, _ = self._snap_rect_ellipse_size(new_w, new_h, h, modifier_pressed)

        self._selected.resize_to_bounds(new_w, new_h)
        local_anchor_offset = QPointF(
            (anchor_fx - 0.5) * self._selected.scaled_width,
            (anchor_fy - 0.5) * self._selected.scaled_height,
        )
        rotated_offset = self._selected._rotate_point(
            local_anchor_offset, QPointF(), self._hdrag_rotation
        )
        center_x = ax - rotated_offset.x()
        center_y = ay - rotated_offset.y()
        self._selected.x = center_x - self._selected.scaled_width / 2.0
        self._selected.y = center_y - self._selected.scaled_height / 2.0

    def _update_hover_cursor(self, pt: QPointF) -> None:
        """Set the mouse cursor shape for hovering over handles/objects when not dragging."""
        if self._selected is not None:
            rotation_handle = self._rotation_handle_rect_for_selection()
            if rotation_handle is not None and rotation_handle.contains(pt):
                self.setCursor(Qt.CrossCursor)
                return
            r = self._object_view_rect(self._selected)
            h = self._selected.hit_test_handle(
                r.x(), r.y(), r.width(), r.height(), pt, self._display_rotation(self._selected)
            )
            if h >= 0:
                if self._selected.supports_endpoint_handles():
                    self.setCursor(Qt.CrossCursor)
                    return
                cursor_map = {
                    0: Qt.SizeFDiagCursor, 7: Qt.SizeFDiagCursor,
                    2: Qt.SizeBDiagCursor, 5: Qt.SizeBDiagCursor,
                    1: Qt.SizeVerCursor,   6: Qt.SizeVerCursor,
                    3: Qt.SizeHorCursor,   4: Qt.SizeHorCursor,
                }
                self.setCursor(cursor_map.get(h, Qt.SizeAllCursor))
                return

        hovered_obj = self._hit_test_object_at_point(pt)
        if hovered_obj is not None:
            self.setCursor(Qt.SizeAllCursor)
            return
        self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._rotating:
                actions = []
                for obj, old_x, old_y, old_rotation in self._rotation_drag_states:
                    if (
                        abs(obj.x - old_x) > 1e-9
                        or abs(obj.y - old_y) > 1e-9
                        or abs(obj.rotation - old_rotation) > 1e-9
                    ):
                        actions.append(RotateAnnotationAction(
                            object_id=self._stable_id_for(obj),
                            from_x=old_x,
                            from_y=old_y,
                            from_rotation=old_rotation,
                            to_x=obj.x,
                            to_y=obj.y,
                            to_rotation=obj.rotation,
                        ))
                if actions:
                    self._record_composite_action(actions)
            self._end_drag_gesture()

    def _end_drag_gesture(self) -> None:
        """Finish a drag: close the history coalescing window, then clear drag state.

        Without closing the window, the next drag of the same object would merge
        into this one and a single Ctrl+Z would revert both gestures.
        """
        self.history.end_coalescing()
        self._reset_drag_state()

    def _reset_drag_state(self) -> None:
        """Clear all mouse-drag/rotation bookkeeping after a drag ends."""
        self._dragging = False
        self._rotating = False
        self._rotation_drag_states = []
        self._drag_handle = -1
        self._drag_endpoint_handles = False
        self._action_recorded_this_drag = False

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._selected is not None:
            self.editRequested.emit(self._selected)

    # ---------------------------------------------------------------- keyboard

    def keyPressEvent(self, event) -> None:
        key = event.key()
        modifiers = event.modifiers()
        selected = self.get_selected_annotations()

        if self._handle_navigation_and_selection_keys(key, modifiers, selected):
            return

        is_ctrl_key = bool(modifiers & Qt.ControlModifier)
        is_shift_key = bool(modifiers & Qt.ShiftModifier)

        if is_ctrl_key:
            if self._handle_ctrl_shortcuts(key, is_shift_key, selected):
                return
        else:
            if self._handle_single_key_shortcuts(key, is_shift_key, selected):
                return

        # v1.2.22: Width/font size adjustment with [ and ] keys
        if not is_ctrl_key and not is_shift_key:
            if self._handle_bracket_property_keys(key, selected):
                return

        super().keyPressEvent(event)

    def _handle_navigation_and_selection_keys(
        self, key: int, modifiers, selected: list[CanvasObject]
    ) -> bool:
        """Handle Page Up/Down/Home/End, Escape, Delete, and arrow keys (move
        selection, or page navigation when nothing is selected).

        Returns True if the key was fully handled (caller should stop processing).
        """
        if key == Qt.Key_PageDown:
            self.goto_page(self._current_page + 1)
            return True
        elif key == Qt.Key_PageUp:
            self.goto_page(self._current_page - 1)
            return True
        elif key == Qt.Key_Home:
            self.goto_page(0)
            return True
        elif key == Qt.Key_End:
            self.goto_page(len(self._pages) - 1)
            return True

        if key == Qt.Key_Escape:
            self.clear_selection()
            return True

        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            if selected:
                self.delete_selected()
            return True

        if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if selected:
                # Movement: 12pt normal, 1px with Shift (per V1.2.18)
                increment = KEYBOARD_MOVE_FINE_STEP_PT if modifiers & Qt.ShiftModifier else KEYBOARD_MOVE_STEP_PT

                if key == Qt.Key_Up:
                    self.move_selected(0, -increment)
                elif key == Qt.Key_Down:
                    self.move_selected(0, increment)
                elif key == Qt.Key_Left:
                    self.move_selected(-increment, 0)
                elif key == Qt.Key_Right:
                    self.move_selected(increment, 0)
                return True
            else:
                # Page navigation without annotation selected: left/right arrows
                if key == Qt.Key_Left:
                    self.goto_page(self._current_page - 1)
                    return True
                elif key == Qt.Key_Right:
                    self.goto_page(self._current_page + 1)
                    return True
        return False

    def _invoke_window_command(self, name: str) -> None:
        """Call `name` on the parent window, logging if it isn't available.

        None of these commands are optional; a missing one means the canvas was
        reparented away from MainWindow and the shortcut would otherwise be
        silently dead.
        """
        window = self.parent()
        command = getattr(window, name, None)
        if command is None:
            logger.warning("Cannot run %r: parent window does not provide it", name)
            return
        command()

    def _handle_ctrl_shortcuts(self, key: int, is_shift_key: bool, selected: list[CanvasObject]) -> bool:
        """Handle Ctrl+<key> shortcuts (copy/cut/paste/duplicate/select-all/undo/redo,
        rotation, and document operations). Returns True if the key was handled.
        """
        if key == Qt.Key_C:
            if selected:
                self.copy_selected()
            return True
        elif key == Qt.Key_X:
            if selected:
                self.cut_selected()
            return True
        elif key == Qt.Key_V:
            self.paste_selected()
            return True
        elif key == Qt.Key_D:
            if selected:
                self.duplicate_selected()
            return True
        elif key == Qt.Key_A:
            self.select_all_on_page()
            return True
        elif key == Qt.Key_Z:
            # Ctrl+Z undo, Ctrl+Shift+Z redo (the conventional chord).
            self._invoke_window_command("redo" if is_shift_key else "undo")
            return True
        elif key == Qt.Key_Y:
            self._invoke_window_command("redo")
            return True
        # ================================================================ Rotation with Ctrl
        elif key == Qt.Key_L:
            if is_shift_key:
                # Shift+Ctrl+L: Rotate current page left
                self.rotate_current_page_left()
            else:
                # Ctrl+L: Rotate all pages left
                self.rotate_all_pages_left()
            return True
        elif key == Qt.Key_R:
            if is_shift_key:
                # Shift+Ctrl+R: Rotate current page right
                self.rotate_current_page_right()
            else:
                # Ctrl+R: Rotate all pages right
                self.rotate_all_pages_right()
            return True
        # ================================================================ Document operations (delegate to parent)
        elif key == Qt.Key_O:
            self._invoke_window_command("open_document")
            return True
        elif key == Qt.Key_S:
            self._invoke_window_command("save_document_as")
            return True
        elif key == Qt.Key_P:
            self._invoke_window_command("print_document")
            return True
        return False

    def _handle_single_key_shortcuts(self, key: int, is_shift_key: bool, selected: list[CanvasObject]) -> bool:
        """Handle single-key hotkey variants available with no Ctrl modifier
        (copy/cut/paste/duplicate/select-all/undo/redo/rotation/document ops
        without needing Ctrl). Returns True if the key was handled.
        """
        if key == Qt.Key_Plus:
            # +: Open the toolbar annotation menu
            self._invoke_window_command("show_annotation_menu")
            return True
        elif key == Qt.Key_O:
            self._invoke_window_command("open_document")
            return True
        elif key == Qt.Key_S:
            self._invoke_window_command("save_document_as")
            return True
        elif key == Qt.Key_P:
            self._invoke_window_command("print_document")
            return True
        elif key == Qt.Key_C:
            # C: Copy
            if selected:
                self.copy_selected()
            return True
        elif key == Qt.Key_X:
            # X: Cut
            if selected:
                self.cut_selected()
            return True
        elif key == Qt.Key_V:
            # V: Paste
            self.paste_selected()
            return True
        elif key == Qt.Key_D:
            # D: Duplicate
            if selected:
                self.duplicate_selected()
            return True
        elif key == Qt.Key_A:
            # A: Select all
            self.select_all_on_page()
            return True
        elif key == Qt.Key_Z:
            self._invoke_window_command("redo" if is_shift_key else "undo")
            return True
        elif key == Qt.Key_Y:
            self._invoke_window_command("redo")
            return True
        elif key == Qt.Key_L:
            # L or Shift+L: Rotate
            if is_shift_key:
                # Shift+L: Rotate current page left
                self.rotate_current_page_left()
            else:
                # L: Rotate all pages left
                self.rotate_all_pages_left()
            return True
        elif key == Qt.Key_R:
            # R or Shift+R: Rotate
            if is_shift_key:
                # Shift+R: Rotate current page right
                self.rotate_current_page_right()
            else:
                # R: Rotate all pages right
                self.rotate_all_pages_right()
            return True
        return False

    def _handle_bracket_property_keys(self, key: int, selected: list[CanvasObject]) -> bool:
        """[ / ] decrease/increase line width (vector types) or font size (text)."""
        if key == Qt.Key_BracketLeft:
            if selected:
                self._adjust_annotation_property(selected, 'decrease')
            return True
        elif key == Qt.Key_BracketRight:
            if selected:
                self._adjust_annotation_property(selected, 'increase')
            return True
        return False

    # ---------------------------------------------------------------- Drag and drop events
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag enter for file drops (MIME type: text/uri-list)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent) -> None:
        """Handle file drop - emit signal with file path for parent to handle."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                # Get the first dropped file path
                file_path = urls[0].toLocalFile()
                if file_path:
                    # Emit signal to parent window to handle the file
                    self.fileDrop.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

