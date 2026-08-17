from __future__ import annotations

import locale
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QSize, Qt, QTimer, QUrl, QCoreApplication
from PySide6.QtGui import QAction, QColor, QDesktopServices, QKeyEvent, QPainter, QImage, QPixmap, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
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
    ExportFormat,
    build_default_output_path,
    build_page_output_path,
    build_suggested_filename_for_dialog,
    replace_placeholder_with_page_number,
    validate_placeholder_for_multipage_export,
    detect_existing_files,
    detect_older_page_files,
    build_overwrite_dialog_info,
    composite_objects_to_format,
    composite_objects_to_jpg,
    composite_pages_to_pdf,
    composite_pages_to_tiff,
)
from .export_quality_dialog import ExportQualityOptionsPanel
from .notification import NotificationToast
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


class _SaveDialogWithFilterDetection(QFileDialog):
    """Custom file dialog that detects filter changes in real-time."""
    
    def __init__(self, parent=None, caption="", directory="", filter=""):
        super().__init__(parent, caption, directory, filter)
        self.setFileMode(QFileDialog.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptSave)
        # Connect to filter change signal
        self.filterSelected.connect(self._on_filter_changed)
        # Listen for file selections (includes text edits and confirmations)
        self.filesSelected.connect(self._on_files_selected)
        
        self.last_format = None
        self.total_pages = 1
        self.document_path = None
        self.last_suggested_filename = None
        self.user_custom_stem = None
        self.current_filename_in_field = None
        self._filename_edit = None
        self._options_button = None
        self.quality_panel = None
    
    def exec(self):
        """Override exec to connect line edit AFTER dialog is created but before showing."""
        # Now that the dialog widgets are created, connect to the line edit
        self._connect_line_edit()
        # Add the Options button
        self._add_options_button()
        # Update Options button state based on initial format
        self._update_options_button_state()
        # Call the parent exec() which will show the dialog
        return super().exec()
    
    def _connect_line_edit(self):
        """Find the QLineEdit widget and connect to its textChanged signal for real-time capture."""
        # Find all QLineEdit widgets in the dialog
        line_edits = self.findChildren(QLineEdit)
        
        if line_edits:
            # The first line edit is typically the filename field
            filename_edit = line_edits[0]
            filename_edit.textChanged.connect(self._on_filename_text_changed)
            self._filename_edit = filename_edit
        else:
            self._filename_edit = None
    
    def _add_options_button(self):
        """Add the Options button to the file dialog's button area."""
        # Find the QDialogButtonBox which contains Save/Cancel buttons
        button_boxes = self.findChildren(QDialogButtonBox)
        
        if button_boxes:
            button_box = button_boxes[0]
            # Add a custom button labeled "Options..."
            self._options_button = button_box.addButton("Options...", QDialogButtonBox.ActionRole)
            self._options_button.clicked.connect(self._on_options_clicked)
    
    def _update_options_button_state(self):
        """Enable/disable Options button based on current format."""
        if not self._options_button:
            return
        
        # Get the currently selected format
        selected_filter = self.selectedNameFilter()
        detected_format = ExportFormat.from_filter_string(selected_filter)
        
        # Enable button only for lossy formats (JPG, PDF)
        is_lossy = detected_format in (ExportFormat.JPG, ExportFormat.PDF)
        self._options_button.setEnabled(is_lossy)
    
    def _on_options_clicked(self):
        """Handle Options button click - show quality panel."""
        selected_filter = self.selectedNameFilter()
        detected_format = ExportFormat.from_filter_string(selected_filter)
        
        # Only show panel for lossy formats
        if detected_format not in (ExportFormat.JPG, ExportFormat.PDF):
            return
        
        # Get current quality from settings (passed via parent window)
        parent_window = self.parent()
        if hasattr(parent_window, '_settings'):
            if detected_format == ExportFormat.JPG:
                current_quality = parent_window._settings.last_jpeg_quality
            else:  # PDF
                current_quality = parent_window._settings.last_pdf_image_quality
        else:
            current_quality = 95
        
        # Show quality panel
        self.quality_panel = ExportQualityOptionsPanel(self, detected_format, current_quality)
        if self.quality_panel.exec() == QDialog.Accepted:
            # Update settings with new quality
            new_quality = self.quality_panel.get_quality()
            if hasattr(parent_window, '_settings'):
                if detected_format == ExportFormat.JPG:
                    parent_window._settings.last_jpeg_quality = new_quality
                else:  # PDF
                    parent_window._settings.last_pdf_image_quality = new_quality
                # Save settings
                if hasattr(parent_window, '_save_settings_safe'):
                    parent_window._save_settings_safe()
    
    def _on_filename_text_changed(self, text):
        """Called in real-time as user types in the filename field."""
        # Extract just the filename without path
        filename = Path(text).name if text else ""
        self.current_filename_in_field = filename
    
    def _on_files_selected(self, files):
        """Called when user selects/types a filename (fallback)."""
        if files:
            filename = Path(files[0]).name
            self.current_filename_in_field = filename
    
    def _on_filter_changed(self, selected_filter: str):
        """Called when user changes the 'Save as type' dropdown."""
        # Update Options button state when format changes
        self._update_options_button_state()
        
        detected_format = ExportFormat.from_filter_string(selected_filter)
        
        # Only update if format actually changed
        if detected_format and detected_format != self.last_format and self.document_path:
            # Get the current filename - use what was in the field from textChanged signal
            current_filename = self.current_filename_in_field or ""
            suggested_for_new_format = build_suggested_filename_for_dialog(
                self.document_path, self.total_pages, detected_format
            )
            
            # Decide what filename to use
            # Check if current filename differs from what we last suggested
            if (current_filename and 
                current_filename != self.last_suggested_filename and 
                current_filename != "" and
                self.last_suggested_filename is not None):
                # User manually edited the filename - extract and preserve their stem
                current_path = Path(current_filename)
                current_stem = current_path.stem
                
                # If this is the first manual edit, capture the user's stem
                if self.user_custom_stem is None:
                    self.user_custom_stem = current_stem
                else:
                    # On subsequent format changes, use the captured custom stem
                    current_stem = self.user_custom_stem
            else:
                # User didn't edit (or first time), use system stem
                current_stem = None
            
            # Build new filename based on whether we have a custom stem
            if current_stem:
                # Use user's custom stem with new format rules
                if detected_format.is_single_file_format():
                    # Single-file format (PDF, TIFF) - no placeholder
                    new_filename = f"{current_stem}{detected_format.extension()}"
                else:
                    # Multi-file format (JPG, PNG, BMP) - add placeholder
                    new_filename = f"{current_stem}-p#{detected_format.extension()}"
            else:
                # No custom stem, use system suggestion
                new_filename = suggested_for_new_format
            
            # Update the filename in the dialog
            # Instead of selectFile(full_path) which shows the full path in the text field,
            # we just update the line edit directly with just the filename
            current_dir = Path(self.directory().absolutePath())
            
            if self._filename_edit:
                self._filename_edit.setText(new_filename)
            else:
                # Fallback: if line edit not available, try selectFile with just filename
                new_full_path = current_dir / new_filename
                self.selectFile(str(new_full_path))
            
            # Update our tracking after we change it
            self.current_filename_in_field = new_filename
            
            # Remember what we suggested for next comparison
            self.last_suggested_filename = new_filename
            self.last_format = detected_format


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


