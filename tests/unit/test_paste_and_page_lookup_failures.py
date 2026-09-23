"""Regression tests: partially-failed pastes and out-of-range page lookups must
surface instead of being papered over.

See CODE_REVIEW_PLAN.md sections B4 and B5.
"""

import json

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from signer.objects import AnnotationType, VectorAnnotation


def _setup_page(canvas, count=1):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white") for _ in range(count)])


def _clipboard_with(items):
    QApplication.clipboard().setText(json.dumps(items))


def test_paste_reports_items_it_could_not_deserialize(canvas):
    """Two good annotations and one broken one must paste 2 and say so."""
    _setup_page(canvas)
    good = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0).to_dict()
    other = VectorAnnotation(AnnotationType.CROSSMARK, 200, 200, page=0).to_dict()
    broken = dict(good)
    del broken["base_width"]
    _clipboard_with([good, broken, other])
    canvas._cached_copy_data = None

    reported = []
    canvas.pasteIncomplete.connect(lambda skipped, total: reported.append((skipped, total)))

    canvas.paste_selected()

    assert reported == [(1, 3)]
    assert len(canvas.page_objects_at(0)) == 2


def test_paste_of_fully_valid_data_does_not_report_a_problem(canvas):
    _setup_page(canvas)
    good = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0).to_dict()
    _clipboard_with([good])
    canvas._cached_copy_data = None

    reported = []
    canvas.pasteIncomplete.connect(lambda skipped, total: reported.append((skipped, total)))

    canvas.paste_selected()

    assert reported == []
    assert len(canvas.page_objects_at(0)) == 1


def test_page_image_for_an_out_of_range_index_raises(canvas):
    """Returning page 1's pixels for page 99 would export plausible-but-wrong output."""
    _setup_page(canvas, count=2)

    with pytest.raises(IndexError):
        canvas.get_page_image_with_rotation(5)
    with pytest.raises(IndexError):
        canvas.get_page_image_with_rotation(-1)


def test_rotated_objects_for_an_out_of_range_index_raises(canvas):
    _setup_page(canvas, count=2)
    canvas._page_rotations[7] = 90

    with pytest.raises(IndexError):
        canvas.page_objects_with_rotation_at(7)


def test_page_image_for_every_valid_index_still_works(canvas):
    _setup_page(canvas, count=3)
    canvas.rotate_all_pages_left()

    for index in range(3):
        assert canvas.get_page_image_with_rotation(index).size == (800, 800)
