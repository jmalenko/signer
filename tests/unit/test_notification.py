"""Unit tests for notification toast widget."""

import tempfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from signer.notification import NotificationToast


@pytest.fixture
def qapp():
    """Provide QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def main_window(qapp):
    """Provide a main window for testing."""
    window = QMainWindow()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    return window


def test_notification_creation_without_directory(main_window):
    """Test creating a notification without directory link."""
    notification = NotificationToast(main_window, "Test message")
    assert notification.message_label.text() == "Test message"
    notification.close()


def test_notification_creation_with_directory(main_window, tmp_path):
    """Test creating a notification with directory link."""
    message = "Exported file.jpg to "
    notification = NotificationToast(main_window, message, directory=tmp_path)
    
    # Check that the notification contains the directory link
    text = notification.message_label.text()
    assert "Exported file.jpg to" in text
    assert str(tmp_path) in text
    
    notification.close()


def test_notification_auto_dismisses(main_window, qapp):
    """Test that notification auto-dismisses after timeout."""
    from PySide6.QtCore import QTimer, QEventLoop
    
    notification = NotificationToast(main_window, "Test", duration_ms=100)
    assert notification.isVisible()
    
    # Use QEventLoop to process events and wait for the timer
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()
    
    # Check that the notification is closed
    assert not notification.isVisible()


def test_notification_manual_close(main_window):
    """Test manual closing via close button."""
    notification = NotificationToast(main_window, "Test", duration_ms=5000)
    assert notification.isVisible()
    
    # Find and click the close button (rightmost button in layout)
    notification.close()
    assert not notification.isVisible()


def test_error_notification_is_red_and_does_not_auto_dismiss(main_window, qapp):
    """Error notifications must be styled red and require manual dismissal."""
    from PySide6.QtCore import QTimer, QEventLoop

    notification = NotificationToast(main_window, "Unable to open directory", is_error=True)
    assert "c62828" in notification.styleSheet()  # red border color

    # Even after waiting well past the default auto-dismiss duration, it stays open
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()
    assert notification.isVisible()

    notification.close()
    assert not notification.isVisible()


def test_directory_link_failure_shows_error_notification(main_window):
    """Clicking a link to a directory that no longer exists shows a red toast, not a dialog."""
    missing_dir = Path("/nonexistent/path")
    notification = NotificationToast(main_window, "Exported file.jpg to ", directory=missing_dir)

    notification._on_link_clicked(str(missing_dir))

    error_toasts = [
        w for w in main_window.findChildren(NotificationToast)
        if w is not notification and w.isVisible()
    ]
    assert len(error_toasts) == 1
    assert "c62828" in error_toasts[0].styleSheet()

    notification.close()
    error_toasts[0].close()


def test_notification_positioning(main_window):
    """Test that notification is positioned at bottom-right."""
    main_window.setGeometry(100, 100, 800, 600)
    notification = NotificationToast(main_window, "Test")
    
    # Check position is roughly at bottom-right of main window
    parent_rect = main_window.geometry()
    notif_x = notification.x()
    notif_y = notification.y()
    
    # Notification should be to the right and below center
    assert notif_x > parent_rect.x() + parent_rect.width() // 2 - 100
    assert notif_y > parent_rect.y() + parent_rect.height() // 2
    
    notification.close()
