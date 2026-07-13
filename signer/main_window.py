from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSlider,
    QToolBar,
)

from .canvas import DocumentCanvas
from .compositor import build_default_output_path, composite_signature_to_jpg
from .pdf_utils import render_first_page_to_image
from .settings import AppSettings, SettingsStore

SUPPORTED_SIGNATURE_EXT = {".png", ".jpg", ".jpeg"}


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("Signer")
        self.resize(1200, 850)

        self._settings_store = settings_store
        self._settings = settings

        self.document_path: str | None = None
        self.signature_path: str | None = None

        self.canvas = DocumentCanvas(self)
        self.setCentralWidget(self.canvas)

        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()

        self.canvas.signatureChanged.connect(self._on_signature_changed)

    def run_startup_load(self, document: str | None, signature: str | None) -> None:
        def _load() -> None:
            if document:
                self.open_document(document)

            if signature:
                self.open_signature(signature)
            elif self._settings.last_signature_path:
                self.open_signature(self._settings.last_signature_path)

        QTimer.singleShot(0, _load)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        open_doc_action = QAction("Open Document", self)
        open_doc_action.triggered.connect(lambda: self.open_document())
        file_menu.addAction(open_doc_action)

        open_sig_action = QAction("Open Signature", self)
        open_sig_action.triggered.connect(lambda: self.open_signature())
        file_menu.addAction(open_sig_action)

        save_action = QAction("Save Document with Signature", self)
        save_action.triggered.connect(self.save_signed_document)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Signature", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel("Signature scale:"))

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(20, 300)
        self.scale_slider.setValue(100)
        self.scale_slider.setSingleStep(5)
        self.scale_slider.setPageStep(10)
        self.scale_slider.setEnabled(False)
        self.scale_slider.valueChanged.connect(self._on_scale_slider_changed)

        toolbar.addWidget(self.scale_slider)

        self.scale_label = QLabel("100%")
        toolbar.addWidget(self.scale_label)

    def _build_statusbar(self) -> None:
        self.doc_status = QLabel("Document: (none)")
        self.sig_status = QLabel("Signature: (none)")
        self.pos_status = QLabel("Signature pos: -")

        self.statusBar().addWidget(self.doc_status, 1)
        self.statusBar().addWidget(self.sig_status, 1)
        self.statusBar().addPermanentWidget(self.pos_status)

    def _on_scale_slider_changed(self, value: int) -> None:
        self.canvas.set_signature_scale(value / 100.0)
        self.scale_label.setText(f"{value}%")

    def _on_signature_changed(self) -> None:
        scale_pct = int(round(self.canvas.signature_scale() * 100))
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(scale_pct)
        self.scale_slider.blockSignals(False)
        self.scale_label.setText(f"{scale_pct}%")

        info = self.canvas.signature_info()
        if info is None:
            self.pos_status.setText("Signature pos: -")
            return

        x, y, w, h, _ = info
        self.pos_status.setText(f"Signature pos: x={int(round(x))}, y={int(round(y))}, {int(round(w))}x{int(round(h))}")

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
            image = render_first_page_to_image(p, dpi=300)
        except Exception as exc:
            QMessageBox.critical(self, "Open document failed", f"Could not open PDF:\n{exc}")
            return False

        self.canvas.set_document_image(image)
        self.document_path = str(p)
        self._settings.last_open_document_path = str(p)
        self._save_settings_safe()

        self.doc_status.setText(f"Document: {p.name}")
        self._update_title()
        return True

    def open_signature(self, path: str | None = None) -> bool:
        chosen = path
        if not chosen:
            start_dir = ""
            if self.signature_path:
                start_dir = str(Path(self.signature_path).parent)
            elif self._settings.last_signature_path:
                start_dir = str(Path(self._settings.last_signature_path).parent)
            chosen, _ = QFileDialog.getOpenFileName(
                self,
                "Open Signature",
                start_dir,
                "Image files (*.png *.jpg *.jpeg);;All files (*.*)",
            )

        if not chosen:
            return False

        p = Path(chosen)
        suffix = p.suffix.lower()
        if suffix == ".xcf":
            QMessageBox.warning(
                self,
                "Unsupported signature format",
                "GIMP .xcf is not supported directly. Export it to .png or .jpg first.",
            )
            return False

        if suffix not in SUPPORTED_SIGNATURE_EXT:
            QMessageBox.warning(self, "Invalid signature", "Signature must be .png, .jpg, or .jpeg.")
            return False

        try:
            with Image.open(p) as img:
                loaded = img.convert("RGBA")
        except (UnidentifiedImageError, OSError) as exc:
            QMessageBox.critical(self, "Open signature failed", f"Could not open signature image:\n{exc}")
            return False

        self.canvas.set_signature_image(loaded, str(p))
        self.signature_path = str(p)
        self.scale_slider.setEnabled(True)
        self.scale_slider.setValue(100)

        self._settings.last_signature_path = str(p)
        self._save_settings_safe()

        self.sig_status.setText(f"Signature: {p.name}")
        self._update_title()
        return True

    def save_signed_document(self) -> bool:
        if not self.canvas.has_document:
            QMessageBox.warning(self, "Missing document", "Open a document first.")
            return False
        if not self.canvas.has_signature:
            QMessageBox.warning(self, "Missing signature", "Open a signature first.")
            return False
        if not self.document_path:
            QMessageBox.warning(self, "Missing document path", "Document path is not available.")
            return False

        default_path = build_default_output_path(self.document_path, self._settings.last_save_directory)
        chosen, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document with Signature",
            str(default_path),
            "JPEG files (*.jpg *.jpeg)",
        )

        if not chosen:
            return False

        output = Path(chosen)
        if output.suffix.lower() not in {".jpg", ".jpeg"}:
            output = output.with_suffix(".jpg")

        sig_state = self.canvas.signature_state_for_save()
        doc_image = self.canvas.document_image
        if sig_state is None or doc_image is None:
            QMessageBox.warning(self, "Not ready", "Missing document or signature state.")
            return False

        sig_image, x, y, scale = sig_state

        try:
            composite_signature_to_jpg(
                document_image=doc_image,
                signature_image=sig_image,
                signature_x=x,
                signature_y=y,
                signature_scale=scale,
                output_path=output,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save output:\n{exc}")
            return False

        self._settings.last_save_directory = str(output.parent)
        self._save_settings_safe()

        QMessageBox.information(self, "Saved", f"Saved signed document:\n{output}")
        return True

    def _save_settings_safe(self) -> None:
        try:
            self._settings_store.save(self._settings)
        except Exception:
            pass

    def _update_title(self) -> None:
        doc_name = Path(self.document_path).name if self.document_path else "(no document)"
        self.setWindowTitle(f"Signer - {doc_name}")
