"""Regression test: editing an existing text annotation's content (via double-click
-> Edit Text dialog) must be undoable, per REQUIREMENTS.md "Supported Actions for
Undo/Redo": "Set text (change text annotation content)".

Bug: MainWindow._on_edit_requested() set `obj.text` directly and never recorded any
history action, so editing existing text content was silently not undoable.
"""

from unittest.mock import patch

from PySide6.QtWidgets import QDialog

from signer.objects import AnnotationType, VectorAnnotation


def _edit_text_via_dialog(main_window, obj, new_text):
    with patch("signer.main_window._TextInputDialog") as mock_dialog_cls:
        instance = mock_dialog_cls.return_value
        instance.exec.return_value = QDialog.Accepted
        instance.text.return_value = new_text
        main_window._on_edit_requested(obj)


def test_text_edit_via_dialog_is_undoable(main_window):
    annotation = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Original")
    main_window.canvas.add_object(annotation)

    _edit_text_via_dialog(main_window, annotation, "Edited")

    assert annotation.text == "Edited"
    assert main_window.canvas.can_undo()

    main_window.canvas.undo()

    assert annotation.text == "Original"


def test_text_edit_with_unchanged_text_does_not_record_history(main_window):
    """Confirming the dialog without changing the text should not add a no-op undo step."""
    annotation = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Same")
    main_window.canvas.add_object(annotation)
    main_window.canvas.clear_history()

    _edit_text_via_dialog(main_window, annotation, "Same")

    assert not main_window.canvas.can_undo()
