"""Notification toast widget for displaying auto-dismissing messages."""

import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class NotificationToast(QWidget):
    """Auto-dismissing notification widget displayed at bottom-right of parent window."""
    
    DEFAULT_DURATION_MS = 5000  # 5 seconds
    MAX_WIDTH = 700  # Maximum width for the notification
    
    def __init__(
        self,
        parent: QWidget,
        message: str,
        directory: Path | None = None,
        exported_files: list[Path] | None = None,
        duration_ms: int = DEFAULT_DURATION_MS,
    ) -> None:
        """
        Create a notification toast.
        
        Args:
            parent: Parent widget (typically the main window)
            message: Message text to display (may contain placeholder for directory)
            directory: Optional directory path that becomes a clickable link
            exported_files: List of exported file paths to select in Explorer
            duration_ms: Auto-dismiss duration in milliseconds
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Remove translucent background for full visibility
        self._directory = directory
        self._exported_files = exported_files or []
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_timeout)
        
        # Setup UI
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Message label with clickable link support
        self.message_label = QLabel(self)
        self.message_label.setWordWrap(True)
        self.message_label.setCursor(Qt.IBeamCursor)
        self.message_label.setMinimumWidth(200)
        self.message_label.setMaximumWidth(self.MAX_WIDTH - 50)
        
        if directory:
            # Create clickable link - format: "message [directory]"
            dir_link = f'<a href="{directory}" style="color: #0078d4; text-decoration: underline; font-weight: bold;">{directory}</a>'
            html_text = f"{message}{dir_link}"
            self.message_label.setText(html_text)
            self.message_label.setOpenExternalLinks(False)  # Handle manually
            self.message_label.linkActivated.connect(self._on_link_clicked)
        else:
            self.message_label.setText(message)
        
        layout.addWidget(self.message_label, 1)
        
        # Close button
        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(24, 24)
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        # Styling - more visible with solid background
        self.setStyleSheet(
            """
            NotificationToast {
                background-color: #c8e6c9;
                border: 2px solid #2e7d32;
                border-radius: 6px;
            }
            QLabel {
                color: #1b5e20;
                font-size: 11px;
                background-color: transparent;
            }
            QPushButton {
                color: #1b5e20;
                border: none;
                padding: 0px;
                margin: 0px;
                background-color: transparent;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a5d6a7;
                border-radius: 3px;
            }
            """
        )
        
        # Dynamic sizing based on content
        self.adjustSize()
        self.setMinimumWidth(350)
        self.setMinimumHeight(60)
        # Ensure width doesn't exceed maximum
        if self.width() > self.MAX_WIDTH:
            self.resize(self.MAX_WIDTH, self.height())
        
        self._reposition()
        self.show()
        
        # Start auto-dismiss timer
        self._timer.start(duration_ms)
    
    def _on_link_clicked(self, url: str) -> None:
        """Handle directory link click - select exported files in Explorer."""
        try:
            path = Path(url)
            if not path.exists():
                # If path no longer exists, show brief error
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self.parent(), "Unable to open directory",
                                  f"The directory no longer exists:\n{path}")
                return
            
            # If we have exported files, select the first one (or all if possible)
            if self._exported_files:
                # Select the first exported file
                first_file = self._exported_files[0]
                if first_file.exists():
                    # Use Windows Explorer /select command to highlight the file
                    subprocess.Popen(f'explorer.exe /select,"{first_file}"')
                else:
                    # File doesn't exist, just open the directory
                    subprocess.Popen(f'explorer.exe "{path}"')
            else:
                # No exported files provided, just open the directory
                subprocess.Popen(f'explorer.exe "{path}"')
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self.parent(), "Unable to open directory",
                              f"Could not open directory:\n{url}\n\nError: {exc}")
    
    def _on_timeout(self) -> None:
        """Auto-dismiss after timeout."""
        self._timer.stop()
        self.close()
    
    def _reposition(self) -> None:
        """Position toast at bottom-right of parent window."""
        if self.parent() and hasattr(self.parent(), 'geometry'):
            parent_rect = self.parent().geometry()
            # Position at bottom-right with some margin
            x = parent_rect.x() + parent_rect.width() - self.width() - 10
            y = parent_rect.y() + parent_rect.height() - self.height() - 10
            self.move(x, y)
        else:
            # Fallback if parent has no geometry
            self.move(100, 100)
