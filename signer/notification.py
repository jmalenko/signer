"""Notification toast widget for displaying success and error messages."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class NotificationToast(QWidget):
    """Notification widget displayed at bottom-right of parent window.

    Success notifications (default) are green and auto-dismiss after
    ``duration_ms``. Error notifications (``is_error=True``) are red and
    must be manually dismissed via the close button; no auto-dismiss timer
    is started for them.
    """
    
    DEFAULT_DURATION_MS = 5000  # 5 seconds
    MAX_WIDTH = 700  # Maximum width for the notification
    
    def __init__(
        self,
        parent: QWidget,
        message: str,
        directory: Path | None = None,
        exported_files: list[Path] | None = None,
        duration_ms: int = DEFAULT_DURATION_MS,
        is_error: bool = False,
    ) -> None:
        """
        Create a notification toast.
        
        Args:
            parent: Parent widget (typically the main window)
            message: Message text to display (may contain placeholder for directory)
            directory: Optional directory path that becomes a clickable link
            exported_files: Exported file paths associated with the
                notification
            duration_ms: Auto-dismiss duration in milliseconds (ignored if is_error)
            is_error: If True, style as a red error notification that only
                dismisses when the user clicks the close button
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
        
        # Styling - more visible with solid background; red for errors, green for success
        if is_error:
            self.setStyleSheet(
                """
                NotificationToast {
                    background-color: #ffcdd2;
                    border: 2px solid #c62828;
                    border-radius: 6px;
                }
                QLabel {
                    color: #b71c1c;
                    font-size: 11px;
                    background-color: transparent;
                }
                QPushButton {
                    color: #b71c1c;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ef9a9a;
                    border-radius: 3px;
                }
                """
            )
        else:
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
        
        # Error notifications require manual dismissal; only success auto-dismisses
        if not is_error:
            self._timer.start(duration_ms)
    
    def _on_link_clicked(self, url: str) -> None:
        """Open a directory link with the platform desktop environment."""
        try:
            path = Path(url)
            if not path.exists():
                NotificationToast(
                    self.parent(), "Unable to open directory", is_error=True
                )
                return

            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                raise OSError(f"Desktop environment could not open {path}")
        except Exception:
            NotificationToast(
                self.parent(), "Unable to open directory", is_error=True
            )
    
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
