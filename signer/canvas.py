from __future__ import annotations

import copy
import json
import math

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from .history import HistoryStack, MoveAnnotationAction, ResizeAnnotationAction
from .objects import (
    ANCHOR_HANDLE,
    HANDLE_FX,
    HANDLE_FY,
    CanvasObject,
    canvas_object_from_dict,
)


class DocumentCanvas(QWidget):
    objectChanged = Signal()        # emitted on move/scale/add/remove
    pageChanged = Signal(int, int)  # (current_page_0indexed, total_pages)
    editRequested = Signal(object)  # CanvasObject — double-click

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # History management
        self.history = HistoryStack()

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

        self._hdrag_anchor_doc: QPointF = QPointF()
        self._hdrag_anchor_fx: float = 0.0
        self._hdrag_anchor_fy: float = 0.0
        self._hdrag_start_w: float = 1.0
        self._hdrag_start_h: float = 1.0

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
        
        For export: returns objects with coordinates already adjusted for the
        rotated page orientation, so their centers stay at the same visual location.
        Annotations themselves are NOT rotated - only their position changes.
        """
        objects = self._page_objects.get(index, [])
        rotation = self._page_rotations.get(index, 0)
        
        if rotation == 0:
            # No rotation, return objects as-is
            return objects
        
        # For rotated pages, create transformed copies
        if index < 0 or index >= len(self._pages):
            return objects
        
        orig_width, orig_height = self._pages[index].size
        transformed = []
        
        for obj in objects:
            # Calculate the center of the annotation
            # (x, y) is the top-left corner, so add half the dimensions to get center
            center_x = obj.x + obj._base_width / 2
            center_y = obj.y + obj._base_height / 2
            
            # Transform the center coordinates so it stays at the same visual location
            new_center_x, new_center_y = self._transform_doc_coords_by_rotation(
                center_x, center_y, rotation, orig_width, orig_height
            )
            
            # Convert back to top-left corner coordinates
            new_x = new_center_x - obj._base_width / 2
            new_y = new_center_y - obj._base_height / 2
            
            # Create a shallow copy of the object with transformed coordinates
            # Annotations keep their original size and are NOT rotated
            import copy
            obj_copy = copy.copy(obj)
            obj_copy.x = new_x
            obj_copy.y = new_y
            transformed.append(obj_copy)
        
        return transformed

    def set_pages(self, pages: list[Image.Image]) -> None:
        self._pages = [p.convert("RGB") for p in pages]
        self._page_pixmaps = [QPixmap.fromImage(ImageQt(p)) for p in self._pages]
        self._current_page = 0
        self._page_objects = {}
        self._object_map = {}  # Clear object map when resetting document
        self._selected = None
        self._selected_multiple.clear()
        self._recompute_fit()
        self.pageChanged.emit(0, len(self._pages))
        self.objectChanged.emit()
        self.update()

    def goto_page(self, page: int) -> None:
        if not self._pages:
            return
        page = max(0, min(page, len(self._pages) - 1))
        if page == self._current_page:
            return
        self._selected = None
        self._selected_multiple.clear()
        self._current_page = page
        self._recompute_fit()
        self.pageChanged.emit(self._current_page, len(self._pages))
        self.objectChanged.emit()
        self.update()

    def _get_rotated_page_image(self, page_index: int) -> Image.Image:
        """Get the PIL image for a page, applying rotation if set."""
        if page_index < 0 or page_index >= len(self._pages):
            return self._pages[0] if self._pages else None
        
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
    
    def rotate_current_page_left(self) -> None:
        """Rotate current page 90 degrees counter-clockwise."""
        self._page_rotations[self._current_page] = (self._page_rotations.get(self._current_page, 0) + 90) % 360
        self._update_rotated_pixmap(self._current_page)
        self._recompute_fit()
        self.objectChanged.emit()
        self.update()
    
    def rotate_current_page_right(self) -> None:
        """Rotate current page 90 degrees clockwise."""
        self._page_rotations[self._current_page] = (self._page_rotations.get(self._current_page, 0) + 270) % 360
        self._update_rotated_pixmap(self._current_page)
        self._recompute_fit()
        self.objectChanged.emit()
        self.update()
    
    def rotate_all_pages_left(self) -> None:
        """Rotate all pages 90 degrees counter-clockwise."""
        for i in range(len(self._pages)):
            self._page_rotations[i] = (self._page_rotations.get(i, 0) + 90) % 360
            self._update_rotated_pixmap(i)
        self._recompute_fit()
        self.objectChanged.emit()
        self.update()
    
    def rotate_all_pages_right(self) -> None:
        """Rotate all pages 90 degrees clockwise."""
        for i in range(len(self._pages)):
            self._page_rotations[i] = (self._page_rotations.get(i, 0) + 270) % 360
            self._update_rotated_pixmap(i)
        self._recompute_fit()
        self.objectChanged.emit()
        self.update()
    
    def _update_rotated_pixmap(self, page_index: int) -> None:
        """Update the pixmap cache for a page after rotation."""
        if page_index < 0 or page_index >= len(self._page_pixmaps):
            return
        rotated_img = self._get_rotated_page_image(page_index)
        self._page_pixmaps[page_index] = QPixmap.fromImage(ImageQt(rotated_img))
    
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

    def add_object(self, obj: CanvasObject) -> None:
        self._page_objects.setdefault(self._current_page, []).append(obj)
        self._selected = obj
        self.objectChanged.emit()
        self.update()

    def remove_selected(self) -> None:
        """Remove selected annotation(s). Works with single or multi-selection."""
        if self.is_multi_selected():
            self.delete_selected()
        elif self._selected is None:
            return
        else:
            # Single selection - original behavior
            objs = self._page_objects.get(self._current_page, [])
            if self._selected in objs:
                objs.remove(self._selected)
            self._selected = None
            self.objectChanged.emit()
            self.update()

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
            if obj in self._selected_multiple:
                # Remove from selection
                self._selected_multiple.discard(obj)
            else:
                # Add to selection
                self._selected_multiple.add(obj)
                # Keep _selected as primary for UI feedback
                if self._selected is None:
                    self._selected = obj
        self.objectChanged.emit()
        self.update()

    def clear_selection(self) -> None:
        """Clear all selections."""
        self._selected = None
        self._selected_multiple.clear()
        self.objectChanged.emit()
        self.update()

    def select_all_on_page(self) -> None:
        """Select all annotations on the current page."""
        objs = self.current_page_objects()
        if not objs:
            return
        self._selected_multiple.clear()
        self._selected_multiple.update(objs)
        if objs:
            self._selected = objs[0]  # Set first as primary
        self.objectChanged.emit()
        self.update()

    def get_selected_annotations(self) -> list[CanvasObject]:
        """Return all selected annotations (sorted for consistency)."""
        if self._selected_multiple:
            return sorted(list(self._selected_multiple), key=lambda o: (o.y, o.x))
        elif self._selected is not None:
            return [self._selected]
        return []

    def is_multi_selected(self) -> bool:
        """Check if multiple annotations are currently selected."""
        return len(self._selected_multiple) > 1

    def move_selected(self, dx: float, dy: float) -> None:
        """Move all selected annotations by (dx, dy) in document space."""
        selected = self.get_selected_annotations()
        if not selected:
            return
        
        objs = self.current_page_objects()
        for obj in selected:
            obj.x += dx
            obj.y += dy
            if self.current_page_image:
                pw, ph = self.current_page_image.size
                obj.clamp_to_page(pw, ph)
        self.objectChanged.emit()

    # v1.2.22: Adjust annotation properties (line width, font size) with keyboard
    def _adjust_annotation_property(self, selected, direction: str) -> None:
        """Adjust line width for vector annotations or font size for text annotations."""
        from .objects import VectorAnnotation, AnnotationType
        from .history import ChangeLineWidthAction, ChangeFontSizeAction
        
        sign = -1 if direction == 'decrease' else 1
        
        objs = self.current_page_objects()
        for obj in selected:
            if isinstance(obj, VectorAnnotation):
                obj_idx = objs.index(obj) if obj in objs else -1
                if obj.ann_type == AnnotationType.TEXT:
                    # Adjust font size for text
                    old_size = obj._font_size_px
                    new_size = max(6, min(72, obj._font_size_px + sign * 1))
                    obj._font_size_px = new_size
                    obj.fit_text_box()
                    # Record to history
                    if obj_idx >= 0:
                        action = ChangeFontSizeAction(
                            object_id=obj_idx,
                            from_size=old_size,
                            to_size=new_size,
                        )
                        self.history.record_action(action)
                elif obj.ann_type not in {AnnotationType.TEXT}:
                    # Adjust line width for vector annotations (not TEXT)
                    old_width = obj._line_width_pt
                    new_width = max(0.5, min(10.0, obj._line_width_pt + sign * 0.5))
                    obj._line_width_pt = new_width
                    # Record to history
                    if obj_idx >= 0:
                        action = ChangeLineWidthAction(
                            object_id=obj_idx,
                            from_width=old_width,
                            to_width=new_width,
                        )
                        self.history.record_action(action)
        
        self.objectChanged.emit()
        self.update()

    def delete_selected(self) -> None:
        """Delete all selected annotations. Single undo unit."""
        objs = self.current_page_objects()
        selected = self.get_selected_annotations()
        if not selected:
            return
        
        # Remove all selected from page
        for obj in selected:
            if obj in objs:
                objs.remove(obj)
        
        self.clear_selection()
        self.objectChanged.emit()

    def duplicate_selected_multi(self) -> None:
        """Duplicate all selected annotations. Single undo unit."""
        objs = self.current_page_objects()
        selected = self.get_selected_annotations()
        if not selected:
            return
        
        new_objs = []
        for obj in selected:
            dup = obj.duplicate()
            dup.x += 10  # Small offset to avoid exact overlap
            dup.y += 10
            if self.current_page_image:
                pw, ph = self.current_page_image.size
                dup.clamp_to_page(pw, ph)
            objs.append(dup)
            new_objs.append(dup)
        
        # Select new duplicates
        self._selected_multiple.clear()
        self._selected_multiple.update(new_objs)
        self._selected = new_objs[0] if new_objs else None
        self.objectChanged.emit()
        self.update()

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

    def cut_selected(self) -> None:
        """Cut selected annotations (copy to clipboard, then delete)."""
        self.copy_selected()
        self.delete_selected()

    def paste_selected(self) -> None:
        """Paste annotations from clipboard onto current page.
        
        Cache is set on the FIRST paste (when reading from clipboard) and then
        persists for all subsequent pastes, even if the clipboard is updated by
        intermediate copy operations. This ensures copy->paste->paste sequences
        always use the position from the original copy.
        
        Offset (~10 pixels) is applied when pasting on the same page to avoid exact overlap.
        No offset is applied when pasting to a different page (already distinct location).
        """
        # If no cache, read from clipboard and cache it
        if self._cached_copy_data is None:
            clipboard = QApplication.clipboard()
            json_str = clipboard.text()
            if not json_str:
                return
            
            try:
                data = json.loads(json_str)
                if not isinstance(data, list):
                    data = [data]
                # Cache this data for all future pastes until a new copy-paste cycle
                self._cached_copy_data = data
            except json.JSONDecodeError:
                # Clipboard doesn't contain valid annotation JSON; ignore
                return
        else:
            # Cache exists, use it
            data = self._cached_copy_data
        
        # Use setdefault to ensure page list exists in _page_objects
        objs = self._page_objects.setdefault(self._current_page, [])
        pasted_objs = []
        
        for item in data:
            try:
                # Use factory function to deserialize based on type
                original_page = item.get("page")
                
                obj = canvas_object_from_dict(item)
                if obj is None:
                    # Unknown type; skip
                    continue
                
                obj.page = self._current_page  # Ensure pasted on current page
                
                # Apply offset only if pasting on same page as original
                if original_page == self._current_page:
                    obj.x += 10  # Offset to avoid exact overlap
                    obj.y += 10
                
                if self.current_page_image:
                    pw, ph = self.current_page_image.size
                    obj.clamp_to_page(pw, ph)
                
                objs.append(obj)
                pasted_objs.append(obj)
            except (KeyError, ValueError, TypeError):
                # Invalid annotation data; skip
                continue
        
        # Select pasted annotations
        self._selected_multiple.clear()
        self._selected_multiple.update(pasted_objs)
        self._selected = pasted_objs[0] if pasted_objs else None
        self.objectChanged.emit()
        self.update()

    def set_color_selected(self, color: QColor) -> None:
        """Set color for all selected annotations."""
        selected = self.get_selected_annotations()
        if not selected:
            return
        for obj in selected:
            obj.color = color
        self.objectChanged.emit()
        self.update()

    def set_line_width_selected(self, width_factor: float) -> None:
        """Set line width factor for vector annotations in selection."""
        from .objects import ARROW_TYPES, AnnotationType
        
        selected = self.get_selected_annotations()
        if not selected:
            return
        for obj in selected:
            # Apply only to vector annotations
            if hasattr(obj, 'annotation_type') and (
                obj.annotation_type in ARROW_TYPES or 
                obj.annotation_type in {AnnotationType.CHECKMARK, AnnotationType.CROSS}
            ):
                if hasattr(obj, 'line_width_factor'):
                    obj.line_width_factor = width_factor
        self.objectChanged.emit()
        self.update()

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

    def _object_view_rect(self, obj: CanvasObject) -> QRectF:
        # Get original page dimensions
        orig_width, orig_height = self._pages[self._current_page].size
        rotation = self._page_rotations.get(self._current_page, 0)
        
        # Calculate the center of the annotation
        # (obj.x, obj.y) is the top-left corner, so add half the dimensions to get center
        center_x = obj.x + obj._base_width / 2
        center_y = obj.y + obj._base_height / 2
        
        # Transform the center coordinates based on page rotation
        # so annotation centers remain at the same visual location on the page
        transformed_center_x, transformed_center_y = self._transform_doc_coords_by_rotation(
            center_x, center_y, rotation, orig_width, orig_height
        )
        
        # Convert back to top-left corner coordinates for QRectF
        transformed_x = transformed_center_x - obj.scaled_width / 2
        transformed_y = transformed_center_y - obj.scaled_height / 2
        
        return QRectF(
            self._doc_offset_x + transformed_x * self._fit_scale,
            self._doc_offset_y + transformed_y * self._fit_scale,
            obj.scaled_width * self._fit_scale,
            obj.scaled_height * self._fit_scale,
        )

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
            obj.draw_in_viewport(painter, r.x(), r.y(), r.width(), r.height(), self._fit_scale)

            # Draw selection boundary for single or multi-selected objects
            is_selected = obj is self._selected or obj in self._selected_multiple
            if is_selected:
                painter.save()
                painter.setPen(QColor("#00a2ff"))
                painter.setBrush(Qt.NoBrush)
                if obj is self._selected and obj.supports_endpoint_handles():
                    pts = obj.endpoint_points_viewport(r.x(), r.y(), r.width(), r.height())
                    if len(pts) == 2:
                        painter.drawLine(pts[0], pts[1])
                else:
                    painter.drawRect(r)
                # Only draw resize handles for primary selected object
                if obj is self._selected:
                    for hr in obj.handle_rects_viewport(r.x(), r.y(), r.width(), r.height()):
                        painter.fillRect(hr, QColor("#00a2ff"))
                        painter.drawRect(hr)
                painter.restore()

    # ---------------------------------------------------------------- mouse

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or not self._pages:
            return
        pt = event.position()
        objects = self.current_page_objects()

        if self._selected is not None:
            r = self._object_view_rect(self._selected)
            h_idx = self._selected.hit_test_handle(r.x(), r.y(), r.width(), r.height(), pt)
            if h_idx >= 0:
                self._start_handle_drag(h_idx, pt)
                return

        for obj in reversed(objects):
            r = self._object_view_rect(obj)
            if r.contains(pt):
                # Check for Shift+click (multi-select)
                if event.modifiers() & Qt.ShiftModifier:
                    self.select_annotation(obj, multi=True)
                else:
                    # Regular click (single select)
                    self.select_annotation(obj, multi=False)
                
                # Start dragging the clicked object
                self._dragging = True
                self._drag_handle = -1
                doc_pt = self._view_to_doc(pt)
                self._drag_doc_offset_x = doc_pt.x() - obj.x
                self._drag_doc_offset_y = doc_pt.y() - obj.y
                
                # Capture initial position for action recording
                self._drag_start_x = obj.x
                self._drag_start_y = obj.y
                self._action_recorded_this_drag = False
                return

        # Clicked on empty space
        if event.modifiers() & Qt.ShiftModifier:
            # Shift+click on empty doesn't clear (no change)
            pass
        else:
            # Regular click on empty clears selection
            self.clear_selection()

    def _start_handle_drag(self, h_idx: int, pt: QPointF) -> None:
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
        ax = obj.x + HANDLE_FX[anchor_h] * obj.scaled_width
        ay = obj.y + HANDLE_FY[anchor_h] * obj.scaled_height
        self._hdrag_anchor_doc = QPointF(ax, ay)
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

    @staticmethod
    def _snap_line_angle(angle_deg: float, modifier_pressed: bool) -> float:
        """Snap line/arrow angle to cardinal or intercardinal direction if close enough.

        Snap is active when angle is within 10° of any of 8 directions:
        0° (E), 45° (NE), 90° (N), 135° (NW), 180° (W), 225° (SW), 270° (S), 315° (SE)
        unless any modifier key is pressed.
        
        Args:
            angle_deg: Angle in degrees (from atan2)
            modifier_pressed: Whether a modifier key (Shift/Ctrl/Alt) is pressed
            
        Returns:
            Snapped angle in degrees
        """
        if modifier_pressed:
            return angle_deg
        
        # Normalize angle to 0-360 range for easier comparison
        normalized = angle_deg % 360.0
        
        # Check if within 10° of the 8 cardinal/intercardinal directions
        # 0° (horizontal right / East)
        if normalized <= 10.0 or normalized >= 350.0:
            return 0.0
        # 45° (diagonal up-right / Northeast)
        if 35.0 <= normalized <= 55.0:
            return 45.0
        # 90° (vertical up / North)
        if 80.0 <= normalized <= 100.0:
            return 90.0
        # 135° (diagonal up-left / Northwest)
        if 125.0 <= normalized <= 145.0:
            return 135.0
        # 180° (horizontal left / West)
        if 170.0 <= normalized <= 190.0:
            return 180.0
        # 225° (diagonal down-left / Southwest)
        if 215.0 <= normalized <= 235.0:
            return 225.0
        # 270° (vertical down / South)
        if 260.0 <= normalized <= 280.0:
            return 270.0
        # 315° (diagonal down-right / Southeast)
        if 305.0 <= normalized <= 325.0:
            return 315.0
        
        return angle_deg

    def mouseMoveEvent(self, event) -> None:
        pt = event.position()

        if self._dragging and self._selected is not None:
            if self._drag_handle == -1:
                # MOVE operation
                doc_pt = self._view_to_doc(pt)
                self._selected.x = doc_pt.x() - self._drag_doc_offset_x
                self._selected.y = doc_pt.y() - self._drag_doc_offset_y
                
                # Record move action with coalescing using stable object ID
                # v1.2.22: Use _object_map for stable ID
                obj_id = id(self._selected) if hasattr(self, '_stable_id_map') else -1
                if obj_id == -1:
                    # Fallback: use array index if object map not available
                    objects = self.current_page_objects()
                    obj_id = objects.index(self._selected) if self._selected in objects else -1
                if obj_id >= 0:
                    if not self._action_recorded_this_drag:
                        # First move: create full-format action with initial state
                        action = MoveAnnotationAction(
                            object_id=obj_id,
                            from_x=self._drag_start_x,
                            from_y=self._drag_start_y,
                            to_x=self._selected.x,
                            to_y=self._selected.y,
                        )
                        self._action_recorded_this_drag = True
                    else:
                        # Subsequent moves: create partial-format action for merging
                        action = MoveAnnotationAction(
                            object_id=obj_id,
                            x=self._selected.x,
                            y=self._selected.y,
                        )
                    self.history.record_action(action)
            else:
                # RESIZE operation
                doc_pt = self._view_to_doc(pt)

                if self._drag_endpoint_handles and self._selected.supports_endpoint_handles():
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
                            modifier_pressed = bool(event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier))
                            self._selected._angle = self._snap_line_angle(raw_angle, modifier_pressed)
                        elif ann_type_val == 'arrow':
                            raw_angle = math.degrees(math.atan2(-dy, dx))
                            # v1.2.23: Apply smart angle snapping to 8 cardinal/intercardinal directions
                            modifier_pressed = bool(event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier))
                            self._selected._angle = self._snap_line_angle(raw_angle, modifier_pressed)
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
                else:
                    ax = self._hdrag_anchor_doc.x()
                    ay = self._hdrag_anchor_doc.y()
                    h = self._drag_handle
                    fx = HANDLE_FX[h]
                    fy = HANDLE_FY[h]

                    if self._selected.supports_free_resize():
                        # Signed extents from the fixed anchor; clamp to keep the
                        # box on the correct side (no inversion past the anchor).
                        if fx != self._hdrag_anchor_fx:
                            new_w = (doc_pt.x() - ax) if fx > self._hdrag_anchor_fx else (ax - doc_pt.x())
                        else:
                            new_w = self._hdrag_start_w
                        if fy != self._hdrag_anchor_fy:
                            new_h = (doc_pt.y() - ay) if fy > self._hdrag_anchor_fy else (ay - doc_pt.y())
                        else:
                            new_h = self._hdrag_start_h
                        new_w = max(8.0, new_w)
                        new_h = max(8.0, new_h)
                    else:
                        if fx != self._hdrag_anchor_fx:
                            new_w = abs(doc_pt.x() - ax) / abs(fx - self._hdrag_anchor_fx)
                        else:
                            new_w = self._hdrag_start_w
                        if fy != self._hdrag_anchor_fy:
                            new_h = abs(doc_pt.y() - ay) / abs(fy - self._hdrag_anchor_fy)
                        else:
                            new_h = self._hdrag_start_h

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
                    modifier_pressed = bool(event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier))
                    if is_rect_ellipse:
                        new_w, new_h, _ = self._snap_rect_ellipse_size(new_w, new_h, h, modifier_pressed)

                    self._selected.set_scaled_size(new_w, new_h)
                    self._selected.x = ax - self._hdrag_anchor_fx * self._selected.scaled_width
                    self._selected.y = ay - self._hdrag_anchor_fy * self._selected.scaled_height
                
                # Record resize action with coalescing using stable object ID
                # v1.2.22: Use object ID for stable reference
                obj_id = id(self._selected) if hasattr(self, '_stable_id_map') else -1
                if obj_id == -1:
                    # Fallback: use array index if object map not available
                    objects = self.current_page_objects()
                    obj_id = objects.index(self._selected) if self._selected in objects else -1
                if obj_id >= 0:
                    if not self._action_recorded_this_drag:
                        # First resize: create full-format action with initial state
                        action = ResizeAnnotationAction(
                            object_id=obj_id,
                            from_width=self._drag_start_w,
                            from_height=self._drag_start_h,
                            to_width=self._selected.scaled_width,
                            to_height=self._selected.scaled_height,
                        )
                        self._action_recorded_this_drag = True
                    else:
                        # Subsequent resizes: create partial-format action for merging
                        action = ResizeAnnotationAction(
                            object_id=obj_id,
                            width=self._selected.scaled_width,
                            height=self._selected.scaled_height,
                        )
                    self.history.record_action(action)

            is_endpoint_drag = self._drag_endpoint_handles and self._selected.supports_endpoint_handles()
            if self.current_page_image and not self._selected.supports_free_resize() and not is_endpoint_drag:
                pw, ph = self.current_page_image.size
                self._selected.clamp_to_page(pw, ph)
            self.objectChanged.emit()
            self.update()
            return

        # Cursor hover
        objects = self.current_page_objects()
        if self._selected is not None:
            r = self._object_view_rect(self._selected)
            h = self._selected.hit_test_handle(r.x(), r.y(), r.width(), r.height(), pt)
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

        for obj in reversed(objects):
            if self._object_view_rect(obj).contains(pt):
                self.setCursor(Qt.SizeAllCursor)
                return
        self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._drag_handle = -1
            self._drag_endpoint_handles = False
            # Reset drag action tracking
            self._action_recorded_this_drag = False

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._selected is not None:
            self.editRequested.emit(self._selected)

    # ---------------------------------------------------------------- keyboard

    def keyPressEvent(self, event) -> None:
        key = event.key()
        modifiers = event.modifiers()
        
        # Get selected annotations
        selected = self.get_selected_annotations()
        
        # ================================================================ Page navigation
        # Page Up / Page Down
        if key == Qt.Key_PageDown:
            self.goto_page(self._current_page + 1)
            return
        elif key == Qt.Key_PageUp:
            self.goto_page(self._current_page - 1)
            return
        elif key == Qt.Key_Home:
            self.goto_page(0)
            return
        elif key == Qt.Key_End:
            self.goto_page(len(self._pages) - 1)
            return
        
        # ================================================================ Escape: Deselect all
        if key == Qt.Key_Escape:
            self.clear_selection()
            return
        
        # ================================================================ Delete annotation(s)
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            if selected:
                self.delete_selected()
            return
        
        # ================================================================ Arrow keys
        if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if selected:
                # Movement: 12pt normal, 1px with Shift (per V1.2.18)
                increment = 1.0 if modifiers & Qt.ShiftModifier else 12.0
                
                if key == Qt.Key_Up:
                    self.move_selected(0, -increment)
                elif key == Qt.Key_Down:
                    self.move_selected(0, increment)
                elif key == Qt.Key_Left:
                    self.move_selected(-increment, 0)
                elif key == Qt.Key_Right:
                    self.move_selected(increment, 0)
                return
            else:
                # Page navigation without annotation selected: left/right arrows
                if key == Qt.Key_Left:
                    self.goto_page(self._current_page - 1)
                    return
                elif key == Qt.Key_Right:
                    self.goto_page(self._current_page + 1)
                    return
        
        # ================================================================ Copy / Cut / Paste / Duplicate
        # Both Ctrl variants (Ctrl+C/X/V/D/A/Z/Y) and single-key variants (C/X/V/D/A/Z/Y)
        is_ctrl_key = modifiers & Qt.ControlModifier
        is_shift_key = modifiers & Qt.ShiftModifier
        
        if is_ctrl_key:
            if key == Qt.Key_C:
                if selected:
                    self.copy_selected()
                return
            elif key == Qt.Key_X:
                if selected:
                    self.cut_selected()
                return
            elif key == Qt.Key_V:
                self.paste_selected()
                return
            elif key == Qt.Key_D:
                if selected:
                    self.duplicate_selected()
                return
            elif key == Qt.Key_A:
                self.select_all_on_page()
                return
            elif key == Qt.Key_Z:
                # Undo (Ctrl+Z) - delegate to parent window
                self.parent().undo() if hasattr(self.parent(), 'undo') else None
                return
            elif key in (Qt.Key_Y, Qt.Key_Plus):  # Ctrl+Y for Redo
                # Redo (Ctrl+Y or Ctrl+Shift+Z) - delegate to parent window
                self.parent().redo() if hasattr(self.parent(), 'redo') else None
                return
            # ================================================================ Rotation with Ctrl
            elif key == Qt.Key_L:
                if is_shift_key:
                    # Shift+Ctrl+L: Rotate current page left
                    self.rotate_current_page_left()
                else:
                    # Ctrl+L: Rotate all pages left
                    self.rotate_all_pages_left()
                return
            elif key == Qt.Key_R:
                if is_shift_key:
                    # Shift+Ctrl+R: Rotate current page right
                    self.rotate_current_page_right()
                else:
                    # Ctrl+R: Rotate all pages right
                    self.rotate_all_pages_right()
                return
            # ================================================================ Document operations (delegate to parent)
            elif key == Qt.Key_O:
                # Ctrl+O: Open document
                if hasattr(self.parent(), 'open_document'):
                    self.parent().open_document()
                return
            elif key == Qt.Key_S:
                # Ctrl+S: Save As dialog
                if hasattr(self.parent(), 'save_document_as'):
                    self.parent().save_document_as()
                return
            elif key == Qt.Key_P:
                # Ctrl+P: Print
                if hasattr(self.parent(), 'print_document'):
                    self.parent().print_document()
                return
        else:
            # ================================================================ Single-key hotkey variants (no Ctrl)
            # These are available only in default document view (no Ctrl modifier)
            if key == Qt.Key_O:
                # O: Open document
                if hasattr(self.parent(), 'open_document'):
                    self.parent().open_document()
                return
            elif key == Qt.Key_S:
                # S: Save As dialog
                if hasattr(self.parent(), 'save_document_as'):
                    self.parent().save_document_as()
                return
            elif key == Qt.Key_P:
                # P: Print
                if hasattr(self.parent(), 'print_document'):
                    self.parent().print_document()
                return
            elif key == Qt.Key_C:
                # C: Copy
                if selected:
                    self.copy_selected()
                return
            elif key == Qt.Key_X:
                # X: Cut
                if selected:
                    self.cut_selected()
                return
            elif key == Qt.Key_V:
                # V: Paste
                self.paste_selected()
                return
            elif key == Qt.Key_D:
                # D: Duplicate
                if selected:
                    self.duplicate_selected()
                return
            elif key == Qt.Key_A:
                # A: Select all
                self.select_all_on_page()
                return
            elif key == Qt.Key_Z:
                # Z: Undo
                if hasattr(self.parent(), 'undo'):
                    self.parent().undo()
                return
            elif key == Qt.Key_Y:
                # Y: Redo
                if hasattr(self.parent(), 'redo'):
                    self.parent().redo()
                return
            elif key == Qt.Key_L:
                # L or Shift+L: Rotate
                if is_shift_key:
                    # Shift+L: Rotate current page left
                    self.rotate_current_page_left()
                else:
                    # L: Rotate all pages left
                    self.rotate_all_pages_left()
                return
            elif key == Qt.Key_R:
                # R or Shift+R: Rotate
                if is_shift_key:
                    # Shift+R: Rotate current page right
                    self.rotate_current_page_right()
                else:
                    # R: Rotate all pages right
                    self.rotate_all_pages_right()
                return
        
        # v1.2.22: Width/font size adjustment with [ and ] keys
        if not is_ctrl_key and not is_shift_key:
            if key == Qt.Key_BracketLeft:  # [
                # Decrease line width or font size
                if selected:
                    self._adjust_annotation_property(selected, 'decrease')
                return
            elif key == Qt.Key_BracketRight:  # ]
                # Increase line width or font size
                if selected:
                    self._adjust_annotation_property(selected, 'increase')
                return
        
        super().keyPressEvent(event)
