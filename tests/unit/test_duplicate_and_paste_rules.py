"""Duplicate and paste: copies stay on the page, keep their relative positions and stacking
order, and paste uses the most recent copy (spec §7.7, §9)."""

import json

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from signer.objects import AnnotationType, VectorAnnotation


@pytest.fixture
def page_canvas(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    return canvas


def kinds(canvas):
    return [obj.ann_type for obj in canvas.current_page_objects()]


def test_a_single_duplicate_stays_on_the_page(page_canvas):
    obj = VectorAnnotation(AnnotationType.CHECKMARK, 1000 - 83.4, 100)
    page_canvas.add_object(obj)

    page_canvas.duplicate_selected()

    copy = page_canvas.selected
    assert copy is not obj
    assert copy.x + copy.scaled_width <= 1000 + 1e-6


def test_duplicating_several_keeps_their_relative_positions_even_at_the_edge(page_canvas):
    first = VectorAnnotation(AnnotationType.CHECKMARK, 800, 100)
    second = VectorAnnotation(AnnotationType.CHECKMARK, 900 - 1, 400)
    page_canvas.add_object(first)
    page_canvas.add_object(second)
    page_canvas.select_all_on_page()

    page_canvas.duplicate_selected()

    copies = page_canvas.get_selected_annotations()
    assert len(copies) == 2
    assert all(c.x + c.scaled_width <= 1000 + 1e-6 for c in copies)
    by_y = sorted(copies, key=lambda c: c.y)
    assert by_y[1].x - by_y[0].x == pytest.approx(second.x - first.x)
    assert by_y[1].y - by_y[0].y == pytest.approx(second.y - first.y)


def test_duplicates_keep_the_stacking_order(page_canvas):
    low = VectorAnnotation(AnnotationType.RECTANGLE, 500, 500)   # below, added first
    high = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100)   # on top, but higher on the page
    page_canvas.add_object(low)
    page_canvas.add_object(high)
    page_canvas.select_all_on_page()

    page_canvas.duplicate_selected()

    assert kinds(page_canvas)[2:] == [AnnotationType.RECTANGLE, AnnotationType.ELLIPSE]


def test_paste_keeps_the_stacking_order(page_canvas):
    low = VectorAnnotation(AnnotationType.RECTANGLE, 500, 500)
    high = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100)
    page_canvas.add_object(low)
    page_canvas.add_object(high)
    page_canvas.select_all_on_page()
    page_canvas.copy_selected()

    page_canvas.paste_selected()

    assert kinds(page_canvas)[2:] == [AnnotationType.RECTANGLE, AnnotationType.ELLIPSE]


def test_paste_uses_the_most_recent_copy_even_from_another_window(page_canvas):
    original = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    page_canvas.add_object(original)
    page_canvas.copy_selected()
    page_canvas.paste_selected()  # the first paste caches the copy

    other = VectorAnnotation(AnnotationType.CHECKMARK, 300, 300)
    QApplication.clipboard().setText(json.dumps([other.to_dict()]))
    page_canvas.paste_selected()

    assert page_canvas.selected.ann_type == AnnotationType.CHECKMARK


def test_paste_ignores_text_on_the_clipboard_that_is_not_annotations(page_canvas):
    original = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    page_canvas.add_object(original)
    page_canvas.copy_selected()
    QApplication.clipboard().setText("just some words")

    page_canvas.paste_selected()

    assert page_canvas.selected.ann_type == AnnotationType.RECTANGLE
