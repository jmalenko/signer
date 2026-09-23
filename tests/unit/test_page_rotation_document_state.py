"""Regression tests: page rotation is per-document state and the rotated pixmap
cache must always agree with it.

See CODE_REVIEW_PLAN.md sections A2 and A3.
"""

from PIL import Image


def _pages(count=2, size=(600, 800)):
    return [Image.new("RGB", size, color="white") for _ in range(count)]


def test_opening_another_document_clears_page_rotations(canvas):
    """Rotations belong to the document that was rotated, not to the canvas."""
    canvas.set_pages(_pages())
    canvas.rotate_current_page_left()
    assert canvas._page_rotations == {0: 90}

    canvas.set_pages(_pages())

    assert canvas._page_rotations == {}


def test_opening_another_document_keeps_pixmaps_consistent_with_rotation(canvas):
    """A stale rotation would make _recompute_fit() transpose a pixmap that was
    rebuilt unrotated, drawing the new document stretched into a swapped rect."""
    canvas.set_pages(_pages(size=(600, 800)))
    canvas.rotate_current_page_left()

    canvas.set_pages(_pages(size=(600, 800)))

    pixmap = canvas._page_pixmaps[0]
    assert (pixmap.width(), pixmap.height()) == (600, 800)
    assert canvas._page_rotations.get(0, 0) == 0


def test_restore_objects_rebuilds_pixmaps_for_rotated_pages(canvas):
    """Opening a project with rotated pages must render them rotated, the same as
    the interactive rotate path does."""
    canvas.set_pages(_pages(count=2, size=(600, 800)))

    canvas.restore_objects([], rotations={0: 90, 1: 180}, current_page=0)

    rotated = canvas._page_pixmaps[0]
    assert (rotated.width(), rotated.height()) == (800, 600)
    unrotated = canvas._page_pixmaps[1]
    assert (unrotated.width(), unrotated.height()) == (600, 800)


def test_restore_objects_matches_interactive_rotation_result(canvas):
    """Loading a 90-degree rotation from a project yields the same pixmap size as
    rotating the page by hand."""
    interactive = canvas
    interactive.set_pages(_pages(count=1, size=(600, 800)))
    interactive.rotate_current_page_left()
    expected = (interactive._page_pixmaps[0].width(), interactive._page_pixmaps[0].height())

    interactive.set_pages(_pages(count=1, size=(600, 800)))
    interactive.restore_objects([], rotations={0: 90}, current_page=0)

    loaded = (interactive._page_pixmaps[0].width(), interactive._page_pixmaps[0].height())
    assert loaded == expected
