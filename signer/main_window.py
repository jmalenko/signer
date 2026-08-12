from __future__ import annotations

import locale
import os
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QKeyEvent
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .canvas import DocumentCanvas
from .compositor import (
    build_default_output_path,
    build_page_output_path,
    composite_objects_to_jpg,
)
from .objects import (
    AnnotationType,
    DEFAULT_FONT_FAMILY,
    DEFAULT_LINE_WIDTH_FACTOR,
    DEFAULT_TEXT_FONT_PX,
    SignatureObject,
    VectorAnnotation,
)
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


class _TextInputDialog(QDialog):
    class _CtrlEnterTextEdit(QTextEdit):
        def __init__(self, on_submit, parent=None) -> None:
            super().__init__(parent)
            self._on_submit = on_submit

        def keyPressEvent(self, event: QKeyEvent) -> None:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ControlModifier:
                    self._on_submit()
                    event.accept()
                    return
                self.insertPlainText("\n")
                event.accept()
                return
            super().keyPressEvent(event)

    def __init__(self, parent: QMainWindow, title: str, initial_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(480, 220)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Text (Enter = new line, Ctrl+Enter = confirm):"))

        self.editor = self._CtrlEnterTextEdit(self.accept, self)
        self.editor.setAcceptRichText(False)
        self.editor.setPlainText(initial_text)
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.editor.toPlainText()


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("Signer")
        
        # Initialize from settings
        self._settings_store = settings_store
        self._settings = settings
        
        # Initialize current color from settings
        self._current_color = QColor(settings.recent_color)
        
        self._sig_ann_menu: QMenu | None = None
        self._hamburger_file_menu: QMenu | None = None
        self._hamburger_text_submenu: QMenu | None = None

        self.document_path: str | None = None
        self._has_unsaved_changes: bool = False

        self.canvas = DocumentCanvas(self)
        self.setCentralWidget(self.canvas)

        self._build_toolbar()

        self.canvas.objectChanged.connect(self._on_object_changed)
        self.canvas.pageChanged.connect(self._on_page_changed)
        self.canvas.editRequested.connect(self._on_edit_requested)

        # Ensure color button reflects the persisted color after full initialization
        # Use QTimer to ensure the widget is fully initialized and shown
        QTimer.singleShot(0, self._update_color_btn)

    def run_startup_load(self, document: str | None, signature: str | None) -> None:
        def _load() -> None:
            if document:
                self.open_document(document)
            if signature:
                self._load_signature_file(signature, at_default_position=True)
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

        # Open Document with recent documents dropdown
        open_doc_btn = QToolButton(self)
        open_doc_btn.setText("📂 Open Document")
        open_doc_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        open_doc_btn.setPopupMode(QToolButton.InstantPopup)
        open_doc_menu = QMenu(open_doc_btn)
        open_doc_btn.setMenu(open_doc_menu)
        
        open_doc_menu.addAction("Open Document…", lambda: self.open_document())
        self._recent_docs_menu = open_doc_menu.addMenu("Recent Documents")
        self._rebuild_recent_documents_menu()
        
        tb.addWidget(open_doc_btn)

        # Annotation picker (2nd)
        ann_btn = QToolButton(self)
        ann_btn.setText("➕ Add Annotation")
        ann_btn.setPopupMode(QToolButton.InstantPopup)
        ann_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        ann_menu = QMenu(ann_btn)
        ann_btn.setMenu(ann_menu)

        ann_menu.addAction("✔ Checkmark", lambda: self._add_vector(AnnotationType.CHECKMARK))
        ann_menu.addAction("✖ Cross", lambda: self._add_vector(AnnotationType.CROSS))

        arrow_menu = ann_menu.addMenu("➡ Arrow")
        for name, atype in ARROW_DIRECTIONS:
            arrow_menu.addAction(name, lambda checked=False, t=atype: self._add_vector(t))

        self._toolbar_text_menu = ann_menu.addMenu("📝 Text")
        self._toolbar_text_menu.addAction("Free text…", lambda: self._add_text_annotation(""))
        self._toolbar_text_menu.addAction("Current date", lambda: self._add_text_annotation(self._locale_date()))
        self._toolbar_text_menu.addAction("Current time", lambda: self._add_text_annotation(self._locale_time()))
        self._toolbar_text_menu.addAction("Current date & time", lambda: self._add_text_annotation(self._locale_datetime()))
        self._toolbar_text_menu.addSeparator()
        self._toolbar_recent_text_actions = []
        self._rebuild_toolbar_recent_texts()

        self._sig_ann_menu = ann_menu.addMenu("🖊 Signature")
        self._rebuild_sig_ann_menu()

        ann_btn.setMenu(ann_menu)
        tb.addWidget(ann_btn)

        # Save action (3rd, same workflow group)
        big_action("💾 Save JPG", self.save_signed_document)

        tb.addSeparator()

        # Page navigation
        big_action("◀ Prev", lambda: self.canvas.goto_page(self.canvas.current_page - 1))
        self.page_label = QLabel("  Page — / —  ")
        tb.addWidget(self.page_label)
        big_action("Next ▶", lambda: self.canvas.goto_page(self.canvas.current_page + 1))

        tb.addSeparator()

        self._dup_action = big_action("❏ Duplicate", lambda: self.canvas.duplicate_selected())
        self._del_action = big_action("🗑 Delete", lambda: self.canvas.remove_selected())

        tb.addSeparator()

        # Color button
        self._color_btn = QPushButton("●")
        self._color_btn.setFixedSize(38, 38)
        self._color_btn.setToolTip("Annotation color")
        self._color_btn.clicked.connect(self._pick_color)
        self._update_color_btn()
        tb.addWidget(self._color_btn)
        self._update_annotation_action_state()

        # Add stretch to push hamburger menu to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # Hamburger menu (right end)
        hamburger = QToolButton(self)
        hamburger.setText("☰")
        hamburger.setPopupMode(QToolButton.InstantPopup)
        hamburger.setToolButtonStyle(Qt.ToolButtonTextOnly)
        hamburger.setToolTip("Menu")
        hamburger_menu = QMenu(hamburger)
        hamburger.setMenu(hamburger_menu)

        # File menu
        self._hamburger_file_menu = hamburger_menu.addMenu("File")
        self._hamburger_file_menu.addAction("Open Document", self.open_document)
        self._hamburger_file_menu.addAction("Save JPG", self.save_signed_document)
        self._hamburger_file_menu.addSeparator()
        self._file_recent_docs_actions = []  # Track recent doc actions for rebuilding
        self._rebuild_file_recent_documents_top_level(self._hamburger_file_menu)
        self._hamburger_file_menu.addSeparator()
        self._hamburger_file_menu.addAction("Exit", self.close)

        # Edit menu
        edit_menu = hamburger_menu.addMenu("Edit")
        edit_menu.addAction("Undo")  # placeholder for future
        edit_menu.addAction("Redo")  # placeholder for future
        edit_menu.addSeparator()
        edit_menu.addAction("Cut")  # placeholder
        edit_menu.addAction("Copy")  # placeholder
        edit_menu.addAction("Paste")  # placeholder
        edit_menu.addAction("Duplicate", self.canvas.duplicate_selected)
        edit_menu.addSeparator()
        edit_menu.addAction("Select All")  # placeholder
        edit_menu.addAction("Delete", self.canvas.remove_selected)

        # Annotations menu
        annotations_menu = hamburger_menu.addMenu("Annotations")
        annotations_menu.addAction("Checkmark", lambda: self._add_vector(AnnotationType.CHECKMARK))
        annotations_menu.addAction("Cross", lambda: self._add_vector(AnnotationType.CROSS))
        arrow_submenu = annotations_menu.addMenu("Arrow")
        for name, atype in ARROW_DIRECTIONS:
            arrow_submenu.addAction(name, lambda checked=False, t=atype: self._add_vector(t))
        self._hamburger_text_submenu = annotations_menu.addMenu("Text")
        self._hamburger_text_submenu.addAction("Free text…", lambda: self._add_text_annotation(""))
        self._hamburger_text_submenu.addAction("Current date", lambda: self._add_text_annotation(self._locale_date()))
        self._hamburger_text_submenu.addAction("Current time", lambda: self._add_text_annotation(self._locale_time()))
        self._hamburger_text_submenu.addAction("Current date & time", lambda: self._add_text_annotation(self._locale_datetime()))
        self._hamburger_text_submenu.addSeparator()
        self._annotations_recent_text_actions = []  # Track recent text actions for rebuilding
        self._rebuild_recent_texts_top_level(self._hamburger_text_submenu)
        annotations_menu.addAction("Signature / Image", self._add_signature_from_file)

        # Help menu
        help_menu = hamburger_menu.addMenu("Help")
        help_menu.addAction("Homepage", lambda: QDesktopServices.openUrl(QUrl("https://github.com/jmalenko/signer")))

        tb.addWidget(hamburger)
        
        # Initial rebuild of recent menus
        self._rebuild_recent_menus()

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

    def _rebuild_recent_documents_menu(self) -> None:
        """Rebuild the recent documents menu in the toolbar."""
        if not hasattr(self, '_recent_docs_menu') or self._recent_docs_menu is None:
            return
        self._recent_docs_menu.clear()
        paths = self._settings.recent_document_paths
        if paths:
            for p in paths:
                self._recent_docs_menu.addAction(
                    Path(p).name,
                    lambda checked=False, path=p: self.open_document(path),
                )
        else:
            act = self._recent_docs_menu.addAction("(none)")
            act.setEnabled(False)

    def _rebuild_file_recent_documents_menu(self) -> None:
        """Rebuild the recent documents menu in the File menu (hamburger)."""
        if not hasattr(self, '_file_recent_docs_menu') or self._file_recent_docs_menu is None:
            return
        self._file_recent_docs_menu.clear()
        paths = self._settings.recent_document_paths
        if paths:
            for p in paths:
                self._file_recent_docs_menu.addAction(
                    Path(p).name,
                    lambda checked=False, path=p: self.open_document(path),
                )
        else:
            act = self._file_recent_docs_menu.addAction("(none)")
            act.setEnabled(False)

    def _rebuild_file_recent_documents_top_level(self, file_menu: QMenu) -> None:
        """Rebuild recent documents at the top level of File menu, after static items, separated by a horizontal rule."""
        # Remove old recent document actions
        for act in self._file_recent_docs_actions:
            file_menu.removeAction(act)
        self._file_recent_docs_actions.clear()
        
        paths = self._settings.recent_document_paths
        if paths:
            # Add separator before recent items
            sep = file_menu.addSeparator()
            self._file_recent_docs_actions.append(sep)
            for p in paths:
                act = file_menu.addAction(
                    Path(p).name,
                    lambda checked=False, path=p: self.open_document(path),
                )
                self._file_recent_docs_actions.append(act)

    def _rebuild_recent_texts_top_level(self, text_submenu: QMenu) -> None:
        """Rebuild recent texts at the top level of Text submenu, after static items, separated by a horizontal rule."""
        # Remove old recent text actions
        for act in self._annotations_recent_text_actions:
            text_submenu.removeAction(act)
        self._annotations_recent_text_actions.clear()
        
        texts = self._settings.recent_text_strings
        if texts:
            # Add separator before recent items
            sep = text_submenu.addSeparator()
            self._annotations_recent_text_actions.append(sep)
            for text in texts:
                # Truncate long text for display
                display_text = text[:50] + "…" if len(text) > 50 else text
                act = text_submenu.addAction(
                    display_text,
                    lambda checked=False, t=text: self._add_text_annotation(t),
                )
                self._annotations_recent_text_actions.append(act)

    def _rebuild_toolbar_recent_texts(self) -> None:
        """Rebuild recent texts in the toolbar's Text menu."""
        if not hasattr(self, '_toolbar_text_menu') or self._toolbar_text_menu is None:
            return
        # Remove old recent text actions
        for act in self._toolbar_recent_text_actions:
            self._toolbar_text_menu.removeAction(act)
        self._toolbar_recent_text_actions.clear()
        
        texts = self._settings.recent_text_strings
        if texts:
            for text in texts:
                # Truncate long text for display
                display_text = text[:50] + "…" if len(text) > 50 else text
                act = self._toolbar_text_menu.addAction(
                    display_text,
                    lambda checked=False, t=text: self._add_text_annotation(t),
                )
                self._toolbar_recent_text_actions.append(act)

    def _rebuild_recent_menus(self) -> None:
        """Rebuild all recent items menus."""
        self._rebuild_recent_documents_menu()
        self._rebuild_file_recent_documents_menu()
        self._rebuild_sig_ann_menu()
        self._rebuild_toolbar_recent_texts()
        # Rebuild top-level recent items in hamburger menus
        if self._hamburger_file_menu is not None:
            self._rebuild_file_recent_documents_top_level(self._hamburger_file_menu)
        if self._hamburger_text_submenu is not None:
            self._rebuild_recent_texts_top_level(self._hamburger_text_submenu)

    def _on_object_changed(self) -> None:
        self._update_annotation_action_state()
        self._update_color_btn()
        self._has_unsaved_changes = True

    def _update_annotation_action_state(self) -> None:
        selected = self.canvas.selected is not None
        self._dup_action.setEnabled(selected)
        self._del_action.setEnabled(selected)
        self._color_btn.setEnabled(True)

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
            dlg = _TextInputDialog(self, "Edit Text", obj.text)
            if dlg.exec() == QDialog.Accepted:
                new_text = dlg.text()
                obj.text = new_text
                if hasattr(obj, "fit_text_box"):
                    obj.fit_text_box()
                self.canvas.update()

    # ---------------------------------------------------------------- color

    def _pick_color(self) -> None:
        selected = self.canvas.selected
        initial = selected.color if selected is not None else self._current_color
        color = QColorDialog.getColor(initial, self, "Annotation color")
        if color.isValid():
            if selected is not None:
                selected.color = color
                self._current_color = color
                self._settings.recent_color = color.name()
                self.canvas.update()
            else:
                self._current_color = color
                self._settings.recent_color = color.name()
            self._update_color_btn()
            self._save_settings_safe()

    def _update_color_btn(self) -> None:
        selected = self.canvas.selected
        color = selected.color if selected is not None else self._current_color
        c = color.name()
        self._color_btn.setStyleSheet(f"background-color: {c}; color: {'#fff' if color.lightness() < 128 else '#000'};")

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
        obj = VectorAnnotation(
            ann_type, 0, 0, self.canvas.current_page,
            font_family=self._settings.recent_font_family,
            font_size_px=self._settings.recent_font_size_px,
            line_width_factor=self._settings.recent_line_width,
        )
        obj.color = QColor(self._current_color)
        x, y = self.canvas.default_position_for(obj)
        obj.x, obj.y = x, y
        self.canvas.add_object(obj)

    def _add_text_annotation(self, preset_text: str) -> None:
        if not self.canvas.has_document:
            QMessageBox.warning(self, "No document", "Open a document first.")
            return
        if preset_text == "":
            dlg = _TextInputDialog(self, "Text Annotation")
            if dlg.exec() != QDialog.Accepted:
                return
            text = dlg.text()
            if not text.strip():
                return
            preset_text = text
        # Track recent text strings (excluding predefined date/time)
        self._update_recent_text_strings(preset_text)
        self._save_settings_safe()
        obj = VectorAnnotation(
            AnnotationType.TEXT, 0, 0, self.canvas.current_page, preset_text,
            font_family=self._settings.recent_font_family,
            font_size_px=self._settings.recent_font_size_px,
            line_width_factor=self._settings.recent_line_width,
        )
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
        # Check for unsaved changes before opening a new document
        if self.document_path and self._has_unsaved_changes:
            if not self._check_unsaved_changes():
                return False
        
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
        self._has_unsaved_changes = False
        self._settings.last_open_document_path = str(p)
        self._update_recent_documents(str(p))
        self._save_settings_safe()
        if pages:
            self._adjust_window_to_document(pages[0].size[0], pages[0].size[1])
        self._update_title()
        self._rebuild_recent_menus()
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
        obj.color = QColor(self._current_color)
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

    def _update_recent_text_strings(self, text: str) -> None:
        """Add a text string to recent texts (LRU, max 10). Excludes predefined date/time strings."""
        if not text or not text.strip():
            return
        # Exclude predefined date/time strings
        predefined = {self._locale_date(), self._locale_time(), self._locale_datetime()}
        if text in predefined:
            return
        texts = self._settings.recent_text_strings
        if text in texts:
            texts.remove(text)
        texts.insert(0, text)
        self._settings.recent_text_strings = texts[:10]

    def _update_recent_documents(self, path: str) -> None:
        """Add a document path to recent documents (LRU, max 10)."""
        paths = self._settings.recent_document_paths
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        self._settings.recent_document_paths = paths[:10]

    def save_signed_document(self) -> bool:
        if not self.canvas.has_document:
            QMessageBox.warning(self, "Missing document", "Open a document first.")
            return False
        if not self.document_path:
            QMessageBox.warning(self, "Missing document path", "Document path is unavailable.")
            return False

        total = self.canvas.page_count
        if total == 0:
            return False

        any_objects = any(self.canvas.page_objects_at(i) for i in range(total))
        if not any_objects:
            QMessageBox.warning(self, "Nothing to save", "Add a signature or annotation to the document first.")
            return False

        page_idx = self.canvas.current_page
        default_path = build_default_output_path(
            self.document_path, page_idx, self._settings.last_save_directory, total
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

        # Derive the base stem: strip any trailing -pNN the user may have kept.
        stem = output.stem
        m = re.match(r"^(.*)-p(\d+)$", stem)
        base_stem = m.group(1) if m else stem
        directory = output.parent

        saved = 0
        for idx in range(total):
            page_image = self.canvas.page_image_at(idx)
            objects = self.canvas.page_objects_at(idx)
            if page_image is None:
                continue
            out_path = build_page_output_path(base_stem, idx, total, directory)
            try:
                composite_objects_to_jpg(page_image, objects, out_path)
            except Exception as exc:
                QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
                return False
            saved += 1

        if saved == 0:
            QMessageBox.warning(self, "Nothing to save", "No pages could be saved.")
            return False

        self._settings.last_save_directory = str(directory)
        self._save_settings_safe()
        self._has_unsaved_changes = False
        QMessageBox.information(self, "Saved", f"Saved {saved} page(s) to:\n{directory}")
        return True

    # ---------------------------------------------------------------- helpers

    def _save_settings_safe(self) -> None:
        try:
            self._settings_store.save(self._settings)
        except Exception:
            pass

    def _adjust_window_to_document(self, doc_w: int, doc_h: int) -> None:
        if doc_w <= 0 or doc_h <= 0:
            return
        toolbar_hint_w = self.findChildren(QToolBar)[0].sizeHint().width() if self.findChildren(QToolBar) else 0
        chrome_h = max(120, self.height() - self.canvas.height())

        screen = self.screen()
        if screen is None:
            return
        avail = screen.availableGeometry()

        # Calculate the maximum canvas size that fits on screen
        max_canvas_h = avail.height() - chrome_h - 60
        max_canvas_w = avail.width() - 20 - 32  # account for toolbar and margins

        # Scale document to fit within max canvas size while maintaining aspect ratio
        scale_h = max_canvas_h / doc_h
        scale_w = max_canvas_w / doc_w
        scale = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 100%

        target_canvas_h = int(doc_h * scale)
        target_canvas_w = int(doc_w * scale)

        # Ensure minimum canvas size
        target_canvas_h = max(520, target_canvas_h)
        target_canvas_w = max(640, target_canvas_w)

        target_w = max(target_canvas_w, toolbar_hint_w + 32)
        target_h = target_canvas_h + chrome_h

        target_w = min(target_w, avail.width() - 20)
        target_h = min(target_h, avail.height() - 20)
        self.resize(target_w, target_h)

        # Center the window on screen to ensure it's fully visible
        self.move(
            avail.x() + (avail.width() - target_w) // 2,
            avail.y() + (avail.height() - target_h) // 2
        )

    def _update_title(self) -> None:
        doc_name = Path(self.document_path).name if self.document_path else "(no document)"
        self.setWindowTitle(f"Signer — {doc_name}")

    # ---------------------------------------------------------------- unsaved changes handling

    def _check_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes and ask user what to do.
        
        Returns True if the user wants to proceed (discard or saved successfully),
        False if the user wants to cancel the operation.
        
        In test mode (when pytest is running), automatically discards changes
        without showing a dialog to prevent blocking the test suite.
        """
        if not self._has_unsaved_changes:
            return True
        
        if not self.document_path:
            return True
        
        # In test mode, automatically discard changes without showing dialog
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        
        doc_name = Path(self.document_path).name
        result = QMessageBox.warning(
            self,
            "Unsaved Changes",
            f"Document '{doc_name}' has unsaved changes.\n\nDo you want to save the changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        
        if result == QMessageBox.Cancel:
            return False
        elif result == QMessageBox.Save:
            return self.save_signed_document()
        else:  # Discard
            return True

    def closeEvent(self, event) -> None:
        """Handle window close event, checking for unsaved changes."""
        if self._check_unsaved_changes():
            event.accept()
        else:
            event.ignore()
