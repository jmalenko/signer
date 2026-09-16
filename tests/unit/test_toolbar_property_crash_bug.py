"""Regression tests for toolbar width/font-family handlers.

Bug: _on_width_changed() and _on_font_family_changed() constructed
ChangeLineWidthAction/ChangeFontFamilyAction with keyword arguments that did not
match the action classes' actual constructor signatures (from_width/to_width vs.
line_width_pt/from_line_width_pt, from_family/to_family vs. font_family/from_font_family),
causing a TypeError crash whenever the toolbar control was changed while an
eligible annotation was selected.
"""

from signer.objects import AnnotationType, VectorAnnotation


def test_width_change_does_not_crash_and_is_undoable(main_window):
    """Expected behavior: changing line width via toolbar succeeds and is undoable."""
    annotation = VectorAnnotation(AnnotationType.LINE, 0, 0)
    main_window.canvas.add_object(annotation)

    main_window._width_spinner.setValue(3.0)

    assert annotation._line_width_pt == 3.0
    assert main_window.canvas.can_undo()
    main_window.canvas.undo()
    assert annotation._line_width_pt != 3.0


def test_font_family_change_does_not_crash_and_is_undoable(main_window):
    """Expected behavior: changing font family via toolbar succeeds and is undoable."""
    annotation = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Signer")
    main_window.canvas.add_object(annotation)
    original_family = annotation._font_family

    main_window._font_family_combo.setCurrentText("Courier New")

    assert annotation._font_family == "Courier New"
    assert main_window.canvas.can_undo()
    main_window.canvas.undo()
    assert annotation._font_family == original_family