class _PasswordDialog(QDialog):
    """Dialog to prompt for PDF password."""
    def __init__(self, parent: QMainWindow, pdf_filename: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.resize(350, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'The file "{pdf_filename}" is encrypted.\nPlease enter the password:'))

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Focus on password input for convenience
        self.password_input.setFocus()

    def password(self) -> str:
        return self.password_input.text()


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
        big_action("💾 Save As…", self.save_document_as)

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
        self._hamburger_file_menu.addAction("Open Document (Ctrl+O or O)", self.open_document)
        self._hamburger_file_menu.addAction("Save As… (Ctrl+S or S)", self.save_document_as)
        self._hamburger_file_menu.addAction("Print (Ctrl+P or P)", self.print_document)
        self._hamburger_file_menu.addSeparator()
        self._file_recent_docs_actions = []  # Track recent doc actions for rebuilding
        self._rebuild_file_recent_documents_top_level(self._hamburger_file_menu)
        self._hamburger_file_menu.addSeparator()
        self._hamburger_file_menu.addAction("Exit", self.close)

        # Edit menu
        edit_menu = hamburger_menu.addMenu("Edit")
        edit_menu.addAction("Undo (Ctrl+Z or Z)", self.undo)
        edit_menu.addAction("Redo (Ctrl+Y or Y)", self.redo)
        edit_menu.addSeparator()
        edit_menu.addAction("Cut (Ctrl+X or X)", self.canvas.cut_selected)
        edit_menu.addAction("Copy (Ctrl+C or C)", self.canvas.copy_selected)
        edit_menu.addAction("Paste (Ctrl+V or V)", self.canvas.paste_selected)
        edit_menu.addAction("Duplicate (Ctrl+D or D)", self.canvas.duplicate_selected)
        edit_menu.addSeparator()
        edit_menu.addAction("Select All (Ctrl+A or A)", self.canvas.select_all_on_page)
        edit_menu.addAction("Delete", self.canvas.remove_selected)
        edit_menu.addSeparator()
        edit_menu.addAction("Rotate Current Page Left (Shift+Ctrl+L or Shift+L)", self.canvas.rotate_current_page_left)
        edit_menu.addAction("Rotate Current Page Right (Shift+Ctrl+R or Shift+R)", self.canvas.rotate_current_page_right)
        edit_menu.addSeparator()
        edit_menu.addAction("Rotate All Pages Left (Ctrl+L or L)", self.canvas.rotate_all_pages_left)
        edit_menu.addAction("Rotate All Pages Right (Ctrl+R or R)", self.canvas.rotate_all_pages_right)

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
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Open Document", start_dir,
                "All Supported Files (*.pdf *.docx *.doc *.odt *.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tiff *.tif);;"
                "PDF Files (*.pdf);;Word Documents (*.docx *.doc);;OpenDocument Text (*.odt);;"
                "Image Files (*.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tiff *.tif)"
            )

        if not chosen:
            return False
        p = Path(chosen)

        password = ""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                pages = render_all_pages(
                    p, dpi=300, password=password,
                    libreoffice_path=self._settings.libreoffice_path
                )
            except ValueError as exc:
                error_msg = str(exc)
                # PDF is encrypted and password is wrong or missing
                if "encrypted" in error_msg.lower():
                    dialog = _PasswordDialog(self, p.name)
                    if dialog.exec() != QDialog.Accepted:
                        return False
                    password = dialog.password()
                    continue
                else:
                    QMessageBox.critical(self, "Open document failed", f"Could not open document:\n{error_msg}")
                    return False
            except Exception as exc:
                QMessageBox.critical(self, "Open document failed", f"Could not open document:\n{exc}")
                return False
            break  # Success
        else:
            # Max attempts exceeded
            QMessageBox.critical(self, "Open document failed", "Incorrect password or maximum attempts exceeded.")
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
        """Deprecated: delegates to save_document_as() for backward compatibility."""
        return self.save_document_as()

    def save_document_as(self) -> bool:
        """Save document in selected format with Save As dialog."""
        # In test mode, skip dialogs that require user interaction
        in_test_mode = os.environ.get("PYTEST_CURRENT_TEST") is not None
        
        if not self.canvas.has_document:
            if not in_test_mode:
                QMessageBox.warning(self, "Missing document", "Open a document first.")
            return False
        if not self.document_path:
            if not in_test_mode:
                QMessageBox.warning(self, "Missing document path", "Document path is unavailable.")
            return False

        total = self.canvas.page_count
        if total == 0:
            return False

        any_objects = any(self.canvas.page_objects_at(i) for i in range(total))
        if not any_objects:
            if not in_test_mode:
                QMessageBox.warning(self, "Nothing to save", "Add a signature or annotation to the document first.")
            return False

        page_idx = self.canvas.current_page
        
        # Determine last export format and folder
        last_format_str = self._settings.last_export_format or "jpg"
        try:
            last_export_format = ExportFormat(last_format_str)
        except ValueError:
            last_export_format = ExportFormat.JPG
        
        last_export_folder = self._settings.last_export_folder or self._settings.last_save_directory
        
        # Track user's last choices in the file dialog so we can restore them if they cancel overwrite confirmation
        last_user_chosen_path: Path | None = None
        last_user_chosen_format: ExportFormat | None = None
        
        # Loop for file dialog - allows user to retry if validation fails or overwrite is cancelled
        while True:
            # Build suggested filename with dynamic placeholder based on current format
            suggested_filename = build_suggested_filename_for_dialog(
                self.document_path, total, last_export_format
            )
            
            directory = Path(last_export_folder) if last_export_folder else Path(self.document_path).parent
            
            # If user previously chose a file in this session and cancelled overwrite, restore those values
            if last_user_chosen_path is not None:
                default_path = last_user_chosen_path
                suggested_filename = last_user_chosen_path.name
                # Also restore the format they chose
                last_export_format = last_user_chosen_format or last_export_format
            else:
                default_path = directory / suggested_filename
            
            # Get all format filters
            all_filters_str = ExportFormat.all_formats_filter()
            
            # In test mode, use static dialog method (easier to mock)
            # In normal mode, use custom dialog with real-time filter detection
            if in_test_mode:
                # Note: Also disable built-in overwrite confirmation for consistency
                # We handle it with our own custom dialog (v1.2.13)
                chosen, selected_filter = QFileDialog.getSaveFileName(
                    self, "Save Document As", str(default_path),
                    all_filters_str, last_export_format.file_filter(),
                    options=QFileDialog.DontConfirmOverwrite
                )
                if not chosen:
                    return False
            else:
                # Use custom dialog that detects filter changes in real-time
                dialog = _SaveDialogWithFilterDetection(
                    self, "Save Document As", str(default_path),
                    all_filters_str
                )
                # CRITICAL: Disable native dialog mode so Qt widgets (QLineEdit) are accessible
                # Native Windows file dialog doesn't expose child widgets for us to monitor
                dialog.setOption(QFileDialog.DontUseNativeDialog, True)
                
                # CRITICAL: Disable Qt's built-in overwrite confirmation
                # We handle overwrite confirmation with our own custom dialog (v1.2.13)
                dialog.setOption(QFileDialog.DontConfirmOverwrite, True)
                
                dialog.last_format = last_export_format
                dialog.total_pages = total
                dialog.document_path = self.document_path
                dialog.last_suggested_filename = suggested_filename  # Remember what we suggested initially
                
                # Set the initial filter to match last_export_format
                filter_to_select = last_export_format.file_filter()
                dialog.selectNameFilter(filter_to_select)
                
                if dialog.exec() != QFileDialog.Accepted:
                    return False
                
                chosen = dialog.selectedFiles()[0] if dialog.selectedFiles() else None
                if not chosen:
                    return False
                
                selected_filter = dialog.selectedNameFilter()
                
                # Explicitly close the file dialog to remove it from screen
                # before showing any confirmation dialogs
                dialog.close()
                # Process events to ensure the dialog is fully closed
                QCoreApplication.processEvents()
            
            output = Path(chosen)
            
            # Save user's choice so we can restore it if they cancel overwrite confirmation
            last_user_chosen_path = output
            
            # DETECT FORMAT FROM USER'S ACTIONS
            # First, try to detect from the file extension they typed
            export_format = ExportFormat.from_extension(output.suffix)
            
            # Then, check what filter they selected in the dropdown
            # If they explicitly selected a different format filter, that takes precedence
            filter_based_format = ExportFormat.from_filter_string(selected_filter)
            
            # Save the detected format for restoration if user cancels overwrite
            last_user_chosen_format = export_format
            
            # If file extension and filter don't match, user likely selected a different format in dropdown
            # The filter selection is explicit user action, so trust that
            if filter_based_format != export_format and selected_filter and "supported" not in selected_filter.lower():
                # User selected a specific format filter
                export_format = filter_based_format
                # Update the filename extension to match what they selected
                output = output.with_suffix(export_format.extension())
            
            # Ensure correct extension
            if output.suffix.lower() != export_format.extension():
                output = output.with_suffix(export_format.extension())
            
            # AUTO-CORRECT FILENAME WHEN FORMAT CHANGES VIA FILTER
            # If the format changed from what we suggested, check if user just selected a different filter
            if export_format != last_export_format:
                # Build what the new format would suggest
                suggested_for_new_format = build_suggested_filename_for_dialog(
                    self.document_path, total, export_format
                )
                
                # If the user's input EXACTLY matches the OLD suggested format,
                # it means they just selected a different format filter without editing the filename.
                # Auto-correct to the new format's requirements.
                if output.name == suggested_filename:
                    # Auto-correct: update filename to match new format
                    output = output.parent / suggested_for_new_format
                    # Update tracking for next iteration if needed
                    last_export_format = export_format
                    last_export_folder = str(output.parent)
                    # Continue loop to validate the auto-corrected filename
                    continue
            
            # Filename validation - format-aware instead of exact-match
            # Get filename without extension (may contain placeholder)
            filename_stem = output.stem
            directory = output.parent
            
            # For single-file formats (PDF, TIFF), any filename with correct extension is valid
            # For multi-file formats (JPG, PNG, BMP), filename must have # placeholder
            if export_format.is_single_file_format():
                # Single-file format - just check extension is correct
                if output.suffix.lower() == export_format.extension():
                    # Extension is correct, validation passes
                    pass  # Continue with export
                else:
                    if not in_test_mode:
                        QMessageBox.information(
                            self, "Invalid extension",
                            f"File extension doesn't match the {export_format.value.upper()} format.\n\n"
                            f"You entered: {output.name}\n"
                            f"Should end with: {export_format.extension()}\n\n"
                            f"Please correct the filename.",
                        )
                        last_export_format = export_format
                        last_export_folder = str(output.parent)
                        continue
                    else:
                        return False
            else:
                # Multi-file format - must have # placeholder for multi-page documents
                is_valid, error_msg = validate_placeholder_for_multipage_export(
                    filename_stem, total, export_format
                )
                
                if not is_valid:
                    if not in_test_mode:
                        result = QMessageBox.warning(
                            self, "Invalid filename",
                            error_msg + "\n\nDo you want to choose a different filename?",
                            QMessageBox.Ok | QMessageBox.Cancel
                        )
                        if result == QMessageBox.Ok:
                            last_export_format = export_format
                            last_export_folder = str(directory)
                            continue
                        else:
                            return False
                    else:
                        return False
                else:
                    pass  # Multi-file format validation passed
            
            # ================================================================
            # CHECK FOR OVERWRITE AND SHOW CONFIRMATION DIALOG (v1.2.13)
            # ================================================================
            
            # Detect which files would be overwritten
            existing_files = detect_existing_files(output, total, export_format, filename_stem)
            older_files = detect_older_page_files(output.parent, filename_stem, total, export_format)
            
            # Get dialog info based on scenario
            dialog_title, dialog_message, show_cleanup_checkbox = build_overwrite_dialog_info(
                existing_files, older_files, total, export_format, output
            )
            
            # If there are files to overwrite, show confirmation dialog
            if existing_files:
                if not in_test_mode:
                    cleanup_checkbox_result = False
                    
                    if show_cleanup_checkbox:
                        # Scenario E: Show dialog with cleanup checkbox for older files
                        dialog = QDialog(self)
                        dialog.setWindowTitle(dialog_title)
                        dialog.setModal(True)
                        dialog.setMinimumWidth(450)
                        
                        layout = QVBoxLayout(dialog)
                        
                        # Add message label
                        message_label = QLabel(dialog_message)
                        message_label.setWordWrap(True)
                        layout.addWidget(message_label)
                        
                        # Add cleanup checkbox
                        cleanup_checkbox = QCheckBox("Delete older page files")
                        cleanup_checkbox.setChecked(False)  # Unchecked by default
                        layout.addWidget(cleanup_checkbox)
                        
                        # Add buttons
                        button_layout = QVBoxLayout()
                        replace_button = QPushButton("Replace")
                        cancel_button = QPushButton("Cancel")
                        button_layout.addWidget(replace_button)
                        button_layout.addWidget(cancel_button)
                        layout.addLayout(button_layout)
                        
                        # Connect button signals
                        user_clicked_replace = False
                        
                        def update_replace_button_text(state=None):
                            """Update Replace button text based on checkbox state."""
                            if cleanup_checkbox.isChecked():
                                replace_button.setText("Replace and delete older page files")
                            else:
                                replace_button.setText("Replace")
                        
                        def on_replace():
                            nonlocal user_clicked_replace
                            user_clicked_replace = True
                            dialog.accept()
                        
                        def on_cancel():
                            dialog.reject()
                        
                        # Connect checkbox state change to update button text
                        cleanup_checkbox.toggled.connect(update_replace_button_text)
                        replace_button.clicked.connect(on_replace)
                        cancel_button.clicked.connect(on_cancel)
                        
                        # Initialize button text
                        update_replace_button_text()
                        
                        # Show dialog
                        result = dialog.exec()
                        cleanup_checkbox_result = cleanup_checkbox.isChecked()
                        
                        # User clicked Cancel - return to file dialog
                        if result == QDialog.Rejected:
                            # Don't clear last_user_chosen_path/format - keep them for restoration
                            continue  # Go back to file dialog with same values
                    else:
                        # Scenarios A-D: Simple yes/no confirmation dialog
                        user_choice = QMessageBox.question(
                            self, dialog_title, dialog_message,
                            QMessageBox.StandardButtons(QMessageBox.Yes | QMessageBox.No),
                            QMessageBox.No
                        )
                        
                        # User clicked No - return to file dialog
                        if user_choice == QMessageBox.No:
                            # Don't clear last_user_chosen_path/format - keep them for restoration
                            continue  # Go back to file dialog with same values
                    
                    # User clicked Replace - proceed with export
                    # If cleanup checkbox was checked, delete older files
                    if show_cleanup_checkbox and cleanup_checkbox_result:
                        for old_file in older_files:
                            try:
                                old_file.unlink()
                            except Exception as e:
                                # Log but don't fail - user still wants to export
                                logging.warning(f"Could not delete {old_file}: {e}")
            
            # All checks passed, proceed with export
            break
        
        # ============================================================================
        # GET QUALITY SETTINGS (Updated by Options button in dialog if clicked)
        # ============================================================================
        
        # Quality values are already in settings; they're updated by Options button in dialog
        jpg_quality = self._settings.last_jpeg_quality
        pdf_quality = self._settings.last_pdf_image_quality
        
        # ============================================================================
        # PROCEED WITH EXPORT
        # ============================================================================
        
        try:
            saved = 0
            exported_files: list[Path] = []
            
            # Handle multi-page PDF and TIFF specially

            if export_format == ExportFormat.PDF:
                # Export all pages as PDF
                page_images = [self.canvas.get_page_image_with_rotation(idx) for idx in range(total)]
                page_objects_list = [self.canvas.page_objects_with_rotation_at(idx) for idx in range(total)]
                
                # Filter out None pages
                valid_pages = [(img, objs) for img, objs in zip(page_images, page_objects_list) if img is not None]
                if valid_pages:
                    page_images, page_objects_list = zip(*valid_pages)
                    try:
                        composite_pages_to_pdf(list(page_images), list(page_objects_list), output, pdf_quality)
                        saved = total
                        exported_files = [output]
                    except PermissionError:
                        if not in_test_mode:
                            QMessageBox.critical(
                                self, "Save failed",
                                f"Permission denied. Check write permissions for:\n{directory}\n\n"
                                "Try saving to a different location."
                            )
                        return False
                    except OSError as exc:
                        if "No space left" in str(exc):
                            if not in_test_mode:
                                QMessageBox.critical(
                                    self, "Save failed",
                                    "Insufficient disk space. Free up space and try again."
                                )
                            return False
                        else:
                            if not in_test_mode:
                                QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
                            return False
                    except Exception as exc:
                        if not in_test_mode:
                            QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
                        return False
            
            elif export_format == ExportFormat.TIFF:
                # Export all pages as TIFF
                page_images = [self.canvas.get_page_image_with_rotation(idx) for idx in range(total)]
                page_objects_list = [self.canvas.page_objects_with_rotation_at(idx) for idx in range(total)]
                
                # Filter out None pages
                valid_pages = [(img, objs) for img, objs in zip(page_images, page_objects_list) if img is not None]
                if valid_pages:
                    page_images, page_objects_list = zip(*valid_pages)
                    try:
                        composite_pages_to_tiff(list(page_images), list(page_objects_list), output)
                        saved = total
                        exported_files = [output]
                    except PermissionError:
                        if not in_test_mode:
                            QMessageBox.critical(
                                self, "Save failed",
                                f"Permission denied. Check write permissions for:\n{directory}\n\n"
                                "Try saving to a different location."
                            )
                        return False
                    except OSError as exc:
                        if "No space left" in str(exc):
                            if not in_test_mode:
                                QMessageBox.critical(
                                    self, "Save failed",
                                    "Insufficient disk space. Free up space and try again."
                                )
                            return False
                        else:
                            if not in_test_mode:
                                QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
                            return False
                    except Exception as exc:
                        if not in_test_mode:
                            QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
                        return False
            
            else:
                # For JPG, PNG, BMP: export per-page or single page
                failed_pages = []
                for idx in range(total):
                    page_image = self.canvas.get_page_image_with_rotation(idx)
                    objects = self.canvas.page_objects_with_rotation_at(idx)
                    if page_image is None:
                        continue
                    
                    # Replace placeholder with actual page number if needed
                    actual_filename = replace_placeholder_with_page_number(filename_stem, idx, total)
                    out_path = directory / f"{actual_filename}{export_format.extension()}"
                    
                    try:
                        composite_objects_to_format(page_image, objects, out_path, export_format, jpg_quality)
                        exported_files.append(out_path)
                        saved += 1
                    except PermissionError:
                        failed_pages.append((idx, "Permission denied"))
                    except OSError as exc:
                        if "No space left" in str(exc):
                            if not in_test_mode:
                                QMessageBox.critical(
                                    self, "Save failed",
                                    "Insufficient disk space. Free up space and try again."
                                )
                            return False
                        else:
                            failed_pages.append((idx, str(exc)))
                    except Exception as exc:
                        failed_pages.append((idx, str(exc)))
                
                # If some pages failed, show error
                if failed_pages:
                    if not in_test_mode:
                        failed_list = "\n".join([f"Page {p+1}: {e}" for p, e in failed_pages])
                        QMessageBox.critical(
                            self, "Save failed",
                            f"Failed to save some pages:\n{failed_list}\n\n"
                            "Check write permissions and disk space, then try again."
                        )
                    # Even if some pages failed, return success if at least one was saved
                    if saved == 0:
                        return False
            
            if saved == 0:
                if not in_test_mode:
                    QMessageBox.warning(self, "Nothing to save", "No pages could be saved.")
                return False
            
            # Update settings with last export format and folder
            self._settings.last_export_format = export_format.value
            self._settings.last_export_folder = str(directory)
            self._settings.last_save_directory = str(directory)
            self._save_settings_safe()
            self._has_unsaved_changes = False
            
            # Show auto-dismissing notification with clickable directory link
            if not in_test_mode:
                if total == 1:
                    # Single-page: show filename
                    filename = output.name
                    message = f"Exported {filename} to "
                else:
                    # Multi-page: show pattern with placeholder
                    message = f"Exported {filename_stem}{export_format.extension()} to "
                
                NotificationToast(self, message, directory, exported_files=exported_files)
            
            return True
        
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Unexpected error:\n{exc}")
            return False

    def print_document(self) -> None:
        """Print the current document with all annotations."""
        in_test_mode = os.environ.get("PYTEST_CURRENT_TEST") is not None
        
        try:
            if not self.canvas.has_document:
                if not in_test_mode:
                    QMessageBox.warning(self, "Missing document", "Open a document first.")
                return
            
            total = self.canvas.page_count
            if total == 0:
                if not in_test_mode:
                    QMessageBox.warning(self, "Empty document", "Document has no pages.")
                return
            
            # Create printer object
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.A4))
            
            # Show print dialog
            print_dialog = QPrintDialog(printer, self)
            dialog_result = print_dialog.exec()
            if dialog_result != QDialog.Accepted:
                return
            
            # Render all pages to printer
            painter = QPainter()
            if not painter.begin(printer):
                if not in_test_mode:
                    QMessageBox.critical(self, "Print failed", "Failed to initialize printer.")
                return
            
            try:
                for page_idx in range(total):
                    # Get page image
                    page_image = self.canvas.page_image_at(page_idx)
                    if page_image is None:
                        continue
                    
                    # Get page objects
                    objects = self.canvas.page_objects_at(page_idx)
                    
                    # Composite objects onto page image (in memory, no file I/O)
                    composite_image = page_image.convert("RGBA")
                    if objects:
                        from PIL import Image as PILImage
                        pw, ph = composite_image.size
                        for obj in objects:
                            try:
                                overlay = obj.render_to_pil().convert("RGBA")
                                x = int(round(obj.x))
                                y = int(round(obj.y))
                                # Clamp to avoid out-of-bounds
                                x = max(0, min(x, pw - 1))
                                y = max(0, min(y, ph - 1))
                                composite_image.alpha_composite(overlay, dest=(x, y))
                            except Exception:
                                continue
                    
                    # Convert back to RGB for printing
                    composite_image = composite_image.convert("RGB")
                    
                    # Convert PIL image to QPixmap for printing
                    from io import BytesIO
                    buffer = BytesIO()
                    composite_image.save(buffer, format='JPEG', quality=95)
                    buffer.seek(0)
                    pixmap = QPixmap()
                    pixmap.loadFromData(buffer.getvalue(), 'JPEG')
                    
                    # Scale to fit page while maintaining aspect ratio
                    page_rect = printer.pageRect(QPrinter.DevicePixel)
                    scaled_pixmap = pixmap.scaledToWidth(
                        int(page_rect.width()), Qt.SmoothTransformation
                    )
                    
                    # Draw on page
                    x = int((page_rect.width() - scaled_pixmap.width()) / 2)
                    y = int((page_rect.height() - scaled_pixmap.height()) / 2)
                    painter.drawPixmap(x, y, scaled_pixmap)
                    
                    # New page for next document (except last page)
                    if page_idx < total - 1:
                        printer.newPage()
            finally:
                painter.end()
            
            if not in_test_mode:
                NotificationToast(self, "Document sent to printer successfully.")
        
        except Exception as exc:
            if not in_test_mode:
                QMessageBox.critical(self, "Print error", f"Unexpected error during printing:\n{exc}")
            import traceback
            traceback.print_exc()

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

    # ---------------------------------------------------------------- undo/redo (placeholder)

    def undo(self) -> None:
        """Undo the last action (placeholder - not yet implemented)."""
        # TODO: Implement undo/redo stack
        pass

    def redo(self) -> None:
        """Redo the last undone action (placeholder - not yet implemented)."""
        # TODO: Implement undo/redo stack
        pass

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
            return self.save_document_as()
        else:  # Discard
            return True

    def closeEvent(self, event) -> None:
        """Handle window close event, checking for unsaved changes."""
        if self._check_unsaved_changes():
            event.accept()
        else:
            event.ignore()
