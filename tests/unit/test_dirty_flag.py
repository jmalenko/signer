"""Only changes to the annotations (and page rotation) count as unsaved changes (spec §4.2).
Looking at a document - zooming, fitting, navigating, selecting - never does."""

import pytest

from signer.objects import AnnotationType, VectorAnnotation


@pytest.fixture
def window(main_window, sample_multipage_pdf):
    assert main_window.open_document(str(sample_multipage_pdf))
    assert main_window._has_unsaved_changes is False
    return main_window


def test_zoom_and_fit_do_not_mark_the_document_changed(window):
    window.canvas.zoom_in()
    window.canvas.zoom_out()
    window.canvas.fit_to_window()
    assert window._has_unsaved_changes is False


def test_page_navigation_does_not_mark_the_document_changed(window):
    window.canvas.goto_page(1)
    window.canvas.goto_page(0)
    assert window._has_unsaved_changes is False


def test_selecting_does_not_mark_the_document_changed(window):
    window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 100, 100))
    window._has_unsaved_changes = False
    window.canvas.select_all_on_page()
    window.canvas.clear_selection()
    window.canvas.select_annotation(window.canvas.current_page_objects()[0])
    assert window._has_unsaved_changes is False


def test_adding_an_annotation_marks_the_document_changed(window):
    window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 100, 100))
    assert window._has_unsaved_changes is True


def test_undo_marks_the_document_changed(window):
    window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 100, 100))
    window._has_unsaved_changes = False
    assert window.canvas.undo()
    assert window._has_unsaved_changes is True


def test_rotating_a_page_marks_the_document_changed(window):
    window.canvas.rotate_current_page_left()
    assert window._has_unsaved_changes is True
