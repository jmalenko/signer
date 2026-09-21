"""The "Prepare Signature" tool: turns a plain scan/photo into a transparent signature PNG.

See FUNCTIONAL_SPECIFICATION.md §17 for the full behavior spec. This dialog is standalone:
it doesn't read or modify the currently open document/canvas.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QRectF, QPointF, QSize, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QBrush, QColor, QPen, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .pdf_utils import render_all_pages
from .signature_background import (
    DEFAULT_COLOR_SOFTNESS,
    DEFAULT_COLOR_TOLERANCE,
    DEFAULT_INK_COLOR,
    DEFAULT_SOFTNESS,
    DEFAULT_THRESHOLD,
    RECOMMENDED_MAX_PT,
    RECOMMENDED_MIN_PT,
    auto_trim,
    fit_to_recommended_range,
    height_px_to_pt,
    remove_background,
    remove_background_by_color,
    resize_to_height_pt,
)

OPEN_FILTER = (
    "Images and PDF (*.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tif *.tiff *.pdf);;"
    "All files (*.*)"
)

_HANDLE_SIZE = 10
_HANDLE_HIT_MARGIN = 6


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def _checkerboard_pixmap(size, cell: int = 8) -> QPixmap:
    pixmap = QPixmap(size)
    painter = QPainter(pixmap)
    light = QColor(255, 255, 255)
    dark = QColor(205, 205, 205)
    for y in range(0, size.height(), cell):
        for x in range(0, size.width(), cell):
            color = dark if ((x // cell) + (y // cell)) % 2 else light
            painter.fillRect(x, y, cell, cell, color)
    painter.end()
    return pixmap


class _EyedropperDialog(QDialog):
    """Small modal that lets the user click a pixel on the crop to sample its ink color."""

    def __init__(self, image: Image.Image, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pick Ink Color")
        self._image = image.convert("RGB")
        self.picked_color: tuple[int, int, int] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Click on the ink to sample its color."))
        img_label = QLabel()
        img_label.setPixmap(pil_to_qpixmap(image))
        img_label.mousePressEvent = self._on_click  # type: ignore[method-assign]
        layout.addWidget(img_label)

    def _on_click(self, event: QMouseEvent) -> None:
        pos = event.position()
        x = max(0, min(self._image.width - 1, int(pos.x())))
        y = max(0, min(self._image.height - 1, int(pos.y())))
        self.picked_color = self._image.getpixel((x, y))
        self.accept()


class _DraggablePreviewLabel(QLabel):
    """A QLabel that reports click-drag deltas, used to pan the fixed-size Stage 3 preview.

    Resizing/redrawing the crop selection is intentionally not possible from here - the user
    must go back to Stage 2 for that; this widget only pans the (fixed-size) preview so an
    oversized crop can still be inspected in full.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pan_delta_callback = None
        self._drag_last_pos: QPointF | None = None
        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_last_pos = QPointF(event.position())
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_last_pos is None:
            return
        pos = QPointF(event.position())
        delta = pos - self._drag_last_pos
        self._drag_last_pos = pos
        if self.pan_delta_callback is not None:
            self.pan_delta_callback(delta.x(), delta.y())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_last_pos = None
        self.setCursor(Qt.OpenHandCursor)


