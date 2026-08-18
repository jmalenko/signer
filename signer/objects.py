from __future__ import annotations

import json
import math
from enum import Enum
from typing import Any

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


DEFAULT_TEXT_FONT_PT: int = 11
# Document is internally rendered at 300 DPI, PDF standard is 72 DPI
# DPI_SCALE is used to convert PDF points to 300 DPI pixels for rendering
DPI_SCALE: float = 300.0 / 72.0  # 4.16667
DEFAULT_FONT_FAMILY: str = "Arial"
DEFAULT_LINE_WIDTH_FACTOR: float = 0.07


class AnnotationType(Enum):
    SIGNATURE = "signature"
    CHECKMARK = "checkmark"
    CROSSMARK = "crossmark"
    ARROW_N = "arrow_n"
    ARROW_NE = "arrow_ne"
    ARROW_E = "arrow_e"
    ARROW_SE = "arrow_se"
    ARROW_S = "arrow_s"
    ARROW_SW = "arrow_sw"
    ARROW_W = "arrow_w"
    ARROW_NW = "arrow_nw"
    TEXT = "text"


ARROW_TYPES: set[AnnotationType] = {
    AnnotationType.ARROW_N,
    AnnotationType.ARROW_NE,
    AnnotationType.ARROW_E,
    AnnotationType.ARROW_SE,
    AnnotationType.ARROW_S,
    AnnotationType.ARROW_SW,
    AnnotationType.ARROW_W,
    AnnotationType.ARROW_NW,
}

ARROW_ANGLES: dict[AnnotationType, float] = {
    AnnotationType.ARROW_E: 0.0,
    AnnotationType.ARROW_NE: 45.0,
    AnnotationType.ARROW_N: 90.0,
    AnnotationType.ARROW_NW: 135.0,
    AnnotationType.ARROW_W: 180.0,
    AnnotationType.ARROW_SW: 225.0,
    AnnotationType.ARROW_S: 270.0,
    AnnotationType.ARROW_SE: 315.0,
}

# 8 handles: TL, TC, TR, ML, MR, BL, BC, BR
HANDLE_FX = [0.0, 0.5, 1.0, 0.0, 1.0, 0.0, 0.5, 1.0]
HANDLE_FY = [0.0, 0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0]
ANCHOR_HANDLE = [7, 6, 5, 4, 3, 2, 1, 0]  # opposite handle for each handle
HANDLE_SIZE = 10.0


