"""Regression tests: page rotation is an undoable action that restores each
page's own previous angle.

See CODE_REVIEW_PLAN.md section B6.
"""

from PIL import Image


def _pages(canvas, count=3, size=(600, 800)):
    canvas.set_pages([Image.new("RGB", size, color="white") for _ in range(count)])


def test_rotating_a_page_is_undoable(canvas):
    _pages(canvas)

    canvas.rotate_current_page_left()
    assert canvas.can_undo() is True

    assert canvas.undo() is True
    assert canvas._page_rotations.get(0, 0) == 0


def test_undo_restores_the_rotated_pixmap(canvas):
    _pages(canvas, count=1)

    canvas.rotate_current_page_left()
    assert (canvas._page_pixmaps[0].width(), canvas._page_pixmaps[0].height()) == (800, 600)

    canvas.undo()

    assert (canvas._page_pixmaps[0].width(), canvas._page_pixmaps[0].height()) == (600, 800)


def test_undo_of_rotate_all_keeps_per_page_differences(canvas):
    """Rotating one page, then all pages, then undoing must not flatten page 2
    to the same angle as the rest."""
    _pages(canvas)
    canvas.goto_page(1)
    canvas.rotate_current_page_left()
    assert canvas._page_rotations == {1: 90}

    canvas.rotate_all_pages_left()
    assert canvas._page_rotations == {0: 90, 1: 180, 2: 90}

    canvas.undo()

    assert canvas._page_rotations == {0: 0, 1: 90, 2: 0}


def test_redo_reapplies_the_rotation(canvas):
    _pages(canvas, count=2)

    canvas.rotate_all_pages_right()
    canvas.undo()
    assert canvas._page_rotations == {0: 0, 1: 0}

    assert canvas.redo() is True
    assert canvas._page_rotations == {0: 270, 1: 270}


def test_rotation_undo_does_not_consume_an_annotation_undo(canvas):
    """Ctrl+Z after a rotation must undo the rotation, not the previous edit."""
    from signer.objects import AnnotationType, VectorAnnotation

    _pages(canvas, count=1)
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    canvas.add_object(obj)

    canvas.rotate_current_page_left()
    canvas.undo()

    assert canvas._page_rotations.get(0, 0) == 0
    assert canvas.page_objects_at(0) == [obj], "the annotation must still be there"
