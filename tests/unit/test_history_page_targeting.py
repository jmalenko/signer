"""Regression tests: history actions must operate on the page the annotation
belongs to, not on whatever page the user happens to be looking at.

See CODE_REVIEW_PLAN.md section A1.
"""

from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


def _setup_pages(canvas, count=3):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white") for _ in range(count)])


def test_undo_delete_restores_annotation_to_its_own_page(canvas):
    """Delete on page 1, navigate to page 2, undo -> the annotation is back on page 1."""
    _setup_pages(canvas)
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    canvas.add_object(obj)
    canvas.select_annotation(obj)
    canvas.remove_selected()
    assert canvas.page_objects_at(0) == []

    canvas.goto_page(1)
    assert canvas.undo() is True

    assert canvas.page_objects_at(0) == [obj], "annotation must return to its own page"
    assert canvas.page_objects_at(1) == [], "annotation must not land on the visible page"
    assert obj.page == 0


def test_undo_delete_works_when_target_page_has_no_object_list_yet(canvas):
    """The object's page must be restored even if `_page_objects` has no entry for
    the page the user is currently on (the `.get(page, [])` default is a throwaway list)."""
    _setup_pages(canvas)
    obj = VectorAnnotation(AnnotationType.CROSSMARK, 50, 50, page=0)
    canvas.add_object(obj)
    canvas.select_annotation(obj)
    canvas.remove_selected()

    canvas.goto_page(2)
    assert 2 not in canvas._page_objects, "precondition: page 3 was never populated"

    canvas.undo()

    assert canvas.page_objects_at(0) == [obj]
    assert canvas._object_map.get(0) is obj


def test_redo_delete_removes_from_the_annotations_own_page(canvas):
    """Redoing a delete must remove the annotation from its own page, not the current one."""
    _setup_pages(canvas)
    obj = VectorAnnotation(AnnotationType.LINE, 120, 120, page=0)
    other = VectorAnnotation(AnnotationType.ELLIPSE, 300, 300, page=1)
    canvas.add_object(obj)
    canvas.goto_page(1)
    canvas.add_object(other)
    canvas.goto_page(0)

    canvas.select_annotation(obj)
    canvas.remove_selected()
    canvas.goto_page(1)
    canvas.undo()
    assert canvas.page_objects_at(0) == [obj]

    assert canvas.redo() is True

    assert canvas.page_objects_at(0) == [], "redo must delete from page 1"
    assert canvas.page_objects_at(1) == [other], "page 2 must be untouched"
