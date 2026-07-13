from __future__ import annotations

from dataclasses import dataclass

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget


@dataclass(slots=True)
class SignatureState:
    path: str | None = None
    image: Image.Image | None = None
    scale: float = 1.0
    x: float = 0.0
    y: float = 0.0


class DocumentCanvas(QWidget):
    signatureChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)

        self._doc_image: Image.Image | None = None
        self._doc_pixmap: QPixmap | None = None
        self._signature = SignatureState()
        self._signature_pixmap_cache: QPixmap | None = None
        self._signature_cache_scale: float | None = None

        self._fit_scale: float = 1.0
        self._doc_offset_x: float = 0.0
        self._doc_offset_y: float = 0.0

        self._dragging = False
        self._drag_offset_x = 0.0
        self._drag_offset_y = 0.0

    @property
    def has_document(self) -> bool:
        return self._doc_image is not None

    @property
    def has_signature(self) -> bool:
        return self._signature.image is not None

    @property
    def document_size(self) -> tuple[int, int] | None:
        if self._doc_image is None:
            return None
        return self._doc_image.size

    @property
    def document_image(self) -> Image.Image | None:
        return self._doc_image

    def set_document_image(self, image: Image.Image) -> None:
        self._doc_image = image.convert("RGB")
        self._doc_pixmap = self._pil_to_qpixmap(self._doc_image)
        self._recompute_fit()

        if self.has_signature:
            self.reset_signature_default_position()

        self.update()

    def set_signature_image(self, image: Image.Image, path: str | None = None) -> None:
        self._signature.image = image.convert("RGBA")
        self._signature.path = path
        self._signature.scale = 1.0
        self._signature_pixmap_cache = None
        self._signature_cache_scale = None

        if self.has_document:
            self.reset_signature_default_position()

        self.signatureChanged.emit()
        self.update()

    def set_signature_scale(self, scale: float) -> None:
        if not self.has_signature:
            return
        scale = max(0.2, min(3.0, scale))
        if abs(scale - self._signature.scale) < 1e-6:
            return

        old_w, old_h = self.signature_size_doc()
        cx = self._signature.x + old_w / 2
        cy = self._signature.y + old_h / 2

        self._signature.scale = scale
        self._signature_pixmap_cache = None
        self._signature_cache_scale = None

        new_w, new_h = self.signature_size_doc()
        self._signature.x = cx - new_w / 2
        self._signature.y = cy - new_h / 2
        self._clamp_signature_position()
        self.signatureChanged.emit()
        self.update()

    def signature_scale(self) -> float:
        return self._signature.scale

    def signature_size_doc(self) -> tuple[float, float]:
        if not self.has_signature or self._signature.image is None:
            return 0.0, 0.0
        w, h = self._signature.image.size
        return w * self._signature.scale, h * self._signature.scale

    def signature_state_for_save(self) -> tuple[Image.Image, float, float, float] | None:
        if not self.has_signature or self._signature.image is None:
            return None
        return self._signature.image, self._signature.x, self._signature.y, self._signature.scale

    def signature_info(self) -> tuple[float, float, float, float, float] | None:
        if not self.has_signature:
            return None
        w, h = self.signature_size_doc()
        return self._signature.x, self._signature.y, w, h, self._signature.scale

    def reset_signature_default_position(self) -> None:
        if not self.has_document or not self.has_signature:
            return
        doc_w, doc_h = self._doc_image.size  # type: ignore[union-attr]
        sig_w, sig_h = self.signature_size_doc()
        self._signature.x = (doc_w - sig_w) / 2
        self._signature.y = 0.8 * doc_h - sig_h / 2
        self._clamp_signature_position()
        self.signatureChanged.emit()
        self.update()

    def _clamp_signature_position(self) -> None:
        if not self.has_document or not self.has_signature:
            return
        doc_w, doc_h = self._doc_image.size  # type: ignore[union-attr]
        sig_w, sig_h = self.signature_size_doc()

        max_x = max(0.0, doc_w - sig_w)
        max_y = max(0.0, doc_h - sig_h)
        self._signature.x = max(0.0, min(self._signature.x, max_x))
        self._signature.y = max(0.0, min(self._signature.y, max_y))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._recompute_fit()

    def _recompute_fit(self) -> None:
        if self._doc_image is None:
            self._fit_scale = 1.0
            self._doc_offset_x = 0.0
            self._doc_offset_y = 0.0
            return

        doc_w, doc_h = self._doc_image.size
        if doc_w <= 0 or doc_h <= 0:
            self._fit_scale = 1.0
            self._doc_offset_x = 0.0
            self._doc_offset_y = 0.0
            return

        viewport_w = max(1, self.width())
        viewport_h = max(1, self.height())
        self._fit_scale = min(viewport_w / doc_w, viewport_h / doc_h)

        draw_w = doc_w * self._fit_scale
        draw_h = doc_h * self._fit_scale
        self._doc_offset_x = (viewport_w - draw_w) / 2
        self._doc_offset_y = (viewport_h - draw_h) / 2

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2f2f2f"))

        if self._doc_pixmap is None or self._doc_image is None:
            return

        doc_w, doc_h = self._doc_image.size
        target = QRectF(
            self._doc_offset_x,
            self._doc_offset_y,
            doc_w * self._fit_scale,
            doc_h * self._fit_scale,
        )
        painter.drawPixmap(target, self._doc_pixmap, QRectF(0, 0, self._doc_pixmap.width(), self._doc_pixmap.height()))

        if self.has_signature:
            sig_pm = self._signature_pixmap()
            sig_w_doc, sig_h_doc = self.signature_size_doc()
            x = self._doc_offset_x + self._signature.x * self._fit_scale
            y = self._doc_offset_y + self._signature.y * self._fit_scale
            w = sig_w_doc * self._fit_scale
            h = sig_h_doc * self._fit_scale
            rect = QRectF(x, y, w, h)
            painter.drawPixmap(rect, sig_pm, QRectF(0, 0, sig_pm.width(), sig_pm.height()))
            painter.setPen(QColor("#00a2ff"))
            painter.drawRect(rect)

    def _signature_pixmap(self) -> QPixmap:
        assert self._signature.image is not None
        if self._signature_pixmap_cache is not None and self._signature_cache_scale == self._signature.scale:
            return self._signature_pixmap_cache

        base = self._signature.image
        w = max(1, int(round(base.width * self._signature.scale)))
        h = max(1, int(round(base.height * self._signature.scale)))
        resized = base.resize((w, h), Image.Resampling.LANCZOS)

        pm = self._pil_to_qpixmap(resized)
        self._signature_pixmap_cache = pm
        self._signature_cache_scale = self._signature.scale
        return pm

    def _view_to_doc(self, pt: QPointF) -> tuple[float, float]:
        x = (pt.x() - self._doc_offset_x) / self._fit_scale
        y = (pt.y() - self._doc_offset_y) / self._fit_scale
        return x, y

    def _signature_rect_view(self) -> QRectF | None:
        if not self.has_signature:
            return None
        sig_w_doc, sig_h_doc = self.signature_size_doc()
        x = self._doc_offset_x + self._signature.x * self._fit_scale
        y = self._doc_offset_y + self._signature.y * self._fit_scale
        return QRectF(x, y, sig_w_doc * self._fit_scale, sig_h_doc * self._fit_scale)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.LeftButton or not self.has_signature or not self.has_document:
            return

        rect = self._signature_rect_view()
        if rect is None or not rect.contains(event.position()):
            return

        doc_x, doc_y = self._view_to_doc(event.position())
        self._drag_offset_x = doc_x - self._signature.x
        self._drag_offset_y = doc_y - self._signature.y
        self._dragging = True

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._dragging:
            return

        doc_x, doc_y = self._view_to_doc(event.position())
        self._signature.x = doc_x - self._drag_offset_x
        self._signature.y = doc_y - self._drag_offset_y
        self._clamp_signature_position()
        self.signatureChanged.emit()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        if not self.has_signature:
            return

        # Ctrl + wheel adjusts signature scale.
        if event.modifiers() & Qt.ControlModifier:
            delta_steps = event.angleDelta().y() / 120.0
            next_scale = self._signature.scale * (1.0 + 0.08 * delta_steps)
            self.set_signature_scale(next_scale)
            event.accept()
            return

        super().wheelEvent(event)

    @staticmethod
    def _pil_to_qpixmap(image: Image.Image) -> QPixmap:
        qimage = ImageQt(image)
        return QPixmap.fromImage(qimage)
