from __future__ import annotations

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .objects import (
    ANCHOR_HANDLE,
    HANDLE_FX,
    HANDLE_FY,
    CanvasObject,
)


class DocumentCanvas(QWidget):
    objectChanged = Signal()        # emitted on move/scale/add/remove
    pageChanged = Signal(int, int)  # (current_page_0indexed, total_pages)
    editRequested = Signal(object)  # CanvasObject — double-click

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._pages: list[Image.Image] = []
        self._page_pixmaps: list[QPixmap] = []
        self._current_page: int = 0
        self._page_objects: dict[int, list[CanvasObject]] = {}
        self._page_rotations: dict[int, int] = {}  # Track rotation angle (0, 90, 180, 270) per page

        self._selected: CanvasObject | None = None
        self._dragging: bool = False
        self._drag_handle: int = -1

        self._drag_doc_offset_x: float = 0.0
        self._drag_doc_offset_y: float = 0.0

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
        self._selected = None
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
        if self._selected is None:
            return
        objs = self._page_objects.get(self._current_page, [])
        if self._selected in objs:
            objs.remove(self._selected)
        self._selected = None
        self.objectChanged.emit()
        self.update()

    def duplicate_selected(self) -> None:
        if self._selected is None:
            return
        dup = self._selected.duplicate()
        dup.page = self._current_page
        self.add_object(dup)

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

            if obj is self._selected:
                painter.save()
                painter.setPen(QColor("#00a2ff"))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(r)
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
                prev_selected = self._selected
                self._selected = obj
                self._dragging = True
                self._drag_handle = -1
                doc_pt = self._view_to_doc(pt)
                self._drag_doc_offset_x = doc_pt.x() - obj.x
                self._drag_doc_offset_y = doc_pt.y() - obj.y
                if prev_selected is not obj:
                    self.objectChanged.emit()
                self.update()
                return

        if self._selected is not None:
            self._selected = None
            self.objectChanged.emit()
        self.update()

    def _start_handle_drag(self, h_idx: int, pt: QPointF) -> None:
        obj = self._selected
        assert obj is not None
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

    def mouseMoveEvent(self, event) -> None:
        pt = event.position()

        if self._dragging and self._selected is not None:
            if self._drag_handle == -1:
                doc_pt = self._view_to_doc(pt)
                self._selected.x = doc_pt.x() - self._drag_doc_offset_x
                self._selected.y = doc_pt.y() - self._drag_doc_offset_y
            else:
                doc_pt = self._view_to_doc(pt)
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

                self._selected.set_scaled_size(new_w, new_h)
                self._selected.x = ax - self._hdrag_anchor_fx * self._selected.scaled_width
                self._selected.y = ay - self._hdrag_anchor_fy * self._selected.scaled_height

            if self.current_page_image and not self._selected.supports_free_resize():
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

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._selected is not None:
            self.editRequested.emit(self._selected)

    # ---------------------------------------------------------------- keyboard

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key_PageDown:
            self.goto_page(self._current_page + 1)
        elif key == Qt.Key_PageUp:
            self.goto_page(self._current_page - 1)
        elif key == Qt.Key_Home:
            self.goto_page(0)
        elif key == Qt.Key_End:
            self.goto_page(len(self._pages) - 1)
        elif key in (Qt.Key_Delete, Qt.Key_Backspace) and self._selected is not None:
            self.remove_selected()
        else:
            super().keyPressEvent(event)
