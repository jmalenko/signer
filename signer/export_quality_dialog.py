"""Export quality options dialog for lossy formats (JPG, PDF)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from .compositor import ExportFormat


class ExportQualityOptionsPanel(QDialog):
    """Non-modal dialog for adjusting export quality for lossy formats.
    
    Shows a quality slider (1-100) with numeric display and labels indicating
    the quality-to-filesize tradeoff ("small file" on left, "large file" on right).
    """

    def __init__(
        self,
        parent,
        export_format: ExportFormat,
        current_quality: int = 95,
    ) -> None:
        """Initialize the export quality options panel.
        
        Args:
            parent: Parent widget
            export_format: ExportFormat enum value (JPG or PDF)
            current_quality: Current quality value (1-100)
        """
        super().__init__(parent)
        self.export_format = export_format
        self.current_quality = current_quality
        self.user_accepted = False
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setWindowTitle("Export Quality Options")
        self.setModal(False)
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Format-specific subtitle
        format_name = self.export_format.value.upper()
        if self.export_format.value == "pdf":
            subtitle_text = "Choose image quality for embedded images in PDF:"
        else:
            subtitle_text = f"Choose quality settings for {format_name}:"
        subtitle = QLabel(subtitle_text)
        layout.addWidget(subtitle)
        
        # Quality control layout
        quality_layout = QVBoxLayout()
        
        # Slider and numeric display row
        slider_row = QHBoxLayout()
        
        # Left label
        left_label = QLabel("small file")
        left_label.setStyleSheet("color: gray; font-size: 11px;")
        slider_row.addWidget(left_label)
        
        # Slider
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setMinimum(1)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(self.current_quality)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(10)
        slider_row.addWidget(self.quality_slider)
        
        # Right label
        right_label = QLabel("large file")
        right_label.setStyleSheet("color: gray; font-size: 11px;")
        slider_row.addWidget(right_label)
        
        quality_layout.addLayout(slider_row)
        
        # Numeric value display and spinbox row
        value_row = QHBoxLayout()
        value_row.addWidget(QLabel("Quality:"))
        
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setMinimum(1)
        self.quality_spinbox.setMaximum(100)
        self.quality_spinbox.setValue(self.current_quality)
        self.quality_spinbox.setMaximumWidth(80)
        value_row.addWidget(self.quality_spinbox)
        
        value_row.addWidget(QLabel("(1-100)"))
        value_row.addStretch()
        
        quality_layout.addLayout(value_row)
        
        layout.addLayout(quality_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def _connect_signals(self) -> None:
        """Connect signal/slot connections."""
        # Keep slider and spinbox in sync
        self.quality_slider.valueChanged.connect(self._on_slider_changed)
        self.quality_spinbox.valueChanged.connect(self._on_spinbox_changed)
        
        # Button signals
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
    def _on_slider_changed(self, value: int) -> None:
        """Handle slider value changes."""
        self.quality_spinbox.blockSignals(True)
        self.quality_spinbox.setValue(value)
        self.quality_spinbox.blockSignals(False)
        
    def _on_spinbox_changed(self, value: int) -> None:
        """Handle spinbox value changes."""
        self.quality_slider.blockSignals(True)
        self.quality_slider.setValue(value)
        self.quality_slider.blockSignals(False)
        
    def _on_ok_clicked(self) -> None:
        """Handle OK button click."""
        self.user_accepted = True
        self.accept()
        
    def _on_cancel_clicked(self) -> None:
        """Handle Cancel button click."""
        self.user_accepted = False
        self.reject()
        
    def get_quality(self) -> int:
        """Get the selected quality value (1-100)."""
        return self.quality_slider.value()
