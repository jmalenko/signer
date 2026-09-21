from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

logger = logging.getLogger(__name__)


DEFAULT_TEXT_FONT_PT: int = 11
# Document is internally rendered at 300 DPI, PDF standard is 72 DPI
# DPI_SCALE is used to convert PDF points to 300 DPI pixels for rendering
DPI_SCALE: float = 300.0 / 72.0  # 4.16667
DEFAULT_FONT_FAMILY: str = "Arial"
DEFAULT_LINE_WIDTH_PT: float = 1.5  # v1.2.22: Default line width in points
DUPLICATE_OFFSET: float = 20.0

# v1.2.32: Discrete step lists for the `[` / `]` keyboard shortcuts, so each press
# jumps to a "usual" size rather than a small fixed increment.
FONT_SIZE_STEPS_PT: tuple[float, ...] = (
    6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 54, 60, 66, 72,
)
LINE_WIDTH_STEPS_PT: tuple[float, ...] = (
    0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16,
)


def step_size(value: float, steps: tuple[float, ...], direction: str) -> float:
    """Return the next value from `steps` in the given direction ('increase'/'decrease').

    Snaps to the nearest step in that direction if `value` isn't already on the list.
    Clamps at the ends of `steps` (no wraparound).
    """
    epsilon = 1e-6
    if direction == "increase":
        for step in steps:
            if step > value + epsilon:
                return step
        return steps[-1]
    else:
        for step in reversed(steps):
            if step < value - epsilon:
                return step
        return steps[0]


class AnnotationType(Enum):
    SIGNATURE = "signature"
    CHECKMARK = "checkmark"
    CROSSMARK = "crossmark"
    LINE = "line"  # v1.2.22
    RECTANGLE = "rectangle"  # v1.2.22
    ELLIPSE = "ellipse"  # v1.2.22
    ARROW = "arrow"  # v1.2.24: Generic arrow (points right by default)
    TEXT = "text"
    IMAGE = "image"  # v1.2.22: Image overlay (signature or image annotation)


ARROW_TYPES: set[AnnotationType] = {
    AnnotationType.ARROW,  # v1.2.24
}

# v1.2.22: Annotation types that support line width control
VECTOR_WITH_WIDTH: set[AnnotationType] = {
    AnnotationType.CHECKMARK,
    AnnotationType.CROSSMARK,
    AnnotationType.LINE,
    AnnotationType.RECTANGLE,
    AnnotationType.ELLIPSE,
    AnnotationType.ARROW,  # v1.2.24
}

LARGE_DEFAULT_TYPES: set[AnnotationType] = {
    AnnotationType.LINE,
    AnnotationType.RECTANGLE,
    AnnotationType.ELLIPSE,
    AnnotationType.ARROW,  # v1.2.24
}

# 8 handles: TL, TC, TR, ML, MR, BL, BC, BR
HANDLE_FX = [0.0, 0.5, 1.0, 0.0, 1.0, 0.0, 0.5, 1.0]
HANDLE_FY = [0.0, 0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0]
ANCHOR_HANDLE = [7, 6, 5, 4, 3, 2, 1, 0]  # opposite handle for each handle
HANDLE_SIZE = 10.0
ROTATION_HANDLE_SIZE = 12.0
ROTATION_HANDLE_OFFSET = 24.0
VISIBLE_ALPHA_RUN = re.compile(rb"[^\x00]+")


