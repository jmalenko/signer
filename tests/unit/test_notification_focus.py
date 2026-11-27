"""A toast never takes the keyboard focus from the main window (spec §14), and a failed
directory link is logged."""

import logging

from signer.notification import NotificationToast


def test_a_toast_does_not_accept_focus(main_window):
    from PySide6.QtCore import Qt

    toast = NotificationToast(main_window, "Exported file to ")

    assert toast.testAttribute(Qt.WA_ShowWithoutActivating)
    assert toast.windowFlags() & Qt.WindowDoesNotAcceptFocus
    toast.close()


def test_a_failed_directory_link_is_logged(main_window, tmp_path, caplog):
    toast = NotificationToast(main_window, "Exported to ", tmp_path)

    with caplog.at_level(logging.WARNING, logger="signer.notification"):
        toast._on_link_clicked(str(tmp_path / "gone"))

    assert "gone" in caplog.text
    toast.close()