class CanvasObject:
    """Base class for all objects placed on the canvas (document-space coordinates)."""

    DEFAULT_BASE_SIZE: float = 20.0  # Annotation size in PDF points

    def __init__(self, x: float, y: float, width: float, height: float, page: int = 0) -> None:
        self.x = x
        self.y = y
        self._base_width = float(width)
        self._base_height = float(height)
        self.scale: float = 1.0
        self.page: int = page
        self.color: QColor = QColor("#cc0000")

    @property
    def scaled_width(self) -> float:
        return self._base_width * self.scale

    @property
    def scaled_height(self) -> float:
        return self._base_height * self.scale

    def clamp_to_page(self, pw: float, ph: float) -> None:
        self.x = max(0.0, min(self.x, max(0.0, pw - self.scaled_width)))
        self.y = max(0.0, min(self.y, max(0.0, ph - self.scaled_height)))

    def draw_in_viewport(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        raise NotImplementedError

    def render_to_pil(self) -> Image.Image:
        """Return an RGBA PIL image at the current scaled size for compositing."""
        raise NotImplementedError

    def duplicate(self) -> "CanvasObject":
        raise NotImplementedError

    def handle_rects_viewport(self, vx: float, vy: float, vw: float, vh: float) -> list[QRectF]:
        hs = HANDLE_SIZE
        return [
            QRectF(vx + fx * vw - hs / 2, vy + fy * vh - hs / 2, hs, hs)
            for fx, fy in zip(HANDLE_FX, HANDLE_FY)
        ]

    def supports_free_resize(self) -> bool:
        return False

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

    def hit_test_handle(self, vx: float, vy: float, vw: float, vh: float, pt: QPointF) -> int:
        """Return handle index 0-7 if pt is over a handle, else -1."""
        for i, r in enumerate(self.handle_rects_viewport(vx, vy, vw, vh)):
            if r.contains(pt):
                return i
        return -1

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
            "page": self.page,
            "color": self.color.name(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanvasObject":
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

    def duplicate(self) -> "SignatureObject":
        obj = SignatureObject(self._image.copy(), self.path, self.x + 20, self.y + 20, self.page)
        obj.scale = self.scale
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
    def from_dict(cls, data: dict[str, Any]) -> "SignatureObject":
        """Deserialize object from a dictionary."""
        import base64
        from io import BytesIO
        img_data = base64.b64decode(data["image_data"])
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        obj = cls(img, data["path"], data["x"], data["y"], data["page"])
        obj._base_width = data["base_width"]
        obj._base_height = data["base_height"]
        obj.scale = data["scale"]
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
        font_size_px: int = DEFAULT_TEXT_FONT_PT,
        line_width_factor: float = DEFAULT_LINE_WIDTH_FACTOR,
    ) -> None:
        self._font_family = font_family
        self._font_size_px = font_size_px
        self._line_width_factor = line_width_factor
        if ann_type == AnnotationType.TEXT:
            # Text box: 180×36 points, scale for 300 DPI rendering
            super().__init__(x, y, 180.0 * DPI_SCALE, 36.0 * DPI_SCALE, page)
            self.ann_type = ann_type
            self.text = text
            self.fit_text_box()
        else:
            base = 2.0 * self.DEFAULT_BASE_SIZE if ann_type in ARROW_TYPES else self.DEFAULT_BASE_SIZE
            # Base sizes are in PDF points, scale for 300 DPI rendering
            super().__init__(x, y, base * DPI_SCALE, base * DPI_SCALE, page)
            self.ann_type = ann_type
            self.text = text
            self._natural_width = float(base * DPI_SCALE)
            self._natural_height = float(base * DPI_SCALE)

    def supports_free_resize(self) -> bool:
        return self.ann_type == AnnotationType.TEXT

    # ------------------------------------------------------------------ text fitting

    def _make_font(self) -> QFont:
        f = QFont(self._font_family)
        # Font size is stored in PDF points; scale to pixels for 300 DPI rendering
        f.setPixelSize(int(round(self._font_size_px * DPI_SCALE)))
        return f

    def fit_text_box(self) -> None:
        """Resize the bounding box so it exactly fits the current text at the set font size."""
        if self.ann_type != AnnotationType.TEXT:
            return
        fm = QFontMetricsF(self._make_font())
        lines = (self.text or "").split("\n")
        widest = 0.0
        for line in lines:
            widest = max(widest, fm.horizontalAdvance(line))
        line_h = fm.height()
        self._base_width = max(8.0, widest)
        self._base_height = max(8.0, line_h * len(lines))
        self._natural_width = self._base_width
        self._natural_height = self._base_height
        self.scale = 1.0

    # ------------------------------------------------------------------ drawing

    def draw_in_viewport(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_symbol(painter, vx, vy, vw, vh, doc_scale)
        painter.restore()

    def _pen(self, vw: float, vh: float) -> QPen:
        pen = QPen(self.color)
        pen.setWidthF(max(1.5, min(vw, vh) * self._line_width_factor))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def _draw_symbol(self, painter: QPainter, vx: float, vy: float, vw: float, vh: float, doc_scale: float = 1.0) -> None:
        m = min(vw, vh) * 0.12
        t = self.ann_type

        if t == AnnotationType.CHECKMARK:
            painter.setPen(self._pen(vw, vh))
            painter.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(vx + m, vy + vh * 0.55)
            path.lineTo(vx + vw * 0.38, vy + vh - m)
            path.lineTo(vx + vw - m, vy + m)
            painter.drawPath(path)

        elif t == AnnotationType.CROSSMARK:
            painter.setPen(self._pen(vw, vh))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(QPointF(vx + m, vy + m), QPointF(vx + vw - m, vy + vh - m))
            painter.drawLine(QPointF(vx + vw - m, vy + m), QPointF(vx + m, vy + vh - m))

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

        elif t in ARROW_TYPES:
            angle_rad = math.radians(ARROW_ANGLES[t])
            cx, cy = vx + vw / 2, vy + vh / 2
            shaft = min(vw, vh) * 0.33
            head = min(vw, vh) * 0.18
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            tip = QPointF(cx + cos_a * shaft, cy - sin_a * shaft)
            tail = QPointF(cx - cos_a * shaft, cy + sin_a * shaft)
            painter.setPen(self._pen(vw, vh))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(tail, tip)
            la = angle_rad + math.radians(145)
            ra = angle_rad - math.radians(145)
            poly = QPolygonF([
                tip,
                QPointF(tip.x() + math.cos(la) * head, tip.y() - math.sin(la) * head),
                QPointF(tip.x() + math.cos(ra) * head, tip.y() - math.sin(ra) * head),
            ])
            painter.setBrush(QBrush(self.color))
            painter.drawPolygon(poly)

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

    def duplicate(self) -> "VectorAnnotation":
        obj = VectorAnnotation(
            self.ann_type, self.x + 20, self.y + 20, self.page, self.text,
            font_family=self._font_family,
            font_size_px=self._font_size_px,
            line_width_factor=self._line_width_factor,
        )
        obj.scale = self.scale
        obj.color = QColor(self.color)
        return obj

    def to_dict(self) -> dict[str, Any]:
        """Serialize object to a dictionary."""
        data = super().to_dict()
        data["ann_type"] = self.ann_type.value
        data["text"] = self.text
        data["font_family"] = self._font_family
        data["font_size_px"] = self._font_size_px
        data["line_width_factor"] = self._line_width_factor
        data["natural_width"] = self._natural_width
        data["natural_height"] = self._natural_height
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorAnnotation":
        """Deserialize object from a dictionary."""
        ann_type = AnnotationType(data["ann_type"])
        obj = cls(
            ann_type,
            data["x"],
            data["y"],
            data["page"],
            data.get("text", ""),
            font_family=data.get("font_family", DEFAULT_FONT_FAMILY),
            font_size_px=data.get("font_size_px", DEFAULT_TEXT_FONT_PT),
            line_width_factor=data.get("line_width_factor", DEFAULT_LINE_WIDTH_FACTOR),
        )
        obj._base_width = data["base_width"]
        obj._base_height = data["base_height"]
        obj.scale = data["scale"]
        obj.color = QColor(data["color"])
        obj._natural_width = data.get("natural_width", obj._natural_width)
        obj._natural_height = data.get("natural_height", obj._natural_height)
        return obj
