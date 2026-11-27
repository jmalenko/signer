"""With several annotations selected, a toolbar control is shown when at least one of them
supports it, and a change applies to the ones that do (spec §2.3)."""

import pytest
from PIL import Image

from signer.objects import AnnotationType, SignatureObject, VectorAnnotation


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    return main_window


def select(window, *objects):
    canvas = window.canvas
    for obj in objects:
        canvas.add_object(obj)
    canvas.select_annotation(objects[0])
    for obj in objects[1:]:
        canvas.select_annotation(obj, multi=True)
    canvas._selected = objects[0]  # the primary selection is the first one
    window._update_annotation_action_state()


def signature(x=100):
    return SignatureObject(Image.new("RGBA", (60, 30), "black"), "sig.png", x, 100)


def test_controls_of_the_other_selected_types_stay_visible(window):
    line = VectorAnnotation(AnnotationType.LINE, 500, 100)
    text = VectorAnnotation(AnnotationType.TEXT, 100, 500, text="hi")
    select(window, signature(), line, text)

    shown = window._context_conceptually_visible  # independent of the width left in the row
    assert window._color_btn_action in shown or window._color_btn_action.isVisibleTo(window)
    assert window._width_group in shown
    assert window._font_size_group in shown
    assert window._angle_group in shown


def test_only_controls_that_nothing_selected_supports_are_hidden(window):
    select(window, signature(), signature(400))

    assert not window._color_btn_action.isVisible()
    assert not window._width_group.isVisibleTo(window)
    assert not window._font_size_group.isVisibleTo(window)


def test_width_change_applies_to_the_selected_annotations_that_have_a_width(window):
    line = VectorAnnotation(AnnotationType.LINE, 500, 100)
    rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 500)
    text = VectorAnnotation(AnnotationType.TEXT, 700, 500, text="hi")
    select(window, text, line, rect)

    window._on_width_changed(5.0)

    assert (line._line_width_pt, rect._line_width_pt) == (5.0, 5.0)


def test_font_size_change_applies_when_the_text_is_not_the_primary_selection(window):
    text = VectorAnnotation(AnnotationType.TEXT, 100, 500, text="hi")
    select(window, signature(), text)

    window._on_font_size_changed(24)

    assert text._font_size_pt == 24
