"""Regression tests: paste history must target the pasted annotations' own page.

See CODE_REVIEW_PLAN.md section B1.
"""

from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


def _setup_pages(canvas, count=3):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white") for _ in range(count)])


def _copy_one_annotation(canvas):
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    canvas.add_object(obj)
    canvas.select_annotation(obj)
    canvas.copy_selected()
    return obj


def test_undo_paste_removes_from_the_page_it_was_pasted_on(canvas):
    """Paste on page 1, navigate to page 2, undo -> the paste is gone from page 1."""
    _setup_pages(canvas)
    _copy_one_annotation(canvas)
    canvas.paste_selected()
    pasted = canvas.page_objects_at(0)[-1]
    assert len(canvas.page_objects_at(0)) == 2

    canvas.goto_page(1)
    assert canvas.undo() is True

    assert pasted not in canvas.page_objects_at(0)
    assert len(canvas.page_objects_at(0)) == 1


def test_undo_paste_keeps_stable_ids_of_objects_it_did_not_remove(canvas):
    """The `_object_map` entry must only be dropped for objects actually removed."""
    _setup_pages(canvas)
    _copy_one_annotation(canvas)
    canvas.paste_selected()
    pasted = canvas.page_objects_at(0)[-1]
    pasted_id = canvas._stable_id_for(pasted)

    # Something else takes the object off the page before the undo runs.
    canvas.page_objects_at(0).remove(pasted)
    canvas.goto_page(2)
    canvas.undo()

    assert canvas._object_map.get(pasted_id) is None or pasted not in canvas.page_objects_at(0)


def test_redo_paste_restores_onto_the_original_page(canvas):
    """Redo must put the annotations back where they were pasted, not on the visible page."""
    _setup_pages(canvas)
    _copy_one_annotation(canvas)
    canvas.paste_selected()
    pasted = canvas.page_objects_at(0)[-1]
    canvas.undo()
    assert pasted not in canvas.page_objects_at(0)

    canvas.goto_page(2)
    assert canvas.redo() is True

    assert pasted in canvas.page_objects_at(0)
    assert canvas.page_objects_at(2) == []
