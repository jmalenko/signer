"""Opening documents and projects: passwords, failures that leave the open document untouched,
Change Document, and the project path lifecycle (spec §3, §4, §16)."""

import json
import shutil
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QDialog

from signer.objects import AnnotationType, VectorAnnotation


class FakePasswordDialog:
    """Stands in for the password dialog and types the given passwords one after the other."""

    prompts: list[str] = []

    def __init__(self, passwords):
        self._passwords = iter(passwords)
        self._current = ""

    def __call__(self, parent, filename):
        FakePasswordDialog.prompts.append(filename)
        return self

    def exec(self):
        try:
            self._current = next(self._passwords)
        except StopIteration:
            return QDialog.Rejected
        return QDialog.Accepted

    def password(self):
        return self._current


@pytest.fixture
def examples(sample_pdf):
    return sample_pdf.parent


@pytest.fixture
def silent_errors():
    with patch("signer.main_window.QMessageBox.critical") as critical:
        yield critical


def test_the_third_password_prompt_is_tried(main_window, examples, silent_errors):
    FakePasswordDialog.prompts = []
    typed = FakePasswordDialog(["wrong", "wrong", "key123"])
    with patch("signer.main_window._PasswordDialog", typed):
        assert main_window.open_document(str(examples / "document-encrypted.pdf"))
    assert len(FakePasswordDialog.prompts) == 3


def test_a_wrong_password_three_times_does_not_open_the_document(main_window, examples, silent_errors):
    typed = FakePasswordDialog(["a", "b", "c", "d"])
    with patch("signer.main_window._PasswordDialog", typed):
        assert not main_window.open_document(str(examples / "document-encrypted.pdf"))
    assert main_window.document_path is None


def test_a_project_of_an_encrypted_pdf_asks_for_the_password(main_window, examples, tmp_path, silent_errors):
    project = tmp_path / "enc.signer"
    project.write_text(json.dumps({
        "version": 1, "document_path": str(examples / "document-encrypted.pdf"), "annotations": [],
    }))
    typed = FakePasswordDialog(["key123"])
    with patch("signer.main_window._PasswordDialog", typed):
        assert main_window.open_project(project)
    assert main_window.document_path.endswith("document-encrypted.pdf")


def project_with(tmp_path, document, annotations):
    path = tmp_path / "bad.signer"
    path.write_text(json.dumps({"version": 1, "document_path": str(document), "annotations": annotations}))
    return path


@pytest.mark.parametrize("annotations", [[{"type": "add_annotation"}], {"0": []}])
def test_a_broken_project_leaves_the_open_document_untouched(
    main_window, examples, tmp_path, silent_errors, annotations
):
    window = main_window
    assert window.open_document(str(examples / "document1.pdf"))
    mine = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100)
    window.canvas.add_object(mine)
    window.project_path = str(tmp_path / "mine.signer")
    dirty_before = window._has_unsaved_changes

    opened = window.open_project(project_with(tmp_path, examples / "document.pdf", annotations), check_unsaved_changes=False)

    assert opened is False
    silent_errors.assert_called()
    assert window.document_path.endswith("document1.pdf")
    assert window.canvas.current_page_objects() == [mine]
    assert window.project_path == str(tmp_path / "mine.signer")
    assert window._has_unsaved_changes == dirty_before


def test_change_document_updates_the_title_and_the_recent_menu(main_window, examples, tmp_path):
    window = main_window
    first = tmp_path / "first.pdf"
    shutil.copy(examples / "document1.pdf", first)
    assert window.open_document(str(first))

    with patch("signer.main_window.QFileDialog.getOpenFileName", return_value=(str(examples / "document.pdf"), "")):
        assert window.change_document()

    assert "document.pdf" in window.windowTitle()
    assert window._settings.recent_document_paths[0].endswith("document.pdf")


def test_project_and_document_actions_need_an_open_document(main_window, sample_pdf):
    window = main_window
    window._update_menu_state()
    actions = (
        window._menu_save_project_action,
        window._menu_save_project_as_action,
        window._menu_change_document_action,
    )
    assert not any(action.isEnabled() for action in actions)

    assert window.open_document(str(sample_pdf))
    window._update_menu_state()
    assert all(action.isEnabled() for action in actions)


def test_opening_another_document_forgets_the_export_of_the_previous_one(main_window, examples):
    window = main_window
    assert window.open_document(str(examples / "document1.pdf"))
    window._last_export_path = "/somewhere/else/document1-signed.jpg"
    window.project_path = "/somewhere/else/document1-signed.signer"

    assert window.open_document(str(examples / "document.pdf"))

    assert window._last_export_path is None
    assert window.project_path is None


def test_opening_a_document_gives_the_canvas_the_keyboard_focus(main_window, sample_pdf):
    window = main_window
    window.show()
    window._toolbar_page_nav_label.setFocus()

    assert window.open_document(str(sample_pdf))

    assert window.canvas.hasFocus() or window.focusWidget() is window.canvas


def test_clicking_the_toolbar_open_button_opens_the_file_picker(main_window):
    button = main_window._toolbar_open_button
    assert button.popupMode() == button.ToolButtonPopupMode.MenuButtonPopup
    assert button.menu() is not None  # the arrow offers the recent documents

    with patch.object(main_window, "open_document") as open_document:
        button.click()

    open_document.assert_called_once_with()
