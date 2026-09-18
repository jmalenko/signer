"""Unit tests for page rotation (single page and all pages)."""

import pytest
from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


def _pages(count=2, size=(200, 100)):
    return [Image.new("RGB", size, color="white") for _ in range(count)]


def test_rotate_current_page_left_is_cumulative(canvas):
    canvas.set_pages(_pages())

    canvas.rotate_current_page_left()
    assert canvas._page_rotations[0] == 90

    canvas.rotate_current_page_left()
    assert canvas._page_rotations[0] == 180

    # Other pages are untouched
    assert canvas._page_rotations.get(1, 0) == 0


def test_rotate_current_page_full_circle_returns_to_zero(canvas):
    canvas.set_pages(_pages())

    for _ in range(4):
        canvas.rotate_current_page_left()

    assert canvas._page_rotations[0] == 0


def test_rotate_current_page_right_is_270_left(canvas):
    canvas.set_pages(_pages())

    canvas.rotate_current_page_right()

    assert canvas._page_rotations[0] == 270


def test_rotate_current_page_left_then_right_restores_original_state(canvas):
    canvas.set_pages(_pages())
    original = dict(canvas._page_rotations)

    canvas.rotate_current_page_left()
    canvas.rotate_current_page_right()

    assert canvas._page_rotations.get(0, 0) == original.get(0, 0)


def test_rotate_all_pages_left_affects_every_page(canvas):
    canvas.set_pages(_pages(count=3))

    canvas.rotate_all_pages_left()

    assert canvas._page_rotations == {0: 90, 1: 90, 2: 90}


def test_rotate_all_pages_right_affects_every_page(canvas):
    canvas.set_pages(_pages(count=3))

    canvas.rotate_all_pages_right()

    assert canvas._page_rotations == {0: 270, 1: 270, 2: 270}


def test_rotation_swaps_fit_dimensions_for_90_and_270(canvas):
    canvas.set_pages(_pages(size=(200, 100)))
    canvas.resize(400, 400)

    canvas.rotate_current_page_left()

    # After a 90-degree rotation, the (originally 200x100) page is treated as
    # 100x200 when computing the fit scale/offset.
    dw, dh = canvas._pages[0].size
    assert (dw, dh) == (200, 100)  # underlying PIL image is unchanged...
    # ...but _recompute_fit() must have swapped dimensions for the rotated view.
    assert canvas._fit_scale == min(400 / 100, 400 / 200)


def test_restore_objects_converts_json_rotation_keys_to_page_indexes(canvas):
    canvas.set_pages(_pages(count=3))

    canvas.restore_objects([], rotations={"2": 90}, current_page=0)

    assert canvas._page_rotations == {2: 90}
    assert canvas._page_rotations.get(2) == 90


def test_rotated_export_uses_scaled_annotation_center(canvas):
    canvas.set_pages([Image.new("RGB", (400, 500), color="white")])
    annotation = VectorAnnotation(AnnotationType.CROSSMARK, 20, 120, 0)
    annotation.scale = 2.0
    canvas._page_objects[0] = [annotation]
    canvas._page_rotations[0] = 90

    rotated = canvas.page_objects_with_rotation_at(0)[0]

    assert rotated.x == 120.0
    assert rotated.y == pytest.approx(213.3333333333333)
