"""Regression tests for AddAnnotationAction's undo fallbacks and redo defaults.

See CODE_REVIEW_PLAN.md sections B2 and B3.
"""

from PIL import Image

from signer.constants import DEFAULT_COLOR, DEFAULT_TEXT_FONT_PT
from signer.history import AddAnnotationAction
from signer.objects import AnnotationType, VectorAnnotation


def _setup_page(canvas, count=1):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white") for _ in range(count)])


def test_undo_add_does_not_remove_an_unrelated_annotation(canvas):
    """If the tracked object is already off the page, undo must not pop a bystander."""
    _setup_page(canvas)
    added = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    canvas.add_object(added)
    action = canvas.history.undo_stack[-1]

    bystander = VectorAnnotation(AnnotationType.CROSSMARK, 200, 200, page=0)
    canvas.page_objects_at(0).append(bystander)
    canvas.page_objects_at(0).remove(added)

    action.undo(canvas)

    assert canvas.page_objects_at(0) == [bystander], "the unrelated annotation must survive"


def test_undo_add_targets_the_page_the_annotation_was_added_to(canvas):
    """Adding on page 1 then undoing from page 2 must clear page 1."""
    _setup_page(canvas, count=2)
    added = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    canvas.add_object(added)

    canvas.goto_page(1)
    canvas.undo()

    assert canvas.page_objects_at(0) == []


def test_redo_add_from_minimal_payload_uses_application_defaults(canvas):
    """A payload without colour/font must be recreated with the app's defaults,
    not with values hardcoded in the action class."""
    _setup_page(canvas)

    action = AddAnnotationAction({"ann_type": "text", "x": 10, "y": 20, "page": 0, "text": "hi"})
    action.execute(canvas)

    obj = canvas.page_objects_at(0)[-1]
    assert obj.color.name() == DEFAULT_COLOR
    assert obj._font_size_pt == DEFAULT_TEXT_FONT_PT


def test_redo_add_from_minimal_payload_uses_the_types_default_size(canvas):
    """Large default types (line/arrow/rectangle/ellipse) keep their larger base size."""
    _setup_page(canvas)

    AddAnnotationAction({"ann_type": "rectangle", "x": 0, "y": 0, "page": 0}).execute(canvas)
    large = canvas.page_objects_at(0)[-1]
    AddAnnotationAction({"ann_type": "checkmark", "x": 0, "y": 0, "page": 0}).execute(canvas)
    small = canvas.page_objects_at(0)[-1]

    reference_large = VectorAnnotation(AnnotationType.RECTANGLE, 0, 0, 0)
    reference_small = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 0)
    assert large.scaled_width == reference_large.scaled_width
    assert small.scaled_width == reference_small.scaled_width


def test_redo_add_of_an_unknown_type_is_logged(canvas, caplog):
    """An unrecognised payload must leave a trace instead of silently doing nothing."""
    _setup_page(canvas)

    with caplog.at_level("WARNING"):
        AddAnnotationAction({"type": "NoSuchObject", "x": 0, "y": 0, "page": 0}).execute(canvas)

    assert canvas.page_objects_at(0) == []
    assert any("AddAnnotationAction.execute()" in r.message for r in caplog.records)
