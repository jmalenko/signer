from __future__ import annotations

import json
import locale
import logging
import os
import re

logger = logging.getLogger(__name__)

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QCoreApplication, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QKeyEvent,
    QPageSize,
    QPainter,
    QPixmap,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .canvas import DocumentCanvas
from .compositor import (
    ExportFormat,
    _composite_objects,
    build_overwrite_dialog_info,
    build_suggested_filename_for_dialog,
    composite_objects_to_format,
    composite_objects_to_jpg,  # noqa: F401 - retained for test patch compatibility
    composite_pages_to_pdf,
    composite_pages_to_tiff,
    detect_existing_files,
    detect_older_page_files,
    replace_placeholder_with_page_number,
    validate_placeholder_for_multipage_export,
)
from .export_quality_dialog import ExportQualityOptionsPanel
from .constants import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_LINE_WIDTH_PT,
    DEFAULT_TEXT_FONT_PT,
    SUPPORTED_SIGNATURE_EXT,
)
from .notification import NotificationToast
from .objects import (
    AnnotationType,
    ProjectFile,
    SignatureObject,
    VectorAnnotation,
)
from .pdf_utils import render_all_pages
from .prepare_signature_dialog import PrepareSignatureDialog
from .settings import AppSettings, SettingsStore

# Max number of entries kept in each "recent items" list (documents, signatures, texts).
MAX_RECENT_ITEMS = 10


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
        self._hamburger_annotations_menu: QMenu | None = None
        self._add_annotation_btn: QToolButton | None = None
        self._save_as_toolbar_action: QAction | None = None
        self._save_as_file_action: QAction | None = None
        self._print_action: QAction | None = None
        self._menu_undo_action: QAction | None = None
        self._menu_redo_action: QAction | None = None
        self._menu_cut_action: QAction | None = None
        self._menu_copy_action: QAction | None = None
        self._menu_paste_action: QAction | None = None
        self._menu_duplicate_action: QAction | None = None
        self._menu_select_all_action: QAction | None = None
        self._menu_delete_action: QAction | None = None
        self._menu_rotate_page_left_action: QAction | None = None
        self._menu_rotate_page_right_action: QAction | None = None
        self._menu_rotate_all_left_action: QAction | None = None
        self._menu_rotate_all_right_action: QAction | None = None
        self._page_nav_prev_action: QAction | None = None
        self._page_nav_next_action: QAction | None = None
        self._page_nav_label: QLabel | None = None

        self.document_path: str | None = None
        self.project_path: str | None = None
        self._last_export_path: str | None = None
        self._has_unsaved_changes: bool = False
        self._saving_project: bool = False

        self.canvas = DocumentCanvas(self)
        self.setCentralWidget(self.canvas)

        self._build_toolbar()
        a4_size = QPageSize(QPageSize.A4).sizePixels(300)
        self._adjust_window_to_document(a4_size.width(), a4_size.height())

        self.canvas.objectChanged.connect(self._on_object_changed)
        self.canvas.pageChanged.connect(self._on_page_changed)
        self.canvas.editRequested.connect(self._on_edit_requested)
        self.canvas.fileDrop.connect(self._on_file_drop)

        # Ensure color button reflects the persisted color after full initialization
        # Use QTimer to ensure the widget is fully initialized and shown
        QTimer.singleShot(0, self._update_color_btn)

        self._in_test_mode = os.environ.get("PYTEST_CURRENT_TEST") is not None

    def run_startup_load(self, document: str | None, signature: str | None) -> None:
        def _load() -> None:
            if document:
                self.open_document(document)
            if signature:
                self._load_signature_file(signature, at_default_position=True)
            # Force real window activation before focusing: a freshly-shown window may not yet be key/active.
            self.raise_()
            self.activateWindow()
            self.canvas.setFocus()
        QTimer.singleShot(0, _load)

    # ---------------------------------------------------------------- toolbar

    def _build_toolbar(self) -> None:
        # macOS unified title/toolbar doesn't reliably re-layout when toolbar
        # widgets are hidden/shown dynamically; use a regular toolbar instead.
        self.setUnifiedTitleAndToolBarOnMac(False)

        tb = QToolBar("Main", self)
        tb.setMovable(False)
        tb.setContextMenuPolicy(Qt.CustomContextMenu)
        tb.setIconSize(QSize(24, 24))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # Fixed height so toggling the color button (38px) doesn't resize the toolbar.
        tb.setFixedHeight(44)
        # Unify font size across buttons, labels and inputs (native button style otherwise renders smaller).
        tb.setStyleSheet(
            "QToolBar QLabel, QToolBar QToolButton, QToolBar QPushButton, "
            "QToolBar QComboBox, QToolBar QSpinBox, QToolBar QDoubleSpinBox { font-size: 13px; }"
        )
        self.addToolBar(tb)
        self._main_toolbar = tb

        def big_action(text: str, slot) -> QAction:
            act = QAction(text, self)
            act.triggered.connect(slot)
            tb.addAction(act)
            return act

        # Open with recent documents dropdown
        open_doc_btn = QToolButton(self)
        open_doc_btn.setText("📂 Open")
        open_doc_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        open_doc_btn.setPopupMode(QToolButton.InstantPopup)
        open_doc_menu = QMenu(open_doc_btn)
        open_doc_btn.setMenu(open_doc_menu)
        
        open_doc_menu.addAction("Open…", lambda: self.open_document())
        self._recent_docs_menu = open_doc_menu.addMenu("Recent Documents")
        self._rebuild_recent_documents_menu()
        
        tb.addWidget(open_doc_btn)

        # Annotation picker (2nd)
        ann_btn = QToolButton(self)
        ann_btn.setText("➕ Add")
        ann_btn.setPopupMode(QToolButton.InstantPopup)
        ann_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        ann_menu = QMenu(ann_btn)
        ann_btn.setMenu(ann_menu)
        self._add_annotation_btn = ann_btn

        self._populate_annotation_type_actions(ann_menu, with_icons=True)

        self._toolbar_text_menu = ann_menu.addMenu("📝 Text")
        self._toolbar_text_menu.addAction("Free text…", lambda: self._add_text_annotation(""))
        self._toolbar_text_menu.addAction("Current date", lambda: self._add_text_annotation(self._locale_date()))
        self._toolbar_text_menu.addAction("Current time", lambda: self._add_text_annotation(self._locale_time()))
        self._toolbar_text_menu.addAction("Current date & time", lambda: self._add_text_annotation(self._locale_datetime()))
        self._toolbar_text_menu.addSeparator()
        self._toolbar_recent_text_actions = []
        self._rebuild_toolbar_recent_texts()

        # v1.2.22: Rename to Signature / Image submenu
        self._sig_ann_menu = ann_menu.addMenu("🖊 Signature / Image")
        self._rebuild_sig_ann_menu()

        ann_btn.setMenu(ann_menu)
        tb.addWidget(ann_btn)

        # Save action (3rd, same workflow group)
        self._save_as_toolbar_action = big_action("💾 Save", self.save_document_as)

        self._page_nav_separator_action = tb.addSeparator()

        # Page navigation
        self._page_nav_prev_action = QAction("◀", self)
        self._page_nav_prev_action.triggered.connect(lambda: self.canvas.goto_page(self.canvas.current_page - 1))
        tb.addAction(self._page_nav_prev_action)

        self._page_nav_label = QLabel("  Page — / —  ")
        self._page_nav_label_action = tb.addWidget(self._page_nav_label)

        self._page_nav_next_action = QAction("▶", self)
        self._page_nav_next_action.triggered.connect(lambda: self.canvas.goto_page(self.canvas.current_page + 1))
        tb.addAction(self._page_nav_next_action)

        self._dup_action = big_action("❏ Duplicate", lambda: self.canvas.duplicate_selected())
        self._del_action = big_action("🗑 Delete", lambda: self.canvas.remove_selected())

        self._properties_separator_action = tb.addSeparator()

        # Color button
        self._color_btn = QPushButton("●")
        self._color_btn.setFixedSize(38, 38)
        self._color_btn.setToolTip("Annotation color")
        self._color_btn.clicked.connect(self._pick_color)
        self._update_color_btn()
        self._color_btn_action = tb.addWidget(self._color_btn)

        # v1.2.22: Line width spinner (for vector annotations)
        self._width_label = QLabel("Width:")
        self._width_label_action = tb.addWidget(self._width_label)
        self._width_spinner = QDoubleSpinBox()
        self._width_spinner.setMinimum(0.5)
        self._width_spinner.setMaximum(16.0)
        self._width_spinner.setSingleStep(0.5)
        self._width_spinner.setValue(DEFAULT_LINE_WIDTH_PT)
        self._width_spinner.setDecimals(1)
        self._width_spinner.setMaximumWidth(60)
        self._width_spinner.setToolTip("Line width in points")
        self._width_spinner.valueChanged.connect(self._on_width_changed)
        self._width_spinner_action = tb.addWidget(self._width_spinner)

        # v1.2.22: Font size spinner (for text annotations)
        self._font_size_label = QLabel("Font Size:")
        self._font_size_label_action = tb.addWidget(self._font_size_label)
        self._font_size_spinner = QSpinBox()
        self._font_size_spinner.setMinimum(6)
        self._font_size_spinner.setMaximum(72)
        self._font_size_spinner.setSingleStep(1)
        self._font_size_spinner.setValue(DEFAULT_TEXT_FONT_PT)
        self._font_size_spinner.setMaximumWidth(60)
        self._font_size_spinner.setToolTip("Font size in points")
        self._font_size_spinner.valueChanged.connect(self._on_font_size_changed)
        self._font_size_spinner_action = tb.addWidget(self._font_size_spinner)

        # v1.2.22: Font family combo (for text annotations)
        self._font_label = QLabel("Font:")
        self._font_label_action = tb.addWidget(self._font_label)
        self._font_family_combo = QComboBox()
        self._font_family_combo.addItems(self._get_system_fonts())
        self._font_family_combo.setCurrentText(DEFAULT_FONT_FAMILY)
        self._font_family_combo.setMaximumWidth(120)
        self._font_family_combo.setToolTip("Font family")
        self._font_family_combo.currentTextChanged.connect(self._on_font_family_changed)
        self._font_family_combo_action = tb.addWidget(self._font_family_combo)

        self._angle_label = QLabel("Angle:")
        self._angle_label_action = tb.addWidget(self._angle_label)
        self._angle_spinner = QSpinBox()
        self._angle_spinner.setRange(0, 359)
        self._angle_spinner.setSingleStep(1)
        self._angle_spinner.setSuffix("°")
        self._angle_spinner.setMaximumWidth(70)
        self._angle_spinner.setToolTip("Clockwise annotation rotation in degrees")
        self._angle_spinner.valueChanged.connect(self._on_angle_changed)
        self._angle_spinner_action = tb.addWidget(self._angle_spinner)

        self._reset_angle_btn = QToolButton(self)
        self._reset_angle_btn.setText("↺")
        self._reset_angle_btn.setToolTip("Reset rotation to 0°")
        self._reset_angle_btn.clicked.connect(lambda: self._angle_spinner.setValue(0))
        self._reset_angle_action = tb.addWidget(self._reset_angle_btn)

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
        open_document_action = self._hamburger_file_menu.addAction("Open Document…\tO", self.open_document)
        open_document_action.setShortcut("O")
        self._save_as_file_action = self._hamburger_file_menu.addAction("Save As…\tS", self.save_document_as)
        self._save_as_file_action.setShortcut("S")
        self._hamburger_file_menu.addSeparator()
        self._save_project_action = self._hamburger_file_menu.addAction("Save Project", lambda: self.save_project())
        self._save_project_as_action = self._hamburger_file_menu.addAction("Save Project As…", lambda: self.save_project_as())
        self._change_document_action = self._hamburger_file_menu.addAction("Change Document…", lambda: self.change_document())
        self._auto_save_project_action = self._hamburger_file_menu.addAction("Auto-save Project on Save", self._toggle_auto_save_project)
        self._auto_save_project_action.setCheckable(True)
        self._auto_save_project_action.setChecked(self._settings.auto_save_project)
        self._hamburger_file_menu.addSeparator()
        self._print_action = self._hamburger_file_menu.addAction("Print\tP", self.print_document)
        self._print_action.setShortcut("P")
        self._hamburger_file_menu.addSeparator()
        self._file_recent_docs_actions = []  # Track recent doc actions for rebuilding
        self._rebuild_file_recent_documents_top_level(self._hamburger_file_menu)
        self._hamburger_file_menu.addSeparator()
        self._hamburger_file_menu.addAction("Exit", self.close)
        self._hamburger_file_menu.aboutToShow.connect(self._update_menu_state)

        # Edit menu
        edit_menu = hamburger_menu.addMenu("Edit")
        self._menu_undo_action = edit_menu.addAction("Undo\tZ", self.undo)
        self._menu_undo_action.setShortcut("Z")
        self._menu_redo_action = edit_menu.addAction("Redo\tY", self.redo)
        self._menu_redo_action.setShortcut("Y")
        edit_menu.addSeparator()
        self._menu_cut_action = edit_menu.addAction("Cut\tX", self.canvas.cut_selected)
        self._menu_cut_action.setShortcut("X")
        self._menu_copy_action = edit_menu.addAction("Copy\tC", self.canvas.copy_selected)
        self._menu_copy_action.setShortcut("C")
        self._menu_paste_action = edit_menu.addAction("Paste\tV", self.canvas.paste_selected)
        self._menu_paste_action.setShortcut("V")
        self._menu_duplicate_action = edit_menu.addAction("Duplicate\tD", self.canvas.duplicate_selected)
        self._menu_duplicate_action.setShortcut("D")
        edit_menu.addSeparator()
        self._menu_select_all_action = edit_menu.addAction("Select All\tA", self.canvas.select_all_on_page)
        self._menu_select_all_action.setShortcut("A")
        self._menu_delete_action = edit_menu.addAction("Delete", self.canvas.remove_selected)
        edit_menu.addSeparator()
        self._menu_rotate_page_left_action = edit_menu.addAction("Rotate Current Page Left\tShift+L", self.canvas.rotate_current_page_left)
        self._menu_rotate_page_left_action.setShortcut("Shift+L")
        self._menu_rotate_page_right_action = edit_menu.addAction("Rotate Current Page Right\tShift+R", self.canvas.rotate_current_page_right)
        self._menu_rotate_page_right_action.setShortcut("Shift+R")
        edit_menu.addSeparator()
        self._menu_rotate_all_left_action = edit_menu.addAction("Rotate All Pages Left\tL", self.canvas.rotate_all_pages_left)
        self._menu_rotate_all_left_action.setShortcut("L")
        self._menu_rotate_all_right_action = edit_menu.addAction("Rotate All Pages Right\tR", self.canvas.rotate_all_pages_right)
        self._menu_rotate_all_right_action.setShortcut("R")
        edit_menu.aboutToShow.connect(self._update_menu_state)

        # Annotations menu
        annotations_menu = hamburger_menu.addMenu("Annotations")
        self._hamburger_annotations_menu = annotations_menu
        self._populate_annotation_type_actions(annotations_menu)
        
        self._hamburger_text_submenu = annotations_menu.addMenu("Text")
        self._hamburger_text_submenu.addAction("Free text…", lambda: self._add_text_annotation(""))
        self._hamburger_text_submenu.addAction("Current date", lambda: self._add_text_annotation(self._locale_date()))
        self._hamburger_text_submenu.addAction("Current time", lambda: self._add_text_annotation(self._locale_time()))
        self._hamburger_text_submenu.addAction("Current date & time", lambda: self._add_text_annotation(self._locale_datetime()))
        self._hamburger_text_submenu.addSeparator()
        self._annotations_recent_text_actions = []  # Track recent text actions for rebuilding
        self._rebuild_recent_texts_top_level(self._hamburger_text_submenu)
        
        # v1.2.22: Rename to Signature/Image
        annotations_menu.addAction("Signature / Image", self._add_signature_from_file)

        # Tools menu: standalone utilities that don't operate on the currently open document
        tools_menu = hamburger_menu.addMenu("Tools")
        tools_menu.addAction("Prepare Signature…", self._open_prepare_signature_tool)

        # Help menu
        help_menu = hamburger_menu.addMenu("Help")
        help_menu.addAction("Homepage", lambda: QDesktopServices.openUrl(QUrl("https://github.com/jmalenko/signer")))

        tb.addWidget(hamburger)
        
        # Initial rebuild of recent menus
        self._rebuild_recent_menus()
        
        # Update UI state after all controls are created
        self._update_annotation_action_state()
        self._update_document_workflow_state()
        self._update_menu_state()

    def show_annotation_menu(self) -> None:
        """Open the toolbar annotation menu from a keyboard shortcut."""
        if self._add_annotation_btn.isEnabled():
            self._add_annotation_btn.showMenu()

    def _populate_annotation_type_actions(self, menu: QMenu, with_icons: bool = False) -> None:
        """Add the shared vector annotation commands to an annotation menu."""
        labels = {
            AnnotationType.CHECKMARK: "✔ Checkmark" if with_icons else "Checkmark",
            AnnotationType.CROSSMARK: "✖ Crossmark" if with_icons else "Crossmark",
            AnnotationType.LINE: "— Line" if with_icons else "Line",
            AnnotationType.ARROW: "➡ Arrow" if with_icons else "Arrow",
            AnnotationType.RECTANGLE: "▭ Rectangle / Square" if with_icons else "Rectangle / Square",
            AnnotationType.ELLIPSE: "○ Ellipse / Circle" if with_icons else "Ellipse / Circle",
        }
        for annotation_type, label in labels.items():
            menu.addAction(
                label,
                lambda checked=False, ann_type=annotation_type: self._add_vector(ann_type),
            )

    def _update_menu_state(self) -> None:
        """Enable/disable hamburger menu items based on document/selection/history state."""
        has_doc = self.canvas.has_document
        has_selection = self.canvas.selected is not None
        has_page_objects = has_doc and bool(self.canvas.current_page_objects())
        can_paste = has_doc and self.canvas.has_pasteable_data()

        if self._auto_save_project_action is not None:
            self._set_value_silently(
                self._auto_save_project_action, self._settings.auto_save_project, setter="setChecked"
            )

        # Declarative action -> enabled-condition mapping so adding a new menu
        # action doesn't require another `if action is not None: action.setEnabled(...)` block.
        rotation_actions = (
            self._menu_rotate_page_left_action,
            self._menu_rotate_page_right_action,
            self._menu_rotate_all_left_action,
            self._menu_rotate_all_right_action,
        )
        action_conditions = [
            (self._print_action, has_doc),
            (self._menu_undo_action, self.canvas.can_undo()),
            (self._menu_redo_action, self.canvas.can_redo()),
            (self._menu_cut_action, has_selection),
            (self._menu_copy_action, has_selection),
            (self._menu_paste_action, can_paste),
            (self._menu_duplicate_action, has_selection),
            (self._menu_select_all_action, has_page_objects),
            (self._menu_delete_action, has_selection),
            *((action, has_doc) for action in rotation_actions),
        ]
        for action, enabled in action_conditions:
            if action is not None:
                action.setEnabled(enabled)

    def _update_document_workflow_state(self) -> None:
        """Enable/disable document-dependent workflow controls."""
        has_doc = self.canvas.has_document

        if self._add_annotation_btn is not None:
            self._add_annotation_btn.setEnabled(has_doc)
        if self._save_as_toolbar_action is not None:
            self._save_as_toolbar_action.setEnabled(has_doc)
        if self._save_as_file_action is not None:
            self._save_as_file_action.setEnabled(has_doc)
        if self._hamburger_annotations_menu is not None:
            self._hamburger_annotations_menu.menuAction().setEnabled(has_doc)

        self._update_page_navigation_visibility()

    def _update_page_navigation_visibility(self) -> None:
        """Hide page navigation controls when the current document has a single page."""
        show_navigation = self.canvas.has_document and self.canvas.page_count > 1

        if self._page_nav_prev_action is not None:
            self._page_nav_prev_action.setVisible(show_navigation)
        if self._page_nav_next_action is not None:
            self._page_nav_next_action.setVisible(show_navigation)
        if self._page_nav_label is not None:
            self._page_nav_label.setVisible(show_navigation)
        if getattr(self, "_page_nav_label_action", None) is not None:
            self._page_nav_label_action.setVisible(show_navigation)

        self._update_page_nav_separator_visibility()
        self._refresh_toolbar_layout()

    def _update_page_nav_separator_visibility(self) -> None:
        """Show the separator after Save As only if page nav or Duplicate/Delete are visible."""
        separator = getattr(self, "_page_nav_separator_action", None)
        if separator is None:
            return
        show_navigation = self.canvas.has_document and self.canvas.page_count > 1
        has_selection = self.canvas.selected is not None
        separator.setVisible(show_navigation or has_selection)

    def _refresh_toolbar_layout(self) -> None:
        """Force the toolbar to repaint after widget visibility changes."""
        toolbar = getattr(self, "_main_toolbar", None)
        if toolbar is None:
            return
        toolbar.update()

    def _rebuild_sig_ann_menu(self) -> None:
        if self._sig_ann_menu is None:
            return
        self._sig_ann_menu.clear()
        self._sig_ann_menu.addAction("From file…", self._add_signature_from_file)
        paths = self._settings.recent_signature_paths
        if paths:
            self._sig_ann_menu.addSeparator()
            self._rebuild_menu_items(
                self._sig_ann_menu, [], paths,
                label_fn=lambda p: Path(p).name,
                callback=lambda p: self._load_signature_file(p, at_default_position=False),
            )

    @staticmethod
    def _truncate_for_menu(text: str, max_len: int = 50) -> str:
        return text[:max_len] + "…" if len(text) > max_len else text

    @staticmethod
    def _rebuild_menu_items(menu: QMenu, tracked_actions: list, items: list, label_fn, callback) -> list:
        """Remove previously-tracked actions from `menu`, then add one action per
        item in `items` (calling `callback(item)` when triggered). Returns the new
        list of tracked actions for the caller to store and pass in next time.
        """
        for act in tracked_actions:
            menu.removeAction(act)
        return [
            menu.addAction(label_fn(item), lambda checked=False, i=item: callback(i))
            for item in items
        ]

    def _rebuild_tracked_menu_section(self, menu: QMenu, tracked_actions: list, items: list, label_fn, callback) -> list:
        """Like `_rebuild_menu_items`, but also manages a leading separator: adds one
        before the item actions when `items` is non-empty, and tracks/removes it
        along with them. Used for recent-items sections appended after static menu
        items (e.g. recent documents at the bottom of the File menu).
        """
        for act in tracked_actions:
            menu.removeAction(act)
        if not items:
            return []
        return [menu.addSeparator()] + self._rebuild_menu_items(menu, [], items, label_fn, callback)

    def _rebuild_recent_documents_menu(self) -> None:
        """Rebuild the recent documents menu in the toolbar."""
        if not hasattr(self, '_recent_docs_menu') or self._recent_docs_menu is None:
            return
        self._recent_docs_menu.clear()
        paths = self._settings.recent_document_paths
        if paths:
            self._rebuild_menu_items(
                self._recent_docs_menu, [], paths,
                label_fn=lambda p: Path(p).name,
                callback=self.open_document,
            )
        else:
            act = self._recent_docs_menu.addAction("(none)")
            act.setEnabled(False)

    def _rebuild_file_recent_documents_top_level(self, file_menu: QMenu) -> None:
        """Rebuild recent documents at the top level of File menu, after static items, separated by a horizontal rule."""
        self._file_recent_docs_actions = self._rebuild_tracked_menu_section(
            file_menu, self._file_recent_docs_actions,
            self._settings.recent_document_paths,
            label_fn=lambda p: Path(p).name,
            callback=self.open_document,
        )

    def _rebuild_recent_texts_top_level(self, text_submenu: QMenu) -> None:
        """Rebuild recent texts at the top level of Text submenu, after static items, separated by a horizontal rule."""
        self._annotations_recent_text_actions = self._rebuild_tracked_menu_section(
            text_submenu, self._annotations_recent_text_actions,
            self._settings.recent_text_strings,
            label_fn=self._truncate_for_menu,
            callback=self._add_text_annotation,
        )

    def _rebuild_toolbar_recent_texts(self) -> None:
        """Rebuild recent texts in the toolbar's Text menu."""
        if not hasattr(self, '_toolbar_text_menu') or self._toolbar_text_menu is None:
            return
        self._toolbar_recent_text_actions = self._rebuild_menu_items(
            self._toolbar_text_menu, self._toolbar_recent_text_actions,
            self._settings.recent_text_strings,
            label_fn=self._truncate_for_menu,
            callback=self._add_text_annotation,
        )

    def _rebuild_recent_menus(self) -> None:
        """Rebuild all recent items menus."""
        self._rebuild_recent_documents_menu()
        self._rebuild_sig_ann_menu()
        self._rebuild_toolbar_recent_texts()
        # Rebuild top-level recent items in hamburger menus
        if self._hamburger_file_menu is not None:
            self._rebuild_file_recent_documents_top_level(self._hamburger_file_menu)
        if self._hamburger_text_submenu is not None:
            self._rebuild_recent_texts_top_level(self._hamburger_text_submenu)

    def _on_object_changed(self) -> None:
        self._update_document_workflow_state()
        self._update_annotation_action_state()
        self._update_menu_state()
        self._update_color_btn()
        self._has_unsaved_changes = True

    @staticmethod
    def _set_value_silently(widget, value, setter: str = "setValue") -> None:
        """Call widget.<setter>(value) with signals blocked, to avoid triggering
        the widget's own valueChanged/toggled handler while syncing UI state."""
        widget.blockSignals(True)
        getattr(widget, setter)(value)
        widget.blockSignals(False)

    def _update_annotation_action_state(self) -> None:
        """Show/hide and sync the selection-dependent toolbar controls (Duplicate/Delete,
        color, width, font, angle) for the currently selected annotation(s)."""
        selected = self.canvas.selected
        has_selection = selected is not None
        self._dup_action.setEnabled(has_selection)
        self._del_action.setEnabled(has_selection)
        self._dup_action.setVisible(has_selection)
        self._del_action.setVisible(has_selection)

        color_visible = self._update_color_control_visibility(selected, has_selection)
        width_visible = self._update_width_control_visibility(selected, has_selection)
        font_visible = self._update_font_control_visibility(selected, has_selection)
        angle_visible = self._update_angle_control_visibility(selected, has_selection)

        # Single separator before the whole property group; shown only if something in it is visible.
        self._properties_separator_action.setVisible(
            color_visible or width_visible or font_visible or angle_visible
        )

        self._update_page_nav_separator_visibility()

        # Keep property controls consistent when no selection remains.
        if not has_selection:
            self._update_color_btn()

        self._refresh_toolbar_layout()

    def _update_color_control_visibility(self, selected, has_selection: bool) -> bool:
        """Color control applies to vector annotations only; Signature/Image has no color control."""
        color_visible = has_selection and isinstance(selected, VectorAnnotation)
        self._color_btn.setVisible(color_visible)
        self._color_btn.setEnabled(color_visible)
        self._color_btn_action.setVisible(color_visible)
        return color_visible

    def _update_width_control_visibility(self, selected, has_selection: bool) -> bool:
        """Width spinner/label: visible for vector types except TEXT (v1.2.22)."""
        width_visible = (
            has_selection and
            isinstance(selected, VectorAnnotation) and
            selected.ann_type != AnnotationType.TEXT
        )
        self._width_spinner.setVisible(width_visible)
        self._width_label.setVisible(width_visible)
        self._width_spinner_action.setVisible(width_visible)
        self._width_label_action.setVisible(width_visible)
        if width_visible:
            # Reflect the selected annotation's actual width (e.g. after a [ / ] shortcut).
            self._set_value_silently(self._width_spinner, selected._line_width_pt)
        return width_visible

    def _update_font_control_visibility(self, selected, has_selection: bool) -> bool:
        """Font size/family controls: visible only for TEXT annotations (v1.2.22)."""
        font_visible = (
            has_selection and
            isinstance(selected, VectorAnnotation) and
            selected.ann_type == AnnotationType.TEXT
        )
        self._font_size_spinner.setVisible(font_visible)
        self._font_size_label.setVisible(font_visible)
        if font_visible:
            # Reflect the selected annotation's actual font size (e.g. after a [ / ] shortcut).
            self._set_value_silently(self._font_size_spinner, selected._font_size_pt)
        self._font_family_combo.setVisible(font_visible)
        self._font_label.setVisible(font_visible)
        self._font_size_spinner_action.setVisible(font_visible)
        self._font_size_label_action.setVisible(font_visible)
        self._font_family_combo_action.setVisible(font_visible)
        self._font_label_action.setVisible(font_visible)
        return font_visible

    def _update_angle_control_visibility(self, selected, has_selection: bool) -> bool:
        """Angle spinner/reset: visible for any selected annotation (all types support rotation)."""
        angle_visible = has_selection
        self._angle_label.setVisible(angle_visible)
        self._angle_spinner.setVisible(angle_visible)
        self._reset_angle_btn.setVisible(angle_visible)
        self._angle_label_action.setVisible(angle_visible)
        self._angle_spinner_action.setVisible(angle_visible)
        self._reset_angle_action.setVisible(angle_visible)
        if angle_visible:
            self._set_value_silently(self._angle_spinner, round(selected.rotation) % 360)
        return angle_visible

    def _on_page_changed(self, current: int, total: int) -> None:
        self._update_document_workflow_state()
        self._update_menu_state()
        if self._page_nav_label is not None:
            if total > 0:
                self._page_nav_label.setText(f"  Page {current + 1} / {total}  ")
            else:
                self._page_nav_label.setText("  Page — / —  ")

    def _on_edit_requested(self, obj: object) -> None:
        from .objects import CanvasObject, VectorAnnotation
        if not isinstance(obj, CanvasObject):
            return
        if isinstance(obj, VectorAnnotation) and obj.ann_type == AnnotationType.TEXT:
            dlg = _TextInputDialog(self, "Edit Text", obj.text)
            if dlg.exec() == QDialog.Accepted:
                from .history import SetTextAnnotationAction
                new_text = dlg.text()
                old_text = obj.text
                if new_text != old_text:
                    obj_id = self.canvas._stable_id_for(obj)
                    action = SetTextAnnotationAction(object_id=obj_id, text=new_text, from_text=old_text)
                    self.canvas.history.record_action(action)
                obj.text = new_text
                if hasattr(obj, "fit_text_box"):
                    obj.fit_text_box()
                self.canvas.objectChanged.emit()
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

    def _on_angle_changed(self, value: int) -> None:
        """Rotate the current selection around its shared center."""
        self.canvas.rotate_selected_to(value)

    # v1.2.22: Line width, font size, and font family handlers
    def _on_width_changed(self, value: float) -> None:
        """Handle line width spinner changes."""
        selected = self.canvas.selected
        if selected is not None and isinstance(selected, VectorAnnotation):
            from .objects import AnnotationType
            # Only allow width change for vector types that support it
            if selected.ann_type != AnnotationType.TEXT:
                self.canvas.set_line_width_selected(value)
                self._settings.recent_line_width_pt = value
                self._save_settings_safe()

    def _on_font_size_changed(self, value: int) -> None:
        """Handle font size spinner changes."""
        selected = self.canvas.selected
        if (
            selected is not None
            and isinstance(selected, VectorAnnotation)
            and selected.ann_type == AnnotationType.TEXT
        ):
            self.canvas.set_font_size_selected(value)
            self._settings.recent_font_size_pt = value
            self._save_settings_safe()

    def _on_font_family_changed(self, family: str) -> None:
        """Handle font family combo changes."""
        selected = self.canvas.selected
        if (
            selected is not None
            and isinstance(selected, VectorAnnotation)
            and selected.ann_type == AnnotationType.TEXT
        ):
            self.canvas.set_font_family_selected(family)
            self._settings.recent_font_family = family
            self._save_settings_safe()

    @staticmethod
    def _get_system_fonts() -> list[str]:
        """Get list of available system fonts."""
        from PySide6.QtGui import QFontDatabase
        db = QFontDatabase()
        # Get common system fonts; default to all if available
        fonts = sorted(db.families())
        # Return common fonts if available, otherwise all
        common = ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Georgia"]
        if all(f in fonts for f in common):
            return common + [f for f in fonts if f not in common]
        return fonts[:50]  # Limit to 50 fonts if very large list

    # ---------------------------------------------------------------- date/time helpers

    @staticmethod
    def _ensure_locale_set() -> None:
        try:
            locale.setlocale(locale.LC_TIME, "")
        except locale.Error:
            logger.debug("Could not set the system locale for date/time formatting", exc_info=True)

    @staticmethod
    def _locale_date() -> str:
        MainWindow._ensure_locale_set()
        return datetime.now(timezone.utc).astimezone().strftime("%x")

    @staticmethod
    def _locale_time() -> str:
        MainWindow._ensure_locale_set()
        return datetime.now(timezone.utc).astimezone().strftime("%X")

    @staticmethod
    def _locale_datetime() -> str:
        MainWindow._ensure_locale_set()
        return datetime.now(timezone.utc).astimezone().strftime("%x %X")

    # ---------------------------------------------------------------- annotation actions

    def _ensure_document_open(self) -> bool:
        """Show a warning and return False if no document is open; True otherwise."""
        if not self.canvas.has_document:
            QMessageBox.warning(self, "No document", "Open a document first.")
            return False
        return True

    def _add_vector(self, ann_type: AnnotationType) -> None:
        if not self._ensure_document_open():
            return
        obj = VectorAnnotation(
            ann_type, 0, 0, self.canvas.current_page,
            font_family=self._settings.recent_font_family,
            font_size_pt=self._settings.recent_font_size_pt,
            line_width_pt=self._settings.recent_line_width_pt,
        )
        obj.color = QColor(self._current_color)
        x, y = self.canvas.default_position_for(obj)
        obj.x, obj.y = x, y
        self.canvas.add_object(obj)

    def _add_text_annotation(self, preset_text: str) -> None:
        if not self._ensure_document_open():
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
            font_size_pt=self._settings.recent_font_size_pt,
            line_width_pt=self._settings.recent_line_width_pt,
        )
        obj.color = QColor(self._current_color)
        x, y = self.canvas.default_position_for(obj)
        obj.x, obj.y = x, y
        self.canvas.add_object(obj)

    def _add_signature_from_file(self) -> None:
        start_dir = ""
        if self._settings.recent_signature_paths:
            start_dir = str(Path(self._settings.recent_signature_paths[0]).parent)
        elif self._settings.recent_document_paths:
            start_dir = str(Path(self._settings.recent_document_paths[0]).parent)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Signature", start_dir,
            "Image files (*.png *.jpg *.jpeg);;All files (*.*)",
        )
        if path:
            self._load_signature_file(path, at_default_position=False)

    def _open_prepare_signature_tool(self) -> None:
        dialog = PrepareSignatureDialog(self)
        dialog.exec()

    # ---------------------------------------------------------------- open/save

    @staticmethod
    def _project_path_for_document(document_path: str | Path) -> Path:
        return Path(document_path).with_suffix(".signer")

    @staticmethod
    def _project_path_for_export(export_path: str | Path) -> Path:
        export = Path(export_path)
        stem = re.sub(r"-p#$", "", export.stem, flags=re.IGNORECASE)
        return export.with_name(f"{stem}.signer")

    def _toggle_auto_save_project(self, checked: bool | None = None) -> None:
        if checked is None:
            checked = self._auto_save_project_action.isChecked()
        self._settings.auto_save_project = checked
        self._save_settings_safe()

    def save_project_as(self) -> bool:
        if not self.canvas.has_document or not self.document_path:
            return False
        suggested = self.project_path or self._project_path_for_export(
            self._last_export_path or self.document_path
        )
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", str(suggested), "Signer Projects (*.signer);;All files (*.*)"
        )
        if not chosen:
            return False
        path = Path(chosen)
        if not path.name.lower().endswith(".signer"):
            path = path.with_name(path.name + ".signer")
        return self.save_project(path)

    def save_project(
        self,
        path: str | Path | None = None,
        silent: bool = False,
        mark_clean: bool = True,
    ) -> bool:
        if not self.canvas.has_document or not self.document_path:
            return False
        if path:
            target = Path(path)
        elif self.project_path:
            target = Path(self.project_path)
        else:
            return self.save_project_as()
        project = ProjectFile.from_annotations(
            document_path=self.document_path,
            export_path=self._last_export_path,
            annotations=[obj for page in range(self.canvas.page_count) for obj in self.canvas.page_objects_at(page)],
            current_page=self.canvas.current_page,
            page_count=self.canvas.page_count,
        )
        project["rotations"] = dict(self.canvas._page_rotations)
        try:
            self._saving_project = True
            ProjectFile.write(target, project)
        except (OSError, TypeError, ValueError) as exc:
            if not silent:
                QMessageBox.critical(self, "Save Project failed", f"Could not save project:\n{exc}")
            return False
        finally:
            self._saving_project = False
        self.project_path = str(target)
        if mark_clean:
            self._has_unsaved_changes = False
        if not silent and not self._in_test_mode:
            self.show_notification(f"Saved project {target.name}")
        return True

    def change_document(self) -> bool:
        if not self.canvas.has_document:
            return self.open_document()
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Change Document", str(Path(self.document_path).parent) if self.document_path else "",
            "All Supported Files (*.pdf *.docx *.doc *.odt *.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tiff *.tif)"
        )
        if not chosen:
            return False
        objects = [obj for page in range(self.canvas.page_count) for obj in self.canvas.page_objects_at(page)]
        if not self._load_document_pages(Path(chosen)):
            return False
        self.canvas.restore_objects(objects, {}, 0)
        # Keep the current project path only when this document belongs to an
        # already-opened project. A new document gets its project identity from
        # the eventual export path.
        self._has_unsaved_changes = True
        return True

    def open_project(self, path: str | Path, check_unsaved_changes: bool = True) -> bool:
        if (
            check_unsaved_changes
            and self.document_path
            and self._has_unsaved_changes
            and not self._check_unsaved_changes()
        ):
            return False
        try:
            project = ProjectFile.read(path)
            ProjectFile.validate(project)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            QMessageBox.critical(self, "Open project failed", str(exc))
            return False
        document_path = Path(project.get("document_path", ""))
        if not document_path.is_absolute():
            sidecar_path = Path(path).parent / document_path
            document_path = sidecar_path if sidecar_path.exists() else document_path
        if not document_path.exists():
            if self._in_test_mode:
                return False
            choice = QMessageBox.warning(
                self, "Document not found",
                "The project document is unavailable. Choose Change Document to continue.",
                QMessageBox.Cancel | QMessageBox.Open,
                QMessageBox.Open,
            )
            if choice != QMessageBox.Open:
                return False
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Change Document", str(Path(path).parent),
                "All Supported Files (*.pdf *.docx *.doc *.odt *.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tiff *.tif)"
            )
            if not chosen:
                return False
            document_path = Path(chosen)
        if not self._load_document_pages(document_path):
            return False
        try:
            objects = ProjectFile.load_annotations(project, Path(path).parent)
        except (KeyError, TypeError, ValueError) as exc:
            QMessageBox.critical(self, "Open project failed", f"Invalid annotation data:\n{exc}")
            return False
        rotations = project.get("rotations", {})
        self.canvas.restore_objects(objects, rotations, 0)
        self.project_path = str(path)
        self._update_recent_documents(str(path))
        self._save_settings_safe()
        self._rebuild_recent_menus()
        self._has_unsaved_changes = False
        self._update_title()
        self._update_document_workflow_state()
        return True

    def _load_document_pages(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            pages = render_all_pages(path, password="", libreoffice_path=self._settings.libreoffice_path)
        except (OSError, RuntimeError, ValueError) as exc:
            QMessageBox.critical(self, "Open document failed", f"Could not open document:\n{exc}")
            return False
        self.canvas.set_pages(pages)
        self.canvas.clear_history()
        self.document_path = str(path)
        self._update_recent_documents(str(path))
        self._save_settings_safe()
        if pages:
            self._adjust_window_to_document(pages[0].size[0], pages[0].size[1])
        self._focus_canvas_after_open()
        return True

    def _focus_canvas_after_open(self) -> None:
        """Restore keyboard focus after a document or project dialog closes."""
        self.raise_()
        self.activateWindow()
        self.canvas.setFocus(Qt.OtherFocusReason)
        QTimer.singleShot(0, self._focus_canvas_deferred)

    def _focus_canvas_deferred(self) -> None:
        self.raise_()
        self.activateWindow()
        self.canvas.setFocus(Qt.OtherFocusReason)

    def open_document(self, path: str | None = None) -> bool:
        # Check for unsaved changes before opening a new document
        if self.document_path and self._has_unsaved_changes and not self._check_unsaved_changes():
            return False
        
        chosen = path
        if not chosen:
            start_dir = ""
            if self.document_path:
                start_dir = str(Path(self.document_path).parent)
            elif self._settings.recent_document_paths:
                start_dir = str(Path(self._settings.recent_document_paths[0]).parent)
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Open Document", start_dir,
                "All Supported Files (*.pdf *.docx *.doc *.odt *.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tiff *.tif *.signer);;"
                "PDF Files (*.pdf);;Word Documents (*.docx *.doc);;OpenDocument Text (*.odt);;"
                "Image Files (*.jpg *.jpeg *.png *.bmp *.webp *.gif *.ico *.tiff *.tif);;"
                "Project Files (*.signer)"
            )

        if not chosen:
            return False
        p = Path(chosen)

        if p.name.lower().endswith(".signer"):
            return self.open_project(p, check_unsaved_changes=False)

        if not p.exists():
            QMessageBox.critical(self, "Open document failed", f"File not found:\n{p}")
            self._remove_recent_document(str(p))
            return False

        password = ""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                pages = render_all_pages(
                    p,
                    password=password,
                    libreoffice_path=self._settings.libreoffice_path,
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
            except (OSError, RuntimeError) as exc:
                QMessageBox.critical(self, "Open document failed", f"Could not open document:\n{exc}")
                return False
            break  # Success
        else:
            # Max attempts exceeded
            QMessageBox.critical(self, "Open document failed", "Incorrect password or maximum attempts exceeded.")
            return False

        self.canvas.set_pages(pages)
        self.canvas.clear_history()  # Clear undo/redo history when opening a new document
        self.document_path = str(p)
        self.project_path = None
        self._has_unsaved_changes = False
        self._update_recent_documents(str(p))
        self._save_settings_safe()
        if pages:
            self._adjust_window_to_document(pages[0].size[0], pages[0].size[1])
        self._update_title()
        self._rebuild_recent_menus()
        self._update_document_workflow_state()
        self._update_annotation_action_state()
        self._update_color_btn()
        return True

    def _on_file_drop(self, file_path: str) -> None:
        """Handle file drop from drag-and-drop.
        
        Determines if the dropped file is a small image (creates annotation)
        or a document (opens as new document).
        """
        file_path_obj = Path(file_path)
        
        # Check if file exists
        if not file_path_obj.exists():
            QMessageBox.critical(self, "File Error", f"File not found: {file_path}")
            return
        
        # Determine file type by extension
        ext = file_path_obj.suffix.lower()
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
        document_extensions = {'.pdf'} | image_extensions
        
        if ext not in document_extensions:
            QMessageBox.critical(
                self, 
                "Unsupported File Format",
                f"Cannot open file: Unsupported format or corrupted file.\n\nFile: {file_path_obj.name}"
            )
            return
        
        # Check if it's an image or document
        is_image = ext in image_extensions
        is_small_image = False
        
        if is_image:
            is_small_image = self._is_small_image(file_path)
        
        # Handle small image drop
        if is_small_image:
            self._handle_small_image_drop(file_path)
        else:
            # Handle big image or PDF drop (document load)
            self._handle_document_drop(file_path)
    
    def _is_small_image(self, file_path: str) -> bool:
        """Check if image fits on A6 paper at 300 DPI (1240 × 1748 pixels).
        
        A6 dimensions: 105mm × 148mm (4.1" × 5.8")
        At 300 DPI: 1240 × 1748 pixels
        Small image: max(width, height) ≤ 1748 pixels (fits A6 in any orientation)
        """
        try:
            img = Image.open(file_path)
            width, height = img.size
            # A6 at 300 DPI: 1240 × 1748 pixels
            # Allow both orientations - image must fit on A6 in either orientation
            a6_max_dimension = 1748
            return max(width, height) <= a6_max_dimension
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            logger.error("Error checking image size: %s", exc)
            return False
    
    def _handle_small_image_drop(self, file_path: str) -> None:
        """Handle dropping a small image - create Signature/Image annotation at drop position."""
        if not self.canvas.has_document:
            QMessageBox.critical(
                self,
                "No Document Open",
                "Cannot drop image: No document is currently open. Please open or create a document first."
            )
            return
        
        try:
            img = Image.open(file_path)
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Image Load Error",
                f"Cannot load image: Unsupported format or corrupted file.\n\nSupported formats: PNG, JPG, JPEG, BMP.\n\nError: {exc}"
            )
            return
        
        # Create Signature/Image annotation at center of current page (default position)
        # This uses the existing signature creation logic
        self._create_dropped_image_annotation(file_path)
    
    def _handle_document_drop(self, file_path: str) -> None:
        """Handle dropping a big image or PDF - open as document."""
        # open_document() will check for unsaved changes using the existing
        # _check_unsaved_changes() dialog (single unified dialog)
        self.open_document(file_path)
    
    def _create_dropped_image_annotation(self, file_path: str) -> None:
        """Create a Signature/Image annotation from the dropped image file at default position."""
        try:
            # Load and convert image to RGBA
            with Image.open(file_path) as img:
                loaded = img.convert("RGBA")
            
            # Create signature object at origin (0, 0) - will be repositioned
            sig_obj = SignatureObject(loaded, str(file_path), 0, 0, self.canvas.current_page)
            sig_obj.color = QColor(self._current_color)
            
            # Get the default position for the object (centered on page)
            x, y = self.canvas.default_position_for(sig_obj)
            sig_obj.x, sig_obj.y = x, y
            
            # Add to current page
            self.canvas.add_object(sig_obj)
            self._has_unsaved_changes = True
            self._update_title()
            self._update_document_workflow_state()
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.error("Error creating dropped image annotation: %s", exc)
            QMessageBox.critical(
                self,
                "Error",
                f"Could not create image annotation:\n{exc}"
            )
    
    def show_notification(self, message: str) -> None:
        """Show a brief non-intrusive notification toast."""
        NotificationToast(self, message)

    def open_signature(self, path: str | None = None) -> bool:
        """Load a signature and place it at the default position on the current page."""
        chosen = path
        if not chosen:
            start_dir = ""
            if self._settings.recent_signature_paths:
                start_dir = str(Path(self._settings.recent_signature_paths[0]).parent)
            elif self._settings.recent_document_paths:
                start_dir = str(Path(self._settings.recent_document_paths[0]).parent)
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
            QMessageBox.warning(self, "Invalid signature", "Signature must be in a supported image format (PNG, JPG, BMP, GIF, TIFF, WebP, etc).")
            return False
        if not p.exists():
            QMessageBox.warning(self, "File not found", f"Signature file not found:\n{p}")
            self._remove_recent_signature(str(p))
            return False
        try:
            with Image.open(p) as img:
                loaded = img.convert("RGBA")
        except (UnidentifiedImageError, OSError) as exc:
            QMessageBox.critical(self, "Open signature failed", f"Could not open signature:\n{exc}")
            return False

        obj = SignatureObject(loaded, str(p), 0, 0, self.canvas.current_page)
        obj.color = QColor(self._current_color)
        # FUNCTIONAL_SPECIFICATION.md #7.7: signatures added via the -signature CLI
        # argument or the Signature submenu default to 80% down the page, not the
        # generic center-of-page position used for other annotation types.
        x, y = self.canvas.default_signature_position_for(obj)
        obj.x, obj.y = x, y

        if self.canvas.has_document:
            self.canvas.add_object(obj)

        self._update_recent_signatures(str(p))
        self._save_settings_safe()
        self._rebuild_sig_ann_menu()
        return True

    def _update_recent_signatures(self, path: str) -> None:
        self._settings.recent_signature_paths = self._update_lru_list(
            self._settings.recent_signature_paths, path
        )

    def _remove_recent_signature(self, path: str) -> None:
        """Prune a signature path (e.g. no longer found on disk) from the recent list."""
        paths = self._settings.recent_signature_paths
        if path in paths:
            paths.remove(path)
            self._settings.recent_signature_paths = paths
            self._save_settings_safe()
            self._rebuild_sig_ann_menu()

    @staticmethod
    def _update_lru_list(items: list, item, max_size: int = MAX_RECENT_ITEMS) -> list:
        """Return `items` with `item` moved to the front (most-recent-first), capped at max_size."""
        if item in items:
            items.remove(item)
        items.insert(0, item)
        return items[:max_size]

    def _update_recent_text_strings(self, text: str) -> None:
        """Add a text string to recent texts (LRU, max 10). Excludes predefined date/time strings."""
        if not text or not text.strip():
            return
        # Exclude predefined date/time strings
        predefined = {self._locale_date(), self._locale_time(), self._locale_datetime()}
        if text in predefined:
            return
        self._settings.recent_text_strings = self._update_lru_list(
            self._settings.recent_text_strings, text
        )

    def _update_recent_documents(self, path: str) -> None:
        """Add a document path to recent documents (LRU, max 10)."""
        self._settings.recent_document_paths = self._update_lru_list(
            self._settings.recent_document_paths, path
        )

    def _remove_recent_document(self, path: str) -> None:
        """Prune a document path (e.g. no longer found on disk) from the recent list."""
        paths = self._settings.recent_document_paths
        if path in paths:
            paths.remove(path)
            self._settings.recent_document_paths = paths
            self._save_settings_safe()
            self._rebuild_recent_menus()

    def save_signed_document(self) -> bool:
        """Deprecated: delegates to save_document_as() for backward compatibility."""
        return self.save_document_as()

    def save_document_as(self) -> bool:
        """Save document in selected format with Save As dialog."""
        # In test mode, skip dialogs that require user interaction
        
        if not self.canvas.has_document:
            if not self._in_test_mode:
                QMessageBox.warning(self, "Missing document", "Open a document first.")
            return False
        if not self.document_path:
            if not self._in_test_mode:
                QMessageBox.warning(self, "Missing document path", "Document path is unavailable.")
            return False

        total = self.canvas.page_count
        if total == 0:
            return False

        any_objects = any(self.canvas.page_objects_at(i) for i in range(total))
        if not any_objects:
            if not self._in_test_mode:
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
            if self._in_test_mode:
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
            # Capture the filename exactly as chosen, before any extension
            # auto-correction below mutates `output` in place. The auto-correct
            # check further down must compare against this original name, not
            # the already-mutated one (otherwise it can never match).
            original_output_name = output.name
            
            # Save user's choice so we can restore it if they cancel overwrite confirmation
            last_user_chosen_path = output
            
            # DETECT FORMAT FROM USER'S ACTIONS
            # First, try to detect from the file extension they typed
            export_format = ExportFormat.from_extension(output.suffix)
            
            # Then, check what filter they selected in the dropdown
            # If they explicitly selected a different format filter, that takes precedence
            filter_based_format = ExportFormat.from_filter_string(selected_filter)
            
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
            
            # Save the detected/finalized format for restoration if user cancels overwrite.
            # Captured only now (not before the filter-override above) so a restore
            # doesn't reintroduce the pre-filter-selection format.
            last_user_chosen_format = export_format
            
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
                if original_output_name == suggested_filename:
                    # Auto-correct: update filename to match new format
                    output = output.parent / suggested_for_new_format
                    # Update tracking for next iteration if needed
                    last_export_format = export_format
                    last_export_folder = str(output.parent)
                    # Keep last_user_chosen_path in sync with the corrected filename,
                    # otherwise the "restore user's choice" branch at the top of the
                    # next iteration would reintroduce the stale, pre-correction name.
                    last_user_chosen_path = output
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
                    if not self._in_test_mode:
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
                    if not self._in_test_mode:
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
            if not self._confirm_overwrite_and_cleanup(output, total, export_format, filename_stem):
                # Don't clear last_user_chosen_path/format - keep them for restoration
                continue  # Go back to file dialog with same values
            
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
                    except (PermissionError, OSError, RuntimeError, TypeError, ValueError) as exc:
                        self._show_save_error_dialog(exc, directory)
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
                    except (PermissionError, OSError, RuntimeError, TypeError, ValueError) as exc:
                        self._show_save_error_dialog(exc, directory)
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
                            if not self._in_test_mode:
                                QMessageBox.critical(
                                    self, "Save failed",
                                    "Insufficient disk space. Free up space and try again."
                                )
                            return False
                        else:
                            failed_pages.append((idx, str(exc)))
                    except (RuntimeError, TypeError, ValueError) as exc:
                        failed_pages.append((idx, str(exc)))
                
                # If some pages failed, show error
                if failed_pages:
                    if not self._in_test_mode:
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
                if not self._in_test_mode:
                    QMessageBox.warning(self, "Nothing to save", "No pages could be saved.")
                return False
            
            # Update settings with last export format and folder
            self._settings.last_export_format = export_format.value
            self._settings.last_export_folder = str(directory)
            self._settings.last_save_directory = str(directory)
            self._save_settings_safe()
            self._last_export_path = str(output)
            self._has_unsaved_changes = False

            if self._settings.auto_save_project:
                self.save_project(self._project_path_for_export(self._last_export_path or output), silent=True, mark_clean=False)
            
            # Show auto-dismissing notification with clickable directory link
            if not self._in_test_mode:
                if total == 1:
                    # Single-page: show filename
                    filename = output.name
                    message = f"Exported {filename} to "
                else:
                    # Multi-page: show pattern with placeholder
                    message = f"Exported {filename_stem}{export_format.extension()} to "
                
                NotificationToast(self, message, directory, exported_files=exported_files)
            
            return True
        
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            QMessageBox.critical(self, "Save failed", f"Unexpected error:\n{exc}")
            return False

    def _confirm_overwrite_and_cleanup(
        self, output: Path, total: int, export_format: ExportFormat, filename_stem: str
    ) -> bool:
        """Show an overwrite confirmation dialog if any target files already exist.

        Returns True if the export should proceed (nothing to overwrite, running in
        test mode, or the user confirmed), False if the user cancelled (caller
        should return to the save dialog to let them pick a different name).
        Deletes older per-page files first if the user opted into cleanup.
        """
        existing_files = detect_existing_files(output, total, export_format, filename_stem)
        older_files = detect_older_page_files(output.parent, filename_stem, total, export_format)

        if not existing_files or self._in_test_mode:
            return True

        dialog_title, dialog_message, show_cleanup_checkbox = build_overwrite_dialog_info(
            existing_files, older_files, total, export_format, output
        )

        if show_cleanup_checkbox:
            proceed, cleanup_old_files = self._show_overwrite_cleanup_dialog(dialog_title, dialog_message)
        else:
            proceed = self._show_overwrite_confirm_dialog(dialog_title, dialog_message)
            cleanup_old_files = False

        if not proceed:
            return False

        if cleanup_old_files:
            for old_file in older_files:
                try:
                    old_file.unlink()
                except OSError as e:
                    # Log but don't fail - user still wants to export
                    logger.warning("Could not delete %s: %s", old_file, e)
        return True

    def _show_overwrite_confirm_dialog(self, title: str, message: str) -> bool:
        """Simple Yes/No overwrite confirmation. Returns True if the user chose to proceed."""
        choice = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButtons(QMessageBox.Yes | QMessageBox.No),
            QMessageBox.No,
        )
        return choice == QMessageBox.Yes

    def _show_overwrite_cleanup_dialog(self, title: str, message: str) -> tuple[bool, bool]:
        """Overwrite confirmation with a 'delete older page files' checkbox.

        Returns (proceed, cleanup_old_files).
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setMinimumWidth(450)

        layout = QVBoxLayout(dialog)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        cleanup_checkbox = QCheckBox("Delete older page files")
        cleanup_checkbox.setChecked(False)
        layout.addWidget(cleanup_checkbox)

        button_layout = QVBoxLayout()
        replace_button = QPushButton("Replace")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(replace_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def update_replace_button_text(state=None) -> None:
            if cleanup_checkbox.isChecked():
                replace_button.setText("Replace and delete older page files")
            else:
                replace_button.setText("Replace")

        cleanup_checkbox.toggled.connect(update_replace_button_text)
        replace_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        update_replace_button_text()

        result = dialog.exec()
        return result == QDialog.Accepted, cleanup_checkbox.isChecked()

    def print_document(self) -> None:
        """Print the current document with all annotations."""
        
        try:
            if not self.canvas.has_document:
                if not self._in_test_mode:
                    QMessageBox.warning(self, "Missing document", "Open a document first.")
                return
            
            total = self.canvas.page_count
            if total == 0:
                if not self._in_test_mode:
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
                if not self._in_test_mode:
                    QMessageBox.critical(self, "Print failed", "Failed to initialize printer.")
                return
            
            try:
                for page_idx in range(total):
                    page_image = self.canvas.get_page_image_with_rotation(page_idx)
                    if page_image is None:
                        continue

                    objects = self.canvas.page_objects_with_rotation_at(page_idx)
                    composite_image = page_image.convert("RGBA")
                    _composite_objects(composite_image, objects)
                    
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
            
            if not self._in_test_mode:
                NotificationToast(self, "Document sent to printer successfully.")
        
        except Exception as exc:
            if not self._in_test_mode:
                QMessageBox.critical(self, "Print error", f"Unexpected error during printing:\n{exc}")
            logger.exception("Unexpected error during printing")

    # ---------------------------------------------------------------- helpers

    def _show_save_error_dialog(self, exc: Exception, directory: Path) -> None:
        """Show the appropriate 'Save failed' dialog for an export/save exception (no-op in test mode)."""
        if self._in_test_mode:
            return
        if isinstance(exc, PermissionError):
            QMessageBox.critical(
                self, "Save failed",
                f"Permission denied. Check write permissions for:\n{directory}\n\n"
                "Try saving to a different location."
            )
        elif isinstance(exc, OSError) and "No space left" in str(exc):
            QMessageBox.critical(self, "Save failed", "Insufficient disk space. Free up space and try again.")
        else:
            QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")

    def _save_settings_safe(self) -> None:
        try:
            self._settings_store.save(self._settings)
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("Failed to save settings: %s", exc)

    def _adjust_window_to_document(self, doc_w: int, doc_h: int) -> None:
        if doc_w <= 0 or doc_h <= 0:
            return
        a4_size = QPageSize(QPageSize.A4).sizePixels(300)
        a4_ratio = a4_size.width() / a4_size.height()
        if abs(doc_w / doc_h - a4_ratio) < 0.005:
            doc_w, doc_h = a4_size.width(), a4_size.height()
        toolbar_hint_w = self.findChildren(QToolBar)[0].sizeHint().width() if self.findChildren(QToolBar) else 0
        chrome_h = self._main_toolbar.height()

        screen = self.screen()
        if screen is None:
            return
        avail = screen.availableGeometry()

        # Calculate the maximum canvas size that fits on screen
        max_canvas_h = avail.height() - chrome_h - 20
        max_canvas_w = avail.width() - 20

        # Scale document to fit within max canvas size while maintaining aspect ratio
        scale_h = max_canvas_h / doc_h
        scale_w = max_canvas_w / doc_w
        scale = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 100%

        target_canvas_h = round(doc_h * scale)
        target_canvas_w = round(doc_w * scale)

        # Ensure minimum canvas size
        target_canvas_h = max(640, target_canvas_h)
        target_canvas_w = max(520, target_canvas_w)

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
        """Undo the last action."""
        if self.canvas.undo():
            self.canvas.update()
        self._update_menu_state()

    def redo(self) -> None:
        """Redo the last undone action."""
        if self.canvas.redo():
            self.canvas.update()
        self._update_menu_state()

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
        if self._in_test_mode:
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