class _CropWidget(QWidget):
    """Displays a scan at a given zoom level and lets the user drag out/adjust a crop rect."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: Image.Image | None = None
        self._pixmap: QPixmap | None = None
        self._zoom: float = 1.0
        self._rect: QRectF | None = None  # in image coordinates
        self._drag_mode: str | None = None
        self._drag_anchor: QPointF | None = None
        self._rect_at_drag_start: QRectF | None = None
        self._creating = False
        self._create_anchor: QPointF | None = None
        self._viewport_provider: QScrollArea | None = None
        self._auto_fit = True
        self.setMouseTracking(True)

    def set_viewport_provider(self, scroll_area: QScrollArea) -> None:
        """Register the QScrollArea this widget is displayed in, used to fit-to-window."""
        self._viewport_provider = scroll_area

    def set_image(self, image: Image.Image) -> None:
        self._image = image
        self._pixmap = pil_to_qpixmap(image)
        self._rect = None
        self.set_zoom(1.0)
        self._auto_fit = True

    def fit_to_view(self) -> None:
        """Fit the complete source image into the current Stage 2 viewport."""
        self._auto_fit = True
        self.set_zoom(self._fit_zoom())

    def _fit_zoom(self) -> float:
        if self._pixmap is None or self._pixmap.width() <= 0 or self._pixmap.height() <= 0:
            return 1.0
        if self._viewport_provider is not None:
            viewport = self._viewport_provider.viewport().size()
        else:
            viewport = self.size()
        scale_w = max(viewport.width() - 20, 100) / self._pixmap.width()
        scale_h = max(viewport.height() - 20, 100) / self._pixmap.height()
        return max(0.05, min(1.0, min(scale_w, scale_h)))

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.05, min(8.0, zoom))
        if self._pixmap is not None:
            self.setFixedSize(
                max(1, round(self._pixmap.width() * self._zoom)),
                max(1, round(self._pixmap.height() * self._zoom)),
            )
        self.update()

    def zoom_in(self) -> None:
        self._auto_fit = False
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self) -> None:
        self._auto_fit = False
        self.set_zoom(self._zoom / 1.25)


    def crop_rect(self) -> QRectF | None:
        return self._rect

    def has_selection(self) -> bool:
        return self._rect is not None and self._rect.width() >= 1 and self._rect.height() >= 1

    # -- coordinate helpers -------------------------------------------------

    def _to_image(self, widget_pos: QPointF) -> QPointF:
        return QPointF(widget_pos.x() / self._zoom, widget_pos.y() / self._zoom)

    def _to_widget(self, image_pos: QPointF) -> QPointF:
        return QPointF(image_pos.x() * self._zoom, image_pos.y() * self._zoom)

    def _handle_positions(self, rect: QRectF) -> dict[str, QPointF]:
        return {
            "tl": rect.topLeft(),
            "tm": QPointF(rect.center().x(), rect.top()),
            "tr": rect.topRight(),
            "ml": QPointF(rect.left(), rect.center().y()),
            "mr": QPointF(rect.right(), rect.center().y()),
            "bl": rect.bottomLeft(),
            "bm": QPointF(rect.center().x(), rect.bottom()),
            "br": rect.bottomRight(),
        }

    def _hit_test(self, widget_pos: QPointF) -> str | None:
        if self._rect is None:
            return None
        for name, image_pos in self._handle_positions(self._rect).items():
            widget_handle_pos = self._to_widget(image_pos)
            if (widget_handle_pos - widget_pos).manhattanLength() <= _HANDLE_SIZE / 2 + _HANDLE_HIT_MARGIN:
                return name
        if self._rect.contains(self._to_image(widget_pos)):
            return "move"
        return None

    # -- Qt events ------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        if self._pixmap is not None:
            painter.drawPixmap(self.rect(), self._pixmap, self._pixmap.rect())
        if self._rect is not None:
            widget_rect = QRectF(self._to_widget(self._rect.topLeft()), self._to_widget(self._rect.bottomRight()))
            pen = QPen(QColor("#1e88e5"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(widget_rect)
            handle_brush = QBrush(QColor("#1e88e5"))
            for image_pos in self._handle_positions(self._rect).values():
                pos = self._to_widget(image_pos)
                painter.fillRect(
                    QRectF(pos.x() - _HANDLE_SIZE / 2, pos.y() - _HANDLE_SIZE / 2, _HANDLE_SIZE, _HANDLE_SIZE),
                    handle_brush,
                )
        painter.end()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton or self._image is None:
            return
        pos = QPointF(event.position())
        hit = self._hit_test(pos)
        self._drag_anchor = pos
        self._rect_at_drag_start = QRectF(self._rect) if self._rect is not None else None
        if hit is None:
            self.begin_selection(self._to_image(pos))
        else:
            self._creating = False
            self._drag_mode = hit

    def begin_selection(self, image_pos: QPointF) -> None:
        """Start drawing a brand-new crop rectangle anchored at `image_pos`.

        The anchor is kept fixed for the whole drag (in `_create_anchor`), independent of
        `_rect` (which gets re-normalized on every move), so dragging from any corner
        towards any other corner always yields the correct rectangle.
        """
        self._drag_mode = "create"
        self._creating = True
        self._create_anchor = QPointF(image_pos)
        self._rect = QRectF(image_pos, image_pos)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_mode is None or self._image is None:
            hit = self._hit_test(QPointF(event.position()))
            self.setCursor(Qt.SizeAllCursor if hit == "move" else (Qt.PointingHandCursor if hit else Qt.ArrowCursor))
            return
        pos = QPointF(event.position())
        image_pos = self._to_image(pos)
        image_pos.setX(max(0.0, min(float(self._image.width), image_pos.x())))
        image_pos.setY(max(0.0, min(float(self._image.height), image_pos.y())))

        if self._drag_mode == "move" and self._rect_at_drag_start is not None and self._drag_anchor is not None:
            delta = self._to_image(pos) - self._to_image(self._drag_anchor)
            new_rect = QRectF(self._rect_at_drag_start)
            new_rect.translate(delta)
            self._rect = new_rect
        else:
            self.update_selection(image_pos)
        self.update()

    def update_selection(self, image_pos: QPointF) -> None:
        """Extend/resize the in-progress rectangle towards `image_pos` (image coords)."""
        if self._rect is None:
            return
        if self._creating and self._create_anchor is not None:
            self._rect = QRectF(self._create_anchor, image_pos).normalized()
            return
        rect = QRectF(self._rect)
        if "l" in self._drag_mode:
            rect.setLeft(image_pos.x())
        if "r" in self._drag_mode:
            rect.setRight(image_pos.x())
        if "t" in self._drag_mode:
            rect.setTop(image_pos.y())
        if "b" in self._drag_mode:
            rect.setBottom(image_pos.y())
        self._rect = rect.normalized()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_mode = None
        self._drag_anchor = None
        self._rect_at_drag_start = None
        self._creating = False
        if self._rect is not None:
            self._rect = self._rect.normalized()


class _CropScrollArea(QScrollArea):
    """Stage 2 viewport that refits only while the crop widget is auto-fitting."""

    def __init__(self, crop_widget: _CropWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._crop_widget = crop_widget

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if self._crop_widget._auto_fit:
            self._crop_widget.fit_to_view()


class PrepareSignatureDialog(QDialog):
    """Modal "Prepare Signature" tool (hamburger menu → Tools)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Prepare Signature")
        self.resize(900, 700)

        self._pages: list[Image.Image] = []
        self._page_index = 0
        self._crop_loaded_page_index: int | None = None
        self._source_path: Path | None = None
        self._final_image: Image.Image | None = None
        self._fit_to_range = True
        self._updating_height = False
        self._ink_color: tuple[int, int, int] = DEFAULT_INK_COLOR
        self._dirty = False
        self._preview_pan = QPointF(0, 0)
        self._last_full_size: tuple[int, int] | None = None
        self._last_preview_image: Image.Image | None = None
        self._last_boundary_bbox: tuple[int, int, int, int] | None = None
        self._manual_height_pt: float | None = None

        self._stack = QStackedWidget(self)
        self._build_stage1()
        self._build_stage2()
        self._build_stage3()

        layout = QVBoxLayout(self)
        layout.addWidget(self._stack)
        self._stack.setCurrentIndex(0)

    # ---------------------------------------------------------------- Stage 1

    def _build_stage1(self) -> None:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.addStretch(1)
        label = QLabel("Open a scan or photo of your signature (image or PDF).")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        open_btn = QPushButton("Open…")
        open_btn.clicked.connect(self._open_scan)
        open_row = QHBoxLayout()
        open_row.addStretch(1)
        open_row.addWidget(open_btn)
        open_row.addStretch(1)
        layout.addLayout(open_row)

        self._opened_file_label = QLabel("")
        self._opened_file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._opened_file_label)

        self._page_nav_row = QHBoxLayout()
        self._prev_page_btn = QPushButton("◀")
        self._prev_page_btn.clicked.connect(lambda: self._change_page(-1))
        self._page_label = QLabel("")
        self._page_label.setAlignment(Qt.AlignCenter)
        self._next_page_btn = QPushButton("▶")
        self._next_page_btn.clicked.connect(lambda: self._change_page(1))
        self._page_nav_row.addStretch(1)
        self._page_nav_row.addWidget(self._prev_page_btn)
        self._page_nav_row.addWidget(self._page_label)
        self._page_nav_row.addWidget(self._next_page_btn)
        self._page_nav_row.addStretch(1)
        layout.addLayout(self._page_nav_row)
        self._set_page_nav_visible(False)

        self._stage1_continue_btn = QPushButton("Continue")
        self._stage1_continue_btn.setEnabled(False)
        self._stage1_continue_btn.clicked.connect(self._go_to_crop)
        continue_row = QHBoxLayout()
        continue_row.addStretch(1)
        continue_row.addWidget(self._stage1_continue_btn)
        layout.addLayout(continue_row)
        layout.addStretch(1)

        self._stack.addWidget(page)

    def _set_page_nav_visible(self, visible: bool) -> None:
        self._prev_page_btn.setVisible(visible)
        self._page_label.setVisible(visible)
        self._next_page_btn.setVisible(visible)

    def _open_scan(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Scan", "", OPEN_FILTER)
        if not path:
            return
        try:
            pages = render_all_pages(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Cannot open file", f"Unable to open '{path}':\n{exc}")
            return
        if not pages:
            QMessageBox.critical(self, "Cannot open file", f"'{path}' has no pages to show.")
            return
        self._pages = pages
        self._page_index = 0
        self._source_path = Path(path)
        self._opened_file_label.setText(f"Opened: {self._source_path.name}")
        self._set_page_nav_visible(len(pages) > 1)
        self._update_page_label()
        self._stage1_continue_btn.setEnabled(True)
        self._dirty = True
        if len(pages) == 1:
            # No page to pick, so there's nothing for "Continue" to add - go straight to crop.
            self._go_to_crop()

    def _change_page(self, delta: int) -> None:
        if not self._pages:
            return
        self._page_index = max(0, min(len(self._pages) - 1, self._page_index + delta))
        self._update_page_label()

    def _update_page_label(self) -> None:
        if self._pages:
            self._page_label.setText(f"Page {self._page_index + 1} / {len(self._pages)}")

    def _go_to_crop(self) -> None:
        if not self._pages:
            return
        if self._crop_loaded_page_index != self._page_index:
            # Only reset zoom/selection when actually switching to a different page; going
            # back and forth (e.g. Stage 1 -> Continue again) keeps the previous selection.
            self._crop_widget.set_image(self._pages[self._page_index])
            self._crop_loaded_page_index = self._page_index
        self._stack.setCurrentIndex(1)

    # ---------------------------------------------------------------- Stage 2

    def _build_stage2(self) -> None:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        hint = QLabel(
            "Select the entire signature, including every stroke. "
            "This area will be processed in the next stage."
        )
        layout.addWidget(hint)

        zoom_row = QHBoxLayout()
        zoom_out_btn = QPushButton("−")
        zoom_in_btn = QPushButton("+")
        zoom_row.addStretch(1)
        zoom_row.addWidget(zoom_out_btn)
        zoom_row.addWidget(zoom_in_btn)
        layout.addLayout(zoom_row)

        self._crop_widget = _CropWidget()
        scroll = _CropScrollArea(self._crop_widget)
        scroll.setWidget(self._crop_widget)
        scroll.setWidgetResizable(False)
        self._crop_widget.set_viewport_provider(scroll)
        layout.addWidget(scroll, stretch=1)
        zoom_out_btn.clicked.connect(self._crop_widget.zoom_out)
        zoom_in_btn.clicked.connect(self._crop_widget.zoom_in)

        button_row = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self._go_to_tuning)
        button_row.addWidget(back_btn)
        button_row.addStretch(1)
        button_row.addWidget(next_btn)
        layout.addLayout(button_row)

        self._stack.addWidget(page)

    def _go_to_tuning(self) -> None:
        if not self._crop_widget.has_selection():
            QMessageBox.information(self, "No selection", "Draw a rectangle around the signature first.")
            return
        # Deliberately don't reset sliders/mode/pan here: re-entering Stage 3 (Back then Next
        # again) keeps whatever the user last set, instead of reverting to defaults.
        self._update_mode_visibility()
        self._stack.setCurrentIndex(2)
        self._update_preview()
        QTimer.singleShot(0, self._update_preview)

    # ---------------------------------------------------------------- Stage 3

    def _build_stage3(self) -> None:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        self._preview_label = _DraggablePreviewLabel()
        self._preview_label.pan_delta_callback = self._on_preview_dragged
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_scroll = QScrollArea()
        self._preview_scroll.setWidget(self._preview_label)
        self._preview_scroll.setWidgetResizable(False)
        self._preview_scroll.setMinimumHeight(200)
        layout.addWidget(self._preview_scroll, stretch=1)

        preview_controls_row = QHBoxLayout()
        preview_controls_row.addWidget(QLabel("Preview"))
        preview_controls_row.addSpacing(12)
        preview_controls_row.addWidget(QLabel("Background"))
        preview_controls_row.addSpacing(6)
        self._backdrop_combo = QComboBox()
        self._backdrop_combo.addItems(["Checkerboard", "White"])
        self._backdrop_combo.currentIndexChanged.connect(self._update_preview)
        preview_controls_row.addWidget(self._backdrop_combo)
        self._show_boundary_checkbox = QCheckBox(
            "Show actual signature boundary"
        )
        self._show_boundary_checkbox.setChecked(True)
        self._show_boundary_checkbox.toggled.connect(
            lambda _checked: self._update_preview()
        )
        preview_controls_row.addWidget(self._show_boundary_checkbox)
        preview_controls_row.addStretch(1)
        layout.addLayout(preview_controls_row)

        self._luminance_controls = QWidget()
        luminance_layout = QVBoxLayout(self._luminance_controls)
        luminance_layout.setContentsMargins(0, 0, 0, 0)

        self._luminance_method_checkbox = QCheckBox(
            "Method 1: Luminance background removal"
        )
        self._luminance_method_checkbox.setChecked(True)
        self._luminance_method_checkbox.toggled.connect(self._on_methods_changed)
        layout.addWidget(self._luminance_method_checkbox)

        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Threshold:"))
        self._threshold_slider = QSlider(Qt.Horizontal)
        self._threshold_slider.setRange(0, 255)
        self._threshold_slider.setValue(int(DEFAULT_THRESHOLD))
        self._threshold_slider.valueChanged.connect(self._update_preview)
        threshold_row.addWidget(self._threshold_slider)
        luminance_layout.addLayout(threshold_row)

        softness_row = QHBoxLayout()
        softness_row.addWidget(QLabel("Softness:"))
        self._softness_slider = QSlider(Qt.Horizontal)
        self._softness_slider.setRange(1, 255)
        self._softness_slider.setValue(int(DEFAULT_SOFTNESS))
        self._softness_slider.valueChanged.connect(self._update_preview)
        softness_row.addWidget(self._softness_slider)
        luminance_layout.addLayout(softness_row)
        layout.addWidget(self._luminance_controls)

        self._color_controls = QWidget()
        color_layout = QVBoxLayout(self._color_controls)
        color_layout.setContentsMargins(0, 0, 0, 0)

        self._color_method_checkbox = QCheckBox("Method 2: Keep ink color")
        self._color_method_checkbox.setChecked(True)
        self._color_method_checkbox.toggled.connect(self._on_methods_changed)
        layout.addWidget(self._color_method_checkbox)

        color_pick_row = QHBoxLayout()
        color_pick_row.addWidget(QLabel("Ink color:"))
        self._color_swatch_btn = QPushButton()
        self._color_swatch_btn.setFixedWidth(40)
        self._color_swatch_btn.clicked.connect(self._pick_ink_color)
        color_pick_row.addWidget(self._color_swatch_btn)
        eyedropper_btn = QPushButton("Pick from image…")
        eyedropper_btn.clicked.connect(self._pick_ink_color_from_image)
        color_pick_row.addWidget(eyedropper_btn)
        color_pick_row.addStretch(1)
        color_layout.addLayout(color_pick_row)

        tolerance_row = QHBoxLayout()
        tolerance_row.addWidget(QLabel("Color tolerance:"))
        self._color_tolerance_slider = QSlider(Qt.Horizontal)
        self._color_tolerance_slider.setRange(1, 180)
        self._color_tolerance_slider.setValue(int(DEFAULT_COLOR_TOLERANCE))
        self._color_tolerance_slider.valueChanged.connect(self._update_preview)
        tolerance_row.addWidget(self._color_tolerance_slider)
        color_layout.addLayout(tolerance_row)

        color_softness_row = QHBoxLayout()
        color_softness_row.addWidget(QLabel("Softness:"))
        self._color_softness_slider = QSlider(Qt.Horizontal)
        self._color_softness_slider.setRange(1, 180)
        self._color_softness_slider.setValue(int(DEFAULT_COLOR_SOFTNESS))
        self._color_softness_slider.valueChanged.connect(self._update_preview)
        color_softness_row.addWidget(self._color_softness_slider)
        color_layout.addLayout(color_softness_row)
        layout.addWidget(self._color_controls)
        self._update_ink_color_swatch()
        self._update_mode_visibility()

        size_row = QHBoxLayout()
        self._fit_range_checkbox = QCheckBox(
            "Scale signature to fit recommended range (10-24pt)"
        )
        self._fit_range_checkbox.setChecked(True)
        self._fit_range_checkbox.toggled.connect(self._on_fit_range_toggled)
        size_row.addWidget(self._fit_range_checkbox)
        size_row.addStretch(1)
        self._scale_status_label = QLabel("")
        size_row.addWidget(self._scale_status_label)
        self._height_label = QLabel("Height (pt):")
        size_row.addWidget(self._height_label)
        self._height_spin = QDoubleSpinBox()
        self._height_spin.setRange(1.0, 500.0)
        self._height_spin.setDecimals(1)
        self._height_spin.valueChanged.connect(self._on_height_changed)
        size_row.addWidget(self._height_spin)
        self._size_warning_label = QLabel("")
        self._size_warning_label.setStyleSheet("color: #b45309;")
        size_row.addWidget(self._size_warning_label)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_sliders)
        size_row.addWidget(reset_btn)
        layout.addLayout(size_row)
        self._update_height_control_visibility()

        button_row = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        save_btn = QPushButton("Save As…")
        save_btn.clicked.connect(self._save)
        button_row.addWidget(back_btn)
        button_row.addStretch(1)
        button_row.addWidget(save_btn)
        layout.addLayout(button_row)

        self._stack.addWidget(page)

    def _reset_sliders(self) -> None:
        self._threshold_slider.setValue(int(DEFAULT_THRESHOLD))
        self._softness_slider.setValue(int(DEFAULT_SOFTNESS))
        self._color_tolerance_slider.setValue(int(DEFAULT_COLOR_TOLERANCE))
        self._color_softness_slider.setValue(int(DEFAULT_COLOR_SOFTNESS))

    def _on_height_changed(self, _value: float) -> None:
        if self._updating_height:
            return
        self._manual_height_pt = self._height_spin.value()
        self._fit_range_checkbox.setChecked(False)
        self._update_preview(resize_from_height_field=True)

    def _on_fit_range_toggled(self, checked: bool) -> None:
        self._fit_to_range = checked
        if not checked and self._manual_height_pt is None:
            self._manual_height_pt = self._current_actual_height_pt()
            self._updating_height = True
            self._height_spin.setValue(round(self._manual_height_pt, 1))
            self._updating_height = False
        self._update_height_control_visibility()
        self._update_preview()

    def _update_height_control_visibility(self) -> None:
        scaled = self._fit_range_checkbox.isChecked()
        self._scale_status_label.setVisible(scaled)
        self._height_label.setVisible(not scaled)
        self._height_spin.setVisible(not scaled)
        self._size_warning_label.setVisible(not scaled)

    def _current_actual_height_pt(self) -> float:
        full = self._compute_processed_image()
        if full is None:
            return 0.0
        return height_px_to_pt(auto_trim(full).height)

    def _on_methods_changed(self, _checked: bool) -> None:
        self._update_mode_visibility()
        self._update_preview()

    def _update_mode_visibility(self) -> None:
        self._luminance_controls.setEnabled(
            self._luminance_method_checkbox.isChecked()
        )
        self._color_controls.setEnabled(self._color_method_checkbox.isChecked())

    def _update_ink_color_swatch(self) -> None:
        color = QColor(*self._ink_color)
        self._color_swatch_btn.setStyleSheet(f"background-color: {color.name()};")

    def _pick_ink_color(self) -> None:
        color = QColorDialog.getColor(QColor(*self._ink_color), self, "Pick Ink Color")
        if not color.isValid():
            return
        self._ink_color = (color.red(), color.green(), color.blue())
        self._update_ink_color_swatch()
        self._update_preview()

    def _pick_ink_color_from_image(self) -> None:
        cropped = self._cropped_source()
        if cropped is None:
            return
        picker = _EyedropperDialog(cropped, self)
        picker.exec()
        if picker.picked_color is not None:
            self._ink_color = picker.picked_color
            self._update_ink_color_swatch()
            self._update_preview()

    def _cropped_source(self) -> Image.Image | None:
        """Return the raw (pre-background-removal) crop, or None if there's no selection."""
        rect = self._crop_widget.crop_rect()
        if rect is None or self._crop_widget._image is None:
            return None
        image = self._crop_widget._image
        box = (
            max(0, int(rect.left())),
            max(0, int(rect.top())),
            min(image.width, int(round(rect.right()))),
            min(image.height, int(round(rect.bottom()))),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        return image.crop(box)

    def _compute_processed_image(self) -> Image.Image | None:
        """Return the background-removed image at the full user-drawn crop size (untrimmed).

        This is what Stage 3 displays: the crop rectangle's extent stays fixed for the whole
        stage regardless of slider/mode changes, so the preview never resizes/jumps. The tight
        "actual signature" boundary (used for saving and the height field) is computed
        separately in `_update_preview` via `auto_trim`.
        """
        cropped = self._cropped_source()
        if cropped is None:
            return None
        processed = cropped.convert("RGBA")
        if self._luminance_method_checkbox.isChecked():
            processed = remove_background(
                processed,
                self._threshold_slider.value(),
                self._softness_slider.value(),
            )
        if self._color_method_checkbox.isChecked():
            processed = remove_background_by_color(
                processed,
                self._ink_color,
                self._color_tolerance_slider.value(),
                self._color_softness_slider.value(),
            )
        return processed

    def _update_preview(self, *_args, resize_from_height_field: bool = False) -> None:
        full = self._compute_processed_image()
        if full is None:
            return
        trimmed = auto_trim(full)

        if self._fit_to_range:
            final = fit_to_recommended_range(trimmed)
        else:
            target_height = self._manual_height_pt
            if target_height is None:
                target_height = height_px_to_pt(trimmed.height)
            final = resize_to_height_pt(trimmed, target_height)

        self._final_image = final

        current_pt = height_px_to_pt(final.height)
        if self._fit_to_range or self._manual_height_pt is None:
            self._updating_height = True
            self._height_spin.setValue(round(current_pt, 1))
            self._updating_height = False

        actual_pt = height_px_to_pt(trimmed.height)
        if self._fit_to_range:
            if actual_pt < RECOMMENDED_MIN_PT:
                target_pt = RECOMMENDED_MIN_PT
            elif actual_pt > RECOMMENDED_MAX_PT:
                target_pt = RECOMMENDED_MAX_PT
            else:
                target_pt = round(actual_pt)
            target_text = f"{target_pt:g}"
            actual_text = f"{actual_pt:g}"
            self._scale_status_label.setText(
                f"Will be scaled to {target_text}pt from the current {actual_text}pt"
            )
        self._update_height_control_visibility()

        if current_pt < RECOMMENDED_MIN_PT or current_pt > RECOMMENDED_MAX_PT:
            self._size_warning_label.setText(
                f"Outside recommended {RECOMMENDED_MIN_PT:.0f}\u2013{RECOMMENDED_MAX_PT:.0f}pt range"
            )
        else:
            self._size_warning_label.setText("")

        boundary_bbox = full.split()[3].getbbox() if self._show_boundary_checkbox.isChecked() else None
        if full.size != self._last_full_size:
            # A genuinely different crop (new selection/page) - re-center the pan.
            self._preview_pan = QPointF(0, 0)
            self._last_full_size = full.size
        self._last_preview_image = full
        self._last_boundary_bbox = boundary_bbox
        self._render_preview(full, boundary_bbox)

    def _on_preview_dragged(self, dx: float, dy: float) -> None:
        self._preview_pan += QPointF(dx, dy)
        if self._last_preview_image is not None:
            self._render_preview(self._last_preview_image, self._last_boundary_bbox)

    def _render_preview(self, image: Image.Image, boundary_bbox: tuple[int, int, int, int] | None = None) -> None:
        viewport = self._preview_scroll.viewport().size()
        canvas_w = max(viewport.width(), 1)
        canvas_h = max(viewport.height(), 1)
        if self._backdrop_combo.currentText() == "White":
            backdrop = QPixmap(canvas_w, canvas_h)
            backdrop.fill(Qt.white)
        else:
            backdrop = _checkerboard_pixmap(QSize(canvas_w, canvas_h))

        display_scale = min(
            1.0,
            viewport.width() / image.width if image.width else 1.0,
            viewport.height() / image.height if image.height else 1.0,
        )
        display_width = max(1, round(image.width * display_scale))
        display_height = max(1, round(image.height * display_scale))
        display_image = image.resize(
            (display_width, display_height), Image.Resampling.LANCZOS
        )
        display_bbox = None
        if boundary_bbox is not None:
            display_bbox = tuple(
                round(value * display_scale) for value in boundary_bbox
            )
        x = (canvas_w - display_width) // 2 + round(self._preview_pan.x())
        y = (canvas_h - display_height) // 2 + round(self._preview_pan.y())
        painter = QPainter(backdrop)
        painter.drawPixmap(x, y, pil_to_qpixmap(display_image))
        if display_bbox is not None:
            left, top, right, bottom = display_bbox
            pen = QPen(QColor("#e53935"))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(x + left, y + top, right - left, bottom - top)
        painter.end()
        self._preview_label.setFixedSize(canvas_w, canvas_h)
        self._preview_label.setPixmap(backdrop)

    # ---------------------------------------------------------------- Save

    def _save(self) -> None:
        if self._final_image is None:
            return
        default_dir = str(self._source_path.parent) if self._source_path else ""
        default_path = str(Path(default_dir) / "signature.png") if default_dir else "signature.png"
        path, _ = QFileDialog.getSaveFileName(self, "Save Signature", default_path, "PNG files (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            self._final_image.save(path, format="PNG")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", f"Unable to save '{path}':\n{exc}")
            return
        self._dirty = False

    # ---------------------------------------------------------------- Close

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Discard signature?",
                "You have not saved the prepared signature. Close anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
