"""Regression tests for silent-failure review finding #2: AddAnnotationAction's
"most reliable" undo strategy (direct object reference) must log a warning when its
LIFO-pop fallback triggers, the same way the other undo fallback strategies already do.
"""

from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


def _setup_page(canvas):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white")])


def test_add_annotation_undo_logs_warning_when_tracked_object_missing_from_page(canvas, caplog):
    """Expected behavior: if the tracked object reference is no longer on its page
    when undo() runs (e.g. removed by another code path), the LIFO-pop fallback must
    be logged - not silently pop an unrelated object with no trace.
    """
    _setup_page(canvas)
    a = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    canvas.add_object(a)
    action = canvas.history.undo_stack[-1]

    other = VectorAnnotation(AnnotationType.CROSSMARK, 200, 200, page=0)
    canvas.current_page_objects().append(other)

    # Simulate `a` having already been removed from the page by another path,
    # while this action still holds a direct reference to it.
    canvas.current_page_objects().remove(a)

    with caplog.at_level("WARNING"):
        action.undo(canvas)

    assert any("AddAnnotationAction.undo()" in r.message for r in caplog.records), (
        "removing an unrelated object via the LIFO fallback must be logged"
    )

