"""Overwrite confirmation wording and buttons (spec §5.4)."""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox

from signer.compositor import ExportFormat, build_overwrite_dialog_info


def test_an_existing_single_page_jpg_is_asked_about_by_its_name(tmp_path):
    existing = tmp_path / "doc-signed.jpg"
    title, message, cleanup = build_overwrite_dialog_info([existing], [], 1, ExportFormat.JPG, existing)

    assert "The file 'doc-signed.jpg' already exists" in message
    assert "replace it" in message
    assert cleanup is False


def test_all_pages_message_has_no_doubled_dot(tmp_path):
    output = tmp_path / "doc-signed-p#.png"
    files = [tmp_path / f"doc-signed-p{n}.png" for n in (1, 2, 3)]

    _, message, _ = build_overwrite_dialog_info(files, [], 3, ExportFormat.PNG, output)

    assert "All 3 pages of 'doc-signed-p#.png'" in message
    assert ".." not in message


def test_the_confirmation_offers_replace_and_cancel_with_cancel_as_default(main_window):
    seen = {}

    def exec_box(box):
        seen["buttons"] = {button.text(): box.buttonRole(button) for button in box.buttons()}
        seen["default"] = box.defaultButton().text()
        return 0

    with patch.object(QMessageBox, "exec", exec_box):
        main_window._show_overwrite_confirm_dialog("File Already Exists", "Replace?")

    assert set(seen["buttons"]) == {"Replace", "Cancel"}
    assert seen["default"] == "Cancel"


@pytest.mark.parametrize("clicked, expected", [("Replace", True), ("Cancel", False)])
def test_only_replace_lets_the_export_proceed(main_window, clicked, expected):
    def exec_box(box):
        box._clicked = next(button for button in box.buttons() if button.text() == clicked)
        return 0

    with patch.object(QMessageBox, "exec", exec_box), \
         patch.object(QMessageBox, "clickedButton", lambda box: box._clicked):
        assert main_window._show_overwrite_confirm_dialog("t", "m") is expected


def test_a_failed_cleanup_of_older_page_files_shows_a_warning(main_window, tmp_path):
    for page in (1, 2, 3, 4, 5):
        (tmp_path / f"doc-p{page}.jpg").write_bytes(b"x")
    main_window._in_test_mode = False
    try:
        with patch.object(main_window, "_show_overwrite_cleanup_dialog", return_value=(True, True)), \
             patch("pathlib.Path.unlink", side_effect=OSError("locked")), \
             patch("signer.main_window.QMessageBox.warning") as warning:
            proceed = main_window._confirm_overwrite_and_cleanup(
                tmp_path / "doc-p#.jpg", 3, ExportFormat.JPG, "doc-p#"
            )
    finally:
        main_window._in_test_mode = True

    assert proceed is True, "the export itself still goes ahead"
    warning.assert_called_once()
    assert "doc-p4.jpg" in warning.call_args.args[2]