class CanvasObject:
    """Base class for all objects placed on the canvas (document-space coordinates)."""

    DEFAULT_BASE_SIZE: float = 20.0  # Annotation size in PDF points

    def __init__(self, x: float, y: float, width: float, height: float, page: int = 0) -> None:
        self.x = x
        self.y = y
        self._base_width = float(width)
        self._base_height = float(height)
        self.scale: float = 1.0
        self._rotation: float = 0.0
        self.page: int = page
        self.color: QColor = QColor("#cc0000")

    @property
    def scaled_width(self) -> float:
        return self._base_width * self.scale

    @property
    def scaled_height(self) -> float:
        return self._base_height * self.scale

    @property
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, angle: float) -> None:
        self._rotation = float(angle) % 360.0

    def clamp_to_page(self, pw: float, ph: float) -> None:
        self.x = max(0.0, min(self.x, max(0.0, pw - self.scaled_width)))
        self.y = max(0.0, min(self.y, max(0.0, ph - self.scaled_height)))

    def draw_in_viewport(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        raise NotImplementedError

    def render_to_pil(self) -> Image.Image:
        """Return an RGBA PIL image at the current scaled size for compositing."""
        raise NotImplementedError

    def duplicate(self) -> CanvasObject:
        raise NotImplementedError

    def handle_rects_viewport(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None = None,
    ) -> list[QRectF]:
        hs = HANDLE_SIZE
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        return [
            QRectF(point.x() - hs / 2, point.y() - hs / 2, hs, hs)
            for point in (
                self._rotate_point(QPointF(vx + fx * vw, vy + fy * vh), center, angle)
                for fx, fy in zip(HANDLE_FX, HANDLE_FY)
            )
        ]

    def rotation_handle_center_viewport(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None = None,
    ) -> QPointF:
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        return self._rotate_point(
            QPointF(center.x(), vy - ROTATION_HANDLE_OFFSET), center, angle
        )

    def rotation_handle_rect_viewport(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None = None,
    ) -> QRectF:
        center = self.rotation_handle_center_viewport(vx, vy, vw, vh, rotation)
        half = ROTATION_HANDLE_SIZE / 2.0
        return QRectF(center.x() - half, center.y() - half, ROTATION_HANDLE_SIZE, ROTATION_HANDLE_SIZE)

    def supports_free_resize(self) -> bool:
        return False

    def supports_endpoint_handles(self) -> bool:
        return False

    def endpoint_points_viewport(self, vx: float, vy: float, vw: float, vh: float) -> list[QPointF]:
        return []

    def endpoint_points_doc(self) -> list[QPointF]:
        return self.endpoint_points_viewport(self.x, self.y, self.scaled_width, self.scaled_height)

    @staticmethod
    def _rotate_point(point: QPointF, center: QPointF, angle_deg: float) -> QPointF:
        """Rotate a point clockwise in screen/document coordinates."""
        radians = math.radians(angle_deg)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        return QPointF(
            center.x() + cos_a * dx - sin_a * dy,
            center.y() + sin_a * dx + cos_a * dy,
        )

    def boundary_points_viewport(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None = None,
    ) -> list[QPointF]:
        """Return the four corners of the rotated viewport boundary."""
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        return [
            self._rotate_point(point, center, angle)
            for point in (
                QPointF(vx, vy),
                QPointF(vx + vw, vy),
                QPointF(vx + vw, vy + vh),
                QPointF(vx, vy + vh),
            )
        ]

    def render_for_compositing(self) -> tuple[Image.Image, float, float]:
        """Render at the stored angle and return image plus center-preserving position."""
        unrotated = self.render_to_pil().convert("RGBA")
        angle = self.rotation % 360.0
        if abs(angle) < 1e-9:
            return unrotated, self.x, self.y
        rotated = unrotated.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
        center_x = self.x + self.scaled_width / 2.0
        center_y = self.y + self.scaled_height / 2.0
        return rotated, center_x - rotated.width / 2.0, center_y - rotated.height / 2.0

    def set_scaled_size(self, width: float, height: float) -> None:
        """Resize object in document-space units."""
        width = max(8.0, width)
        height = max(8.0, height)
        if self.supports_free_resize():
            self._base_width = width
            self._base_height = height
            self.scale = 1.0
            return

        sx = width / max(1.0, self._base_width)
        sy = height / max(1.0, self._base_height)
        self.scale = max(0.05, min(10.0, max(sx, sy)))

    def resize_to_bounds(self, width: float, height: float) -> None:
        """Apply an interactive boundary resize."""
        self.set_scaled_size(width, height)

    def hit_test_handle(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        pt: QPointF,
        rotation: float | None = None,
    ) -> int:
        """Return handle index 0-7 if pt is over a handle, else -1."""
        for i, r in enumerate(self.handle_rects_viewport(vx, vy, vw, vh, rotation)):
            if r.contains(pt):
                return i
        return -1

    def contains_viewport_point(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        pt: QPointF,
        rotation: float | None = None,
    ) -> bool:
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        local_pt = self._rotate_point(pt, center, -angle)
        return QRectF(vx, vy, vw, vh).contains(local_pt)

    def hit_test_point(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        pt: QPointF,
        rotation: float | None = None,
    ) -> bool:
        """Return True only when the point lands on a visible alpha pixel."""
        if vw <= 0 or vh <= 0:
            return False
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        local_pt = self._rotate_point(pt, center, -angle)
        if not QRectF(vx, vy, vw, vh).contains(local_pt):
            return False

        img = self.render_to_pil().convert("RGBA")
        if img.width <= 0 or img.height <= 0:
            return False

        rel_x = ((local_pt.x() - vx) / vw) * img.width
        rel_y = ((local_pt.y() - vy) / vh) * img.height
        x = int(round(rel_x))
        y = int(round(rel_y))
        if x < 0 or x >= img.width or y < 0 or y >= img.height:
            return False

        alpha = img.getpixel((x, y))[3]
        return alpha > 0

    def distance_to_visible_pixel(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        pt: QPointF,
        rotation: float | None = None,
    ) -> float:
        """Distance from pt to the nearest visible rendered pixel in this object."""
        if vw <= 0 or vh <= 0:
            return float("inf")

        img = self.render_to_pil().convert("RGBA")
        if img.width <= 0 or img.height <= 0:
            return float("inf")

        width, height = img.size
        alpha = img.getchannel("A").tobytes()
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        local_pt = self._rotate_point(pt, center, -angle)
        query_x = ((local_pt.x() - vx) / vw) * width
        query_y = ((local_pt.y() - vy) / vh) * height
        scale_x = vw / width
        scale_y = vh / height
        nearest_squared = float("inf")

        # Scan nontransparent byte runs in native regex code, then split runs
        # at row boundaries so Python evaluates horizontal spans, not pixels.
        for match in VISIBLE_ALPHA_RUN.finditer(alpha):
            start, end = match.span()
            while start < end:
                y = start // width
                row_end = min(end, (y + 1) * width)
                left = start - y * width
                right = row_end - y * width - 1
                nearest_x = min(max(round(query_x), left), right)
                dx = (nearest_x - query_x) * scale_x
                dy = (y - query_y) * scale_y
                nearest_squared = min(nearest_squared, dx * dx + dy * dy)
                start = row_end

        return math.sqrt(nearest_squared)

    # ------------------------------------------------------------------ serialization

    def to_dict(self) -> dict[str, Any]:
        """Serialize object to a dictionary."""
        return {
            "type": self.__class__.__name__,
            "x": self.x,
            "y": self.y,
            "base_width": self._base_width,
            "base_height": self._base_height,
            "scale": self.scale,
            "rotation": self.rotation % 360.0,
            "page": self.page,
            "color": self.color.name(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanvasObject:
        """Deserialize object from a dictionary."""
        raise NotImplementedError("Subclasses must implement from_dict")


class SignatureObject(CanvasObject):
    """A PNG image overlay (signature or image annotation)."""

    def __init__(self, image: Image.Image, path: str, x: float, y: float, page: int = 0) -> None:
        img = image.convert("RGBA")
        super().__init__(x, y, float(img.width), float(img.height), page)
        self._image = img
        self.path = path
        self._pixmap_cache: QPixmap | None = None
        self._pixmap_scale: float | None = None

    @property
    def image(self) -> Image.Image:
        return self._image

    def _get_pixmap(self) -> QPixmap:
        if self._pixmap_cache is not None and self._pixmap_scale == self.scale:
            return self._pixmap_cache
        w = max(1, int(round(self._base_width * self.scale)))
        h = max(1, int(round(self._base_height * self.scale)))
        resized = self._image.resize((w, h), Image.Resampling.LANCZOS)
        self._pixmap_cache = QPixmap.fromImage(ImageQt(resized))
        self._pixmap_scale = self.scale
        return self._pixmap_cache

    def draw_in_viewport(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        pm = self._get_pixmap()
        painter.drawPixmap(QRectF(vx, vy, vw, vh), pm, QRectF(pm.rect()))

    def render_to_pil(self) -> Image.Image:
        w = max(1, int(round(self._base_width * self.scale)))
        h = max(1, int(round(self._base_height * self.scale)))
        return self._image.resize((w, h), Image.Resampling.LANCZOS)

    def duplicate(self) -> SignatureObject:
        obj = SignatureObject(
            self._image.copy(),
            self.path,
            self.x + DUPLICATE_OFFSET,
            self.y + DUPLICATE_OFFSET,
            self.page,
        )
        obj.scale = self.scale
        obj.rotation = self.rotation
        obj.color = QColor(self.color)
        return obj

    def to_dict(self) -> dict[str, Any]:
        """Serialize object to a dictionary."""
        data = super().to_dict()
        data["path"] = self.path
        # Store image as base64
        import base64
        from io import BytesIO
        buf = BytesIO()
        self._image.save(buf, format="PNG")
        data["image_data"] = base64.b64encode(buf.getvalue()).decode("ascii")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignatureObject:
        """Deserialize object from a dictionary."""
        import base64
        from io import BytesIO
        if "image_data" in data:
            img_data = base64.b64decode(data["image_data"])
            img = Image.open(BytesIO(img_data)).convert("RGBA")
        else:
            image_path = Path(data["path"])
            if not image_path.exists():
                raise ValueError(f"Signature image not found: {image_path}")
            img = Image.open(image_path).convert("RGBA")
        obj = cls(img, data["path"], data["x"], data["y"], data["page"])
        obj._base_width = data["base_width"]
        obj._base_height = data["base_height"]
        obj.scale = data["scale"]
        obj.rotation = float(data.get("rotation", 0.0)) % 360.0
        obj.color = QColor(data["color"])
        return obj


class VectorAnnotation(CanvasObject):
    """Checkmark, crossmark, arrow, or text annotation drawn as vector graphics."""

    def __init__(
        self,
        ann_type: AnnotationType,
        x: float,
        y: float,
        page: int = 0,
        text: str = "",
        font_family: str = DEFAULT_FONT_FAMILY,
        font_size_pt: int = DEFAULT_TEXT_FONT_PT,
        line_width_pt: float = DEFAULT_LINE_WIDTH_PT,  # v1.2.22
    ) -> None:
        self._font_family = font_family
        self._font_size_pt = font_size_pt
        self._line_width_pt = line_width_pt  # v1.2.22
        self._angle: float | None = None  # Rotation angle in degrees for LINE/ARROW
        if ann_type == AnnotationType.TEXT:
            # Text box: 180×36 points, scale for 300 DPI rendering
            super().__init__(x, y, 180.0 * DPI_SCALE, 36.0 * DPI_SCALE, page)
            self.ann_type = ann_type
            self.text = text
            self.fit_text_box()
        else:
            # v1.2.22 UX tweak: larger defaults for line/arrow/rectangle/ellipse.
            # Keep checkmark/crossmark at legacy size for document-density use.
            if ann_type in LARGE_DEFAULT_TYPES:
                base = 4.0 * self.DEFAULT_BASE_SIZE
            else:
                base = self.DEFAULT_BASE_SIZE
            # Base sizes are in PDF points, scale for 300 DPI rendering
            super().__init__(x, y, base * DPI_SCALE, base * DPI_SCALE, page)
            self.ann_type = ann_type
            self.text = text
            self._natural_width = float(base * DPI_SCALE)
            self._natural_height = float(base * DPI_SCALE)

    def supports_free_resize(self) -> bool:
        """Check if annotation type supports free-form resizing (not just scaling)."""
        return self.ann_type in {
            AnnotationType.TEXT,
            AnnotationType.LINE,  # v1.2.22
            AnnotationType.ARROW,  # v1.2.24: endpoint-driven resize; avoid scale-cap clamping
            AnnotationType.RECTANGLE,  # v1.2.22
            AnnotationType.ELLIPSE,  # v1.2.22
        }

    def set_scaled_size(self, width: float, height: float) -> None:
        if self.ann_type != AnnotationType.TEXT:
            super().set_scaled_size(width, height)
            return

        target_width = max(8.0, width)
        target_height = max(8.0, height)
        width_factor = target_width / max(1.0, self.scaled_width)
        height_factor = target_height / max(1.0, self.scaled_height)
        size_factor = min(width_factor, height_factor)
        old_font_size = self._font_size_pt
        requested_font_size = round(old_font_size * size_factor)
        self._font_size_pt = max(
            FONT_SIZE_STEPS_PT[0],
            min(FONT_SIZE_STEPS_PT[-1], requested_font_size),
        )
        self.fit_text_box()
        if (
            self._font_size_pt != old_font_size
            and self._font_size_pt == requested_font_size
        ):
            self._base_width = target_width
            self._base_height = target_height
            self.scale = 1.0

    def resize_to_bounds(self, width: float, height: float) -> None:
        self.set_scaled_size(width, height)
        if self.ann_type == AnnotationType.TEXT:
            self.fit_text_box()

    def supports_endpoint_handles(self) -> bool:
        return self.ann_type in {AnnotationType.LINE, AnnotationType.ARROW}

    def endpoint_points_viewport(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None = None,
    ) -> list[QPointF]:
        if not self.supports_endpoint_handles():
            return []

        if self.ann_type == AnnotationType.LINE:
            angle = getattr(self, '_angle', None)
            if angle is None:
                points = [QPointF(vx, vy + vh), QPointF(vx + vw, vy)]
                return self._rotate_endpoint_points(points, vx, vy, vw, vh, rotation)

            cx, cy = vx + vw / 2.0, vy + vh / 2.0
            half_len = min(vw, vh) / 2.0
            a_rad = math.radians(angle)
            cos_a = math.cos(a_rad)
            sin_a = math.sin(a_rad)
            points = [
                QPointF(cx - cos_a * half_len, cy - sin_a * half_len),
                QPointF(cx + cos_a * half_len, cy + sin_a * half_len),
            ]
            return self._rotate_endpoint_points(points, vx, vy, vw, vh, rotation)

        # ARROW: use actual drawn tail/tip so endpoint anchors match visuals.
        angle_deg = getattr(self, '_angle', None)
        if angle_deg is None:
            angle_deg = 0.0
        angle_rad = math.radians(angle_deg)
        cx, cy = vx + vw / 2.0, vy + vh / 2.0
        shaft = min(vw, vh) * 0.33
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        tail = QPointF(cx - cos_a * shaft, cy + sin_a * shaft)
        tip = QPointF(cx + cos_a * shaft, cy - sin_a * shaft)
        return self._rotate_endpoint_points([tail, tip], vx, vy, vw, vh, rotation)

    def _rotate_endpoint_points(
        self,
        points: list[QPointF],
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None,
    ) -> list[QPointF]:
        angle = self.rotation if rotation is None else rotation
        center = QPointF(vx + vw / 2.0, vy + vh / 2.0)
        return [self._rotate_point(point, center, angle) for point in points]

    def handle_rects_viewport(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        rotation: float | None = None,
    ) -> list[QRectF]:
        if not self.supports_endpoint_handles():
            return super().handle_rects_viewport(vx, vy, vw, vh, rotation)
        hs = HANDLE_SIZE
        return [
            QRectF(pt.x() - hs / 2.0, pt.y() - hs / 2.0, hs, hs)
            for pt in self.endpoint_points_viewport(vx, vy, vw, vh, rotation)
        ]

    # ------------------------------------------------------------------ text fitting

    def _make_font(self) -> QFont:
        f = QFont(self._font_family)
        # Font size is stored in PDF points; scale to pixels for 300 DPI rendering
        f.setPixelSize(int(round(self._font_size_pt * DPI_SCALE)))
        return f

    def fit_text_box(self) -> None:
        """Resize the bounding box so it exactly fits the current text at the set font size."""
        if self.ann_type != AnnotationType.TEXT:
            return

        lines = (self.text or "").split("\n")
        try:
            if QGuiApplication.instance() is None:
                raise RuntimeError("Qt font metrics require a GUI application")
            fm = QFontMetricsF(self._make_font())
            widest = 0.0
            for line in lines:
                widest = max(widest, fm.horizontalAdvance(line))
            line_h = fm.height()
            self._base_width = max(8.0, widest)
            self._base_height = max(8.0, line_h * len(lines))
            self._natural_width = self._base_width
            self._natural_height = self._base_height
            self.scale = 1.0
        except Exception:
            # Fallback for Qt font metrics failures on other platforms
            logger.debug("fit_text_box(): QFontMetricsF unavailable, using approximate sizing", exc_info=True)
            font_pixel_size = self._make_font().pixelSize()
            avg_char_width = max(8.0, float(font_pixel_size))
            widest_line = max((line.replace("\t", "    ") for line in lines or [""]), key=len)
            self._base_width = max(8.0, len(widest_line) * avg_char_width)
            self._base_height = max(8.0, font_pixel_size * 1.2 * len(lines))
            self._natural_width = self._base_width
            self._natural_height = self._base_height
            self.scale = 1.0

    # ------------------------------------------------------------------ drawing

    def draw_in_viewport(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_symbol(painter, vx, vy, vw, vh, doc_scale)
        painter.restore()

    def _pen(self, doc_scale: float = 1.0) -> QPen:
        pen = QPen(self.color)
        pen.setWidthF(max(1.5, self._line_width_pt * DPI_SCALE * doc_scale))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def _draw_symbol(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        m = min(vw, vh) * 0.12
        t = self.ann_type

        if t == AnnotationType.CHECKMARK:
            painter.setPen(self._pen(doc_scale))
            painter.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(vx + m, vy + vh * 0.55)
            path.lineTo(vx + vw * 0.38, vy + vh - m)
            path.lineTo(vx + vw - m, vy + m)
            painter.drawPath(path)

        elif t == AnnotationType.CROSSMARK:
            painter.setPen(self._pen(doc_scale))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(QPointF(vx + m, vy + m), QPointF(vx + vw - m, vy + vh - m))
            painter.drawLine(QPointF(vx + vw - m, vy + m), QPointF(vx + m, vy + vh - m))

        elif t == AnnotationType.LINE:
            pen = QPen(self.color)
            pen.setWidthF(max(1.5, self._line_width_pt * DPI_SCALE * doc_scale))
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            angle = getattr(self, '_angle', None)
            if angle is not None:
                # Draw a rotated line through the center of the bounding box.
                # Use min(vw, vh)/2 so the line always fits inside the box
                # regardless of angle.  The bounding box should be square for
                # full-length lines in all directions.
                cx, cy = vx + vw / 2.0, vy + vh / 2.0
                half_len = min(vw, vh) / 2.0
                a_rad = math.radians(angle)
                cos_a = math.cos(a_rad)
                sin_a = math.sin(a_rad)
                painter.drawLine(
                    QPointF(cx - cos_a * half_len, cy - sin_a * half_len),
                    QPointF(cx + cos_a * half_len, cy + sin_a * half_len),
                )
            else:
                # Default: diagonal line from bottom-left to top-right (like /)
                painter.drawLine(QPointF(vx, vy + vh), QPointF(vx + vw, vy))

        elif t == AnnotationType.RECTANGLE:
            pen = QPen(self.color)
            pen.setWidthF(max(1.5, self._line_width_pt * DPI_SCALE * doc_scale))
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            half_pw = pen.widthF() / 2.0
            painter.drawRect(QRectF(vx + half_pw, vy + half_pw, vw - pen.widthF(), vh - pen.widthF()))

        elif t == AnnotationType.ELLIPSE:
            pen = QPen(self.color)
            pen.setWidthF(max(1.5, self._line_width_pt * DPI_SCALE * doc_scale))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            half_pw = pen.widthF() / 2.0
            painter.drawEllipse(QRectF(vx + half_pw, vy + half_pw, vw - pen.widthF(), vh - pen.widthF()))

        elif t == AnnotationType.TEXT:
            factor = min(
                self.scaled_width / max(1.0, self._natural_width),
                self.scaled_height / max(1.0, self._natural_height),
            )
            font = self._make_font()
            # Font size already includes DPI_SCALE from _make_font(), multiply by factor and doc_scale
            font.setPixelSize(max(1, int(round(font.pixelSize() * factor * doc_scale))))
            painter.setFont(font)
            painter.setPen(self.color)
            painter.setBrush(Qt.NoBrush)
            painter.drawText(QRectF(vx, vy, vw, vh), Qt.AlignLeft | Qt.AlignTop, self.text or "")

        elif t == AnnotationType.ARROW:
            # ARROW uses _angle for free rotation
            angle_deg = getattr(self, '_angle', None)
            if angle_deg is None:
                angle_deg = 0.0
            angle_rad = math.radians(angle_deg)
            cx, cy = vx + vw / 2, vy + vh / 2
            shaft = min(vw, vh) * 0.33
            head = min(vw, vh) * 0.18
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            tip = QPointF(cx + cos_a * shaft, cy - sin_a * shaft)
            tail = QPointF(cx - cos_a * shaft, cy + sin_a * shaft)
            pen = QPen(self.color)
            pen.setWidthF(max(1.5, self._line_width_pt * DPI_SCALE * doc_scale))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(tail, tip)
            la = angle_rad + math.radians(145)
            ra = angle_rad - math.radians(145)
            left_tip = QPointF(tip.x() + math.cos(la) * head, tip.y() - math.sin(la) * head)
            right_tip = QPointF(tip.x() + math.cos(ra) * head, tip.y() - math.sin(ra) * head)
            # Draw all arrowheads as stroked segments so head width matches stem.
            painter.drawLine(tip, left_tip)
            painter.drawLine(tip, right_tip)

    # ------------------------------------------------------------------ PIL render

    def render_to_pil(self) -> Image.Image:
        w = max(1, int(round(self._base_width * self.scale)))
        h = max(1, int(round(self._base_height * self.scale)))
        qimage = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        qimage.fill(Qt.transparent)
        painter = QPainter(qimage)
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_symbol(painter, 0.0, 0.0, float(w), float(h), doc_scale=1.0)
        painter.end()
        qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
        ptr = qimage.bits()
        bpl = qimage.bytesPerLine()
        raw_bytes = ptr.tobytes() if hasattr(ptr, "tobytes") else bytes(ptr)
        # Strip row padding if any
        if bpl != w * 4:
            rows = [raw_bytes[r * bpl: r * bpl + w * 4] for r in range(h)]
            raw_bytes = b"".join(rows)
        return Image.frombytes("RGBA", (w, h), raw_bytes)

    # ------------------------------------------------------------------ duplicate

    def duplicate(self) -> VectorAnnotation:
        obj = VectorAnnotation(
            self.ann_type,
            self.x + DUPLICATE_OFFSET,
            self.y + DUPLICATE_OFFSET,
            self.page,
            self.text,
            font_family=self._font_family,
            font_size_pt=self._font_size_pt,
            line_width_pt=self._line_width_pt,  # v1.2.22
        )
        obj.scale = self.scale
        obj.rotation = self.rotation
        obj.color = QColor(self.color)
        # v1.2.22: Copy bounding box for free-resize types (TEXT, LINE, RECTANGLE, ELLIPSE)
        if self.supports_free_resize():
            obj._base_width = self._base_width
            obj._base_height = self._base_height
            obj._natural_width = self._natural_width
            obj._natural_height = self._natural_height
        obj._angle = self._angle
        return obj

    def to_dict(self) -> dict[str, Any]:
        """Serialize object to a dictionary."""
        data = super().to_dict()
        data["ann_type"] = self.ann_type.value
        data["text"] = self.text
        # Only save font properties for TEXT annotations
        if self.ann_type == AnnotationType.TEXT:
            data["font_family"] = self._font_family
            data["font_size_pt"] = self._font_size_pt
        # Save line width for vector annotations (all types)
        data["line_width_pt"] = self._line_width_pt  # v1.2.22: line width in points
        data["natural_width"] = self._natural_width
        data["natural_height"] = self._natural_height
        if self._angle is not None:
            data["angle"] = self._angle
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VectorAnnotation:
        """Deserialize object from a dictionary."""
        ann_type = AnnotationType(data["ann_type"])
        obj = cls(
            ann_type,
            data["x"],
            data["y"],
            data["page"],
            data.get("text", ""),
            font_family=data.get("font_family", DEFAULT_FONT_FAMILY),
            font_size_pt=data.get("font_size_pt", DEFAULT_TEXT_FONT_PT),
            line_width_pt=data.get("line_width_pt", DEFAULT_LINE_WIDTH_PT),  # v1.2.22
        )
        obj._base_width = data["base_width"]
        obj._base_height = data["base_height"]
        obj.scale = data["scale"]
        obj.rotation = float(data.get("rotation", 0.0)) % 360.0
        # Handle color: can be either a string like "#FF0000" or already a QColor
        color_val = data["color"]
        if isinstance(color_val, QColor):
            obj.color = color_val
        else:
            obj.color = QColor(color_val)
        obj._natural_width = data.get("natural_width", obj._natural_width)
        obj._natural_height = data.get("natural_height", obj._natural_height)
        obj._angle = data.get("angle", None)
        return obj


# ------------------------------------------------------------------ factory

def canvas_object_from_dict(data: dict[str, Any]) -> CanvasObject | None:
    """Factory function to deserialize a CanvasObject from a dictionary.
    
    Dispatches to the appropriate subclass based on the "type" field.
    
    Args:
        data: Dictionary containing serialized object data
        
    Returns:
        Deserialized CanvasObject, or None if type is unknown
    """
    obj_type = data.get("type")
    
    if obj_type == "SignatureObject":
        return SignatureObject.from_dict(data)
    elif obj_type == "VectorAnnotation":
        return VectorAnnotation.from_dict(data)
    else:
        # Unknown type; return None
        return None


class ProjectFile:
    """Project-workspace persistence using the same canonical serialized objects.

    The project file does not invent a second annotation model; it stores the same
    dictionary payloads produced by CanvasObject.to_dict() and rehydrates them via
    canvas_object_from_dict(). This keeps project save/load, action recorder data,
    and JSON fixtures aligned to one schema.
    """

    SCHEMA = "signer.project.v1"
    VERSION = 1

    @classmethod
    def validate(cls, project: dict[str, Any]) -> None:
        if project.get("version") != cls.VERSION:
            raise ValueError("Unsupported signer project file version")
        if not isinstance(project.get("document_path"), str) or not isinstance(project.get("annotations"), list):
            raise ValueError("Invalid signer project file")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_annotations(
        cls,
        *,
        document_path: str | Path | None,
        export_path: str | Path | None,
        annotations: list[CanvasObject],
        current_page: int,
        page_count: int,
    ) -> dict[str, Any]:
        doc_path = str(document_path) if document_path is not None else ""
        serialized_annotations = []
        for obj in annotations:
            data = {
                "type": "open_signature" if isinstance(obj, SignatureObject) else "add_annotation",
                "x": obj.x,
                "y": obj.y,
                "width": obj.scaled_width,
                "height": obj.scaled_height,
                "color": obj.color.name(),
            }
            if obj.page:
                data["page"] = obj.page
            if isinstance(obj, SignatureObject):
                data["path"] = obj.path
                data["image_data"] = obj.to_dict()["image_data"]
                if obj.scale != 1.0:
                    data["scale"] = obj.scale
            else:
                data["annotation_type"] = obj.ann_type.value
                data["line_width_pt"] = obj._line_width_pt
                if obj.scale != 1.0:
                    data["scale"] = obj.scale
                if obj.ann_type == AnnotationType.TEXT:
                    data["text"] = obj.text
                    data["font_family"] = obj._font_family
                    data["font_size_pt"] = obj._font_size_pt
            serialized_annotations.append(data)

        return {
            "version": cls.VERSION,
            "document_path": doc_path,
            "annotations": serialized_annotations,
        }

    @staticmethod
    def load_annotations(
        project: dict[str, Any], base_path: str | Path | None = None
    ) -> list[CanvasObject]:
        """Return the reconstituted objects stored in a project file."""
        items = project.get("annotations", [])
        restored: list[CanvasObject] = []
        for item in items:
            if item.get("type") == "open_signature":
                object_data = dict(item)
                object_data["type"] = "SignatureObject"
                object_data.setdefault("page", 0)
                object_data.setdefault("scale", 1.0)
                object_data.setdefault("color", "#cc0000")
                if base_path and not Path(object_data["path"]).is_absolute():
                    object_data["path"] = str(Path(base_path) / object_data["path"])
                if "image_data" in object_data:
                    import base64
                    from io import BytesIO
                    image = Image.open(BytesIO(base64.b64decode(object_data["image_data"])))
                else:
                    image = Image.open(object_data["path"])
                object_data.setdefault("width", image.width)
                object_data.setdefault("height", image.height)
                scale = float(object_data["scale"])
                object_data.setdefault("base_width", object_data["width"] / scale)
                object_data.setdefault("base_height", object_data["height"] / scale)
                if image is not None:
                    object_data.setdefault("base_width", image.width)
                    object_data.setdefault("base_height", image.height)
                    image.close()
                obj = canvas_object_from_dict(object_data)
            elif item.get("type") == "add_annotation":
                object_data = dict(item)
                object_data["type"] = "VectorAnnotation"
                object_data["ann_type"] = object_data.pop("annotation_type")
                object_data.setdefault("page", 0)
                object_data.setdefault("scale", 1.0)
                object_data.setdefault("line_width_pt", DEFAULT_LINE_WIDTH_PT)
                ann_type = AnnotationType(object_data["ann_type"])
                defaults = VectorAnnotation(ann_type, object_data["x"], object_data["y"], object_data["page"])
                object_data.setdefault("width", defaults.scaled_width)
                object_data.setdefault("height", defaults.scaled_height)
                scale = float(object_data["scale"])
                object_data.setdefault("base_width", object_data["width"] / scale)
                object_data.setdefault("base_height", object_data["height"] / scale)
                obj = canvas_object_from_dict(object_data)
            else:
                obj = None
            if obj is None:
                raise ValueError("Unknown annotation type in signer project file")
            restored.append(obj)
        return restored

    @classmethod
    def write(cls, path: str | Path, project: dict[str, Any]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(project, fh, indent=2)

    @classmethod
    def read(cls, path: str | Path) -> dict[str, Any]:
        with Path(path).open("r", encoding="utf-8") as fh:
            return json.load(fh)
