"""Resizing a text box derives the largest whole-point font size that fits it (spec §7.2)."""

import pytest

from signer.objects import AnnotationType, VectorAnnotation


@pytest.mark.parametrize("factor, expected_pt", [(1.05, 12), (1.2, 14), (1.5, 18), (0.95, 11), (2.0, 24)])
def test_resize_picks_the_largest_font_that_fits(qapp, factor, expected_pt):
    text = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Hello world", font_size_pt=12)
    width, height = text.scaled_width, text.scaled_height

    text.resize_to_bounds(width * factor, height * factor)

    assert text._font_size_pt == expected_pt
    assert text.scaled_width <= width * factor * 1.02
    assert text.scaled_height <= height * factor * 1.02
