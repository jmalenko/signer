"""The Save As dialog follows the file-type selection of the user at once (spec §5.3): the
filename gets the extension and placeholder rules of the new format, and the Options button
is enabled only for the lossy formats."""

import pytest
from PySide6.QtWidgets import QComboBox, QFileDialog, QLineEdit

from signer.compositor import ExportFormat, build_suggested_filename_for_dialog
from signer.main_window import _SaveDialogWithFilterDetection


def make_dialog(qapp, tmp_path, total_pages, start_format=ExportFormat.JPG):
    document = tmp_path / "doc.pdf"
    suggested = build_suggested_filename_for_dialog(document, total_pages, start_format)
    dialog = _SaveDialogWithFilterDetection(None, "Save", str(tmp_path / suggested), ExportFormat.all_formats_filter())
    dialog.setOption(QFileDialog.DontUseNativeDialog, True)
    dialog.setOption(QFileDialog.DontConfirmOverwrite, True)
    dialog.last_format = start_format
    dialog.total_pages = total_pages
    dialog.document_path = str(document)
    dialog.last_suggested_filename = suggested
    dialog.selectNameFilter(start_format.file_filter())
    dialog._connect_line_edit()
    dialog._connect_filter_combo()
    dialog._add_options_button()
    dialog._update_options_button_state()
    dialog.show()
    qapp.processEvents()
    return dialog


def choose_filter(qapp, dialog, export_format):
    """Select a file type like the user does: pick it in the combo box."""
    combo = dialog.findChild(QComboBox, "fileTypeCombo")
    index = next(i for i in range(combo.count()) if combo.itemText(i) == export_format.file_filter())
    combo.setCurrentIndex(index)
    combo.activated.emit(index)
    qapp.processEvents()


def filename(dialog):
    return dialog.findChildren(QLineEdit)[0].text()


def type_filename(dialog, text):
    edit = dialog.findChildren(QLineEdit)[0]
    edit.setText(text)
    edit.textEdited.emit(text)


def test_switching_from_per_page_to_single_file_removes_the_placeholder(qapp, tmp_path):
    dialog = make_dialog(qapp, tmp_path, total_pages=3)
    assert filename(dialog) == "doc-signed-p#.jpg"

    choose_filter(qapp, dialog, ExportFormat.PDF)

    assert filename(dialog) == "doc-signed.pdf"


def test_switching_to_a_per_page_format_adds_the_placeholder(qapp, tmp_path):
    dialog = make_dialog(qapp, tmp_path, total_pages=3, start_format=ExportFormat.PDF)

    choose_filter(qapp, dialog, ExportFormat.PNG)

    assert filename(dialog) == "doc-signed-p#.png"


def test_a_single_page_document_never_gets_a_placeholder(qapp, tmp_path):
    dialog = make_dialog(qapp, tmp_path, total_pages=1, start_format=ExportFormat.PDF)

    choose_filter(qapp, dialog, ExportFormat.PNG)

    assert filename(dialog) == "doc-signed.png"


def test_the_stem_the_user_typed_is_kept_when_the_format_changes(qapp, tmp_path):
    dialog = make_dialog(qapp, tmp_path, total_pages=3)
    type_filename(dialog, "my-scan-p#.jpg")

    choose_filter(qapp, dialog, ExportFormat.PDF)
    assert filename(dialog) == "my-scan.pdf"

    choose_filter(qapp, dialog, ExportFormat.BMP)
    assert filename(dialog) == "my-scan-p#.bmp"


@pytest.mark.parametrize("export_format, enabled", [
    (ExportFormat.JPG, True), (ExportFormat.PDF, True),
    (ExportFormat.PNG, False), (ExportFormat.TIFF, False), (ExportFormat.BMP, False),
])
def test_the_options_button_follows_the_selected_format(qapp, tmp_path, export_format, enabled):
    dialog = make_dialog(qapp, tmp_path, total_pages=3)

    choose_filter(qapp, dialog, export_format)

    assert dialog._options_button.isEnabled() is enabled
