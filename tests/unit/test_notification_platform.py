"""Cross-platform notification behavior tests."""

from unittest.mock import patch

from PySide6.QtWidgets import QMainWindow

from signer.notification import NotificationToast


def test_directory_link_uses_desktop_services(qtbot, tmp_path):
    """Directory links are delegated to the platform desktop environment."""
    main_window = QMainWindow()
    qtbot.addWidget(main_window)
    notification = NotificationToast(
        main_window, "Exported to ", directory=tmp_path
    )

    with patch(
        "signer.notification.QDesktopServices.openUrl", return_value=True
    ) as open_url:
        notification._on_link_clicked(str(tmp_path))

    opened_url = open_url.call_args.args[0]
    assert opened_url.toLocalFile() == str(tmp_path)
