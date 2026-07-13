from __future__ import annotations

import locale
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolBar,
    QToolButton,
)

from .canvas import DocumentCanvas
from .compositor import build_default_output_path, composite_objects_to_jpg
from .objects import AnnotationType, SignatureObject, VectorAnnotation
from .pdf_utils import render_all_pages
from .settings import AppSettings, SettingsStore

SUPPORTED_SIGNATURE_EXT = {".png", ".jpg", ".jpeg"}
ARROW_DIRECTIONS = [
    ("North", AnnotationType.ARROW_N),
    ("North-East", AnnotationType.ARROW_NE),
    ("East", AnnotationType.ARROW_E),
    ("South-East", AnnotationType.ARROW_SE),
    ("South", AnnotationType.ARROW_S),
    ("South-West", AnnotationType.ARROW_SW),
    ("West", AnnotationType.ARROW_W),
    ("North-West", AnnotationType.ARROW_NW),
]


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("Signer")
        self.resize(1280, 900)

        self._settings_store = settings_store
        self._settings = settings
        self._current_color = QColor("#cc0000")
        self._sig_ann_menu: QMenu | None = None

        self.document_path: str | None = None

        self.canvas = DocumentCanvas(self)
        self.setCentralWidget(self.canvas)

        self._build_toolbar()
        self._build_statusbar()

        self.canvas.objectChanged.connect(self._on_object_changed)
        self.canvas.pageChanged.connect(self._on_page_changed)
        self.canvas.editRequested.connect(self._on_edit_requested)

    def run_startup_load(self, document: str | None, signature: str | None) -> None:
        def _load() -> None:
            if document:
                self.open_document(document)
            if signature:
                self._load_signature_file(signature, at_default_position=True)
            elif self._settings.last_signature_path:
                self._load_signature_file(self._settings.last_signature_path, at_default_position=True)
        QTimer.singleShot(0, _load)

    # ---------------------------------------------------------------- toolbar

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        tb.setIconSize(QSize(24, 24))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def big_action(text: str, slot) -> QAction:
            act = QAction(text, self)
            act.triggered.connect(slot)
            tb.addAction(act)
            return act

        big_action("📂 Open Document", lambda: self.open_document())
        big_action("✍ Open Signature", lambda: self.open_signature())
        tb.addSeparator()

        # Page navigation
        big_action("◀ Prev", lambda: self.canvas.goto_page(self.canvas.current_page - 1))
        self.page_label = QLabel("  Page — / —  ")
        tb.addWidget(self.page_label)
        big_action("Next ▶", lambda: self.canvas.goto_page(self.canvas.current_page + 1))
        tb.addSeparator()

        # Annotation picker
        ann_btn = QToolButton(self)
        ann_btn.setText("➕ Add Annotation")
        ann_btn.setPopupMode(QToolButton.MenuButtonPopup)
        ann_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        ann_menu = QMenu(ann_btn)

        ann_menu.addAction("✔ Checkmark", lambda: self._add_vector(AnnotationType.CHECKMARK))
        ann_menu.addAction("✖ Cross", lambda: self._add_vector(AnnotationType.CROSS))

        arrow_menu = ann_menu.addMenu("➡ Arrow")
        for name, atype in ARROW_DIRECTIONS:
            arrow_menu.addAction(name, lambda checked=False, t=atype: self._add_vector(t))

        text_menu = ann_menu.addMenu("📝 Text")
        text_menu.addAction("Free text…", lambda: self._add_text_annotation(""))
        text_menu.addAction("Current date", lambda: self._add_text_annotation(self._locale_date()))
        text_menu.addAction("Current time", lambda: self._add_text_annotation(self._locale_time()))
        text_menu.addAction("Current date & time", lambda: self._add_text_annotation(self._locale_datetime()))

        self._sig_ann_menu = ann_menu.addMenu("🖊 Signature")
        self._rebuild_sig_ann_menu()

        ann_btn.setMenu(ann_menu)
        ann_btn.clicked.connect(ann_menu.exec_)
        tb.addWidget(ann_btn)

        tb.addSeparator()

        big_action("❏ Duplicate", lambda: self.canvas.duplicate_selected())
        big_action("🗑 Delete", lambda: self.canvas.remove_selected())

        tb.addSeparator()

        # Color button
        self._color_btn = QPushButton("●")
        self._color_btn.setFixedSize(38, 38)
        self._color_btn.setToolTip("Annotation color")
        self._color_btn.clicked.connect(self._pick_color)
        self._update_color_btn()
        tb.addWidget(self._color_btn)

        tb.addSeparator()
        big_action("💾 Save JPG", self.save_signed_document)

    def _rebuild_sig_ann_menu(self) -> None:
        if self._sig_ann_menu is None:
            return
        self._sig_ann_menu.clear()
        self._sig_ann_menu.addAction("From file…", self._add_signature_from_file)
        paths = self._settings.recent_signature_paths
        if paths:
            self._sig_ann_menu.addSeparator()
            for p in paths:
                self._sig_ann_menu.addAction(
                    Path(p).name,
                    lambda checked=False, path=p: self._load_signature_file(path, at_default_position=False),
                )

    # ---------------------------------------------------------------- statusbar

    def _build_statusbar(self) -> None:
        self.doc_status = QLabel("Document: (none)")
        self.obj_status = QLabel("No object selected")
        self.statusBar().addWidget(self.doc_status, 2)
        self.statusBar().addPermanentWidget(self.obj_status)

    def _on_object_changed(self) -> None:
        obj = self.canvas.selected
        if obj is None:
            self.obj_status.setText("No object selected")
        else:
            sw = int(round(obj.scaled_width))
            sh = int(round(obj.scaled_height))
            x = int(round(obj.x))
            y = int(round(obj.y))
            self.obj_status.setText(f"x={x} y={y}  {sw}×{sh} px")

    def _on_page_changed(self, current: int, total: int) -> None:
        if total > 0:
            self.page_label.setText(f"  Page {current + 1} / {total}  ")
        else:
            self.page_label.setText("  Page — / —  ")

    def _on_edit_requested(self, obj: object) -> None:
        from .objects import CanvasObject, VectorAnnotation
        if not isinstance(obj, CanvasObject):
            return
        if isinstance(obj, VectorAnnotation) and obj.ann_type == AnnotationType.TEXT:
            new_text, ok = QInputDialog.getText(self, "Edit Text", "Text:", text=obj.text)
            if ok:
                obj.text = new_text
                self.canvas.update()
        color = QColorDialog.getColor(obj.color, self, "Object color")
        if color.isValid():
            obj.color = color
            self.canvas.update()

    # ---------------------------------------------------------------- color

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._current_color, self, "Annotation color")
        if color.isValid():
            self._current_color = color
            self._update_color_btn()

    def _update_color_btn(self) -> None:
        c = self._current_color.name()
        self._color_btn.setStyleSheet(f"background-color: {c}; color: {'#fff' if self._current_color.lightness() < 128 else '#000'};")

    # ---------------------------------------------------------------- date/time helpers

    @staticmethod
    def _locale_date() -> str:
        try:
            locale.setlocale(locale.LC_TIME, "")
        except Exception:
            pass
        return datetime.now().strftime("%x")

    @staticmethod
    def _locale_time() -> str:
        try:
            locale.setlocale(locale.LC_TIME, "")
        except Exception:
            pass
        return datetime.now().strftime("%X")

    @staticmethod
    def _locale_datetime() -> str:
        try:
            locale.setlocale(locale.LC_TIME, "")
        except Exception:
            pass
        return datetime.now().strftime("%x %X")

    # ---------------------------------------------------------------- annotation actions

    def _add_vector(self, ann_type: AnnotationType) -> None:
        if not self.canvas.has_document:
            QMessageBox.warning(self, "No document", "Open a document first.")
            return
        obj = VectorAnnotation(ann_type, 0, 0, self.canvas.current_page)
        obj.color = QColor(self._current_color)
        x, y = self.canvas.default_position_for(obj)
        obj.x, obj.y = x, y
        self.canvas.add_object(obj)

    def _add_text_annotation(self, preset_text: str) -> None:
        if not self.canvas.has_document:
            QMessageBox.warning(self, "No document", "Open a document first.")
            return
        if preset_text == "":
            text, ok = QInputDialog.getText(self, "Text Annotation", "Enter text:")
            if not ok or not text.strip():
                return
            preset_text = text.strip()
        obj = VectorAnnotation(AnnotationType.TEXT, 0, 0, self.canvas.current_page, preset_text)
        obj.color = QColor(self._current_color)
        x, y = self.canvas.default_position_for(obj)
        obj.x, obj.y = x, y
        self.canvas.add_object(obj)

    def _add_signature_from_file(self) -> None:
        start_dir = ""
        if self._settings.recent_signature_paths:
            start_dir = str(Path(self._settings.recent_signature_paths[0]).parent)
        elif self._settings.last_open_document_path:
            start_dir = str(Path(self._settings.last_open_document_path).parent)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Signature", start_dir,
            "Image files (*.png *.jpg *.jpeg);;All files (*.*)",
        )
        if path:
            self._load_signature_file(path, at_default_position=False)

    # ---------------------------------------------------------------- open/save

    def open_document(self, path: str | None = None) -> bool:
        chosen = path
        if not chosen:
            start_dir = ""
            if self.document_path:
                start_dir = str(Path(self.document_path).parent)
            elif self._settings.last_open_document_path:
                start_dir = str(Path(self._settings.last_open_document_path).parent)
            chosen, _ = QFileDialog.getOpenFileName(self, "Open Document", start_dir, "PDF files (*.pdf)")

        if not chosen:
            return False
        p = Path(chosen)
        if p.suffix.lower() != ".pdf":
            QMessageBox.warning(self, "Invalid document", "Document must be a .pdf file.")
            return False

        try:
            pages = render_all_pages(p, dpi=300)
        except Exception as exc:
            QMessageBox.critical(self, "Open document failed", f"Could not open PDF:\n{exc}")
            return False

        self.canvas.set_pages(pages)
        self.document_path = str(p)
        self._settings.last_open_document_path = str(p)
        self._save_settings_safe()
        self.doc_status.setText(f"Document: {p.name}")
        self._update_title()
        return True

    def open_signature(self, path: str | None = None) -> bool:
        """Load a signature and place it at the default position on the current page."""
        chosen = path
        if not chosen:
            start_dir = ""
            if self._settings.recent_signature_paths:
                start_dir = str(Path(self._settings.recent_signature_paths[0]).parent)
            elif self._settings.last_open_document_path:
                start_dir = str(Path(self._settings.last_open_document_path).parent)
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Open Signature", start_dir,
                "Image files (*.png *.jpg *.jpeg);;All files (*.*)",
            )
        if not chosen:
            return False
        return self._load_signature_file(chosen, at_default_position=True)

    def _load_signature_file(self, path: str, at_default_position: bool) -> bool:
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix == ".xcf":
            QMessageBox.warning(
                self, "Unsupported format",
                "GIMP .xcf files are not supported. Export the signature to .png or .jpg first.",
            )
            return False
        if suffix not in SUPPORTED_SIGNATURE_EXT:
            QMessageBox.warning(self, "Invalid signature", "Signature must be .png, .jpg, or .jpeg.")
            return False
        if not p.exists():
            QMessageBox.warning(self, "File not found", f"Signature file not found:\n{p}")
            return False
        try:
            with Image.open(p) as img:
                loaded = img.convert("RGBA")
        except (UnidentifiedImageError, OSError) as exc:
            QMessageBox.critical(self, "Open signature failed", f"Could not open signature:\n{exc}")
            return False

        obj = SignatureObject(loaded, str(p), 0, 0, self.canvas.current_page)
        if at_default_position or not self.canvas.has_document:
            x, y = self.canvas.default_position_for(obj)
        else:
            x, y = self.canvas.default_position_for(obj)
        obj.x, obj.y = x, y

        if self.canvas.has_document:
            self.canvas.add_object(obj)

        self._settings.last_signature_path = str(p)
        self._update_recent_signatures(str(p))
        self._save_settings_safe()
        self._rebuild_sig_ann_menu()
        return True

    def _update_recent_signatures(self, path: str) -> None:
        paths = self._settings.recent_signature_paths
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        self._settings.recent_signature_paths = paths[:10]

    def save_signed_document(self) -> bool:
        if not self.canvas.has_document:
            QMessageBox.warning(self, "Missing document", "Open a document first.")
            return False
        if not self.canvas.current_page_objects():
            QMessageBox.warning(self, "Nothing to save", "Add a signature or annotation to the page first.")
            return False
        if not self.document_path:
            QMessageBox.warning(self, "Missing document path", "Document path is unavailable.")
            return False

        page_idx = self.canvas.current_page
        default_path = build_default_output_path(
            self.document_path, page_idx, self._settings.last_save_directory
        )
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save Document with Signature", str(default_path),
            "JPEG files (*.jpg *.jpeg)",
        )
        if not chosen:
            return False
        output = Path(chosen)
        if output.suffix.lower() not in {".jpg", ".jpeg"}:
            output = output.with_suffix(".jpg")

        page_image = self.canvas.current_page_image
        objects = self.canvas.current_page_objects()
        if page_image is None or not objects:
            return False

        try:
            composite_objects_to_jpg(page_image, objects, output)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
            return False

        self._settings.last_save_directory = str(output.parent)
        self._save_settings_safe()
        QMessageBox.information(self, "Saved", f"Saved:\n{output}")
        return True

    # ---------------------------------------------------------------- helpers

    def _save_settings_safe(self) -> None:
        try:
            self._settings_store.save(self._settings)
        except Exception:
            pass

    def _update_title(self) -> None:
        doc_name = Path(self.document_path).name if self.document_path else "(no document)"
        self.setWindowTitle(f"Signer — {doc_name}")
