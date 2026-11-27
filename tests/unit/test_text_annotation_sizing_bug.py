"""Regression tests for text annotation sizing and toolbar labels."""

import pytest
from PySide6.QtGui import QFontMetricsF

from signer.objects import AnnotationType, VectorAnnotation
from tests.utils.test_helpers import export_to_page


def test_new_text_bounding_box_contains_rendered_font(qapp):
    annotation = VectorAnnotation(
        AnnotationType.TEXT,
        0,
        0,
        text="WWW",
        font_size_pt=12,
    )
    metrics = QFontMetricsF(annotation._make_font())

    assert annotation._base_width >= metrics.boundingRect(annotation.text).width()
    assert annotation._base_height >= metrics.height()


def exported_text_ink(text: str, spacing: float) -> tuple[VectorAnnotation, tuple[int, int, int, int]]:
    annotation = VectorAnnotation(
        AnnotationType.TEXT, 100, 100, text=text, font_size_pt=12, character_spacing_pt=spacing,
    )
    return annotation, export_to_page(annotation).getchannel("A").getbbox()


@pytest.mark.parametrize("text", ["WWW", "Hello World", "WWW\nW"])
@pytest.mark.parametrize("spacing", [-6.0, -3.0, 0.0, 3.0, 6.0])
def test_text_box_contains_the_exported_text_at_any_character_spacing(qapp, text, spacing):
    annotation, bbox = exported_text_ink(text, spacing)
    assert bbox is not None
    assert bbox[0] >= 100 - 1  # anti-aliasing may bleed one pixel
    assert bbox[2] <= 100 + annotation.scaled_width + 1


def test_toolbar_property_labels_do_not_show_units(main_window):
    assert main_window._width_label.text() == "Width:"
    assert main_window._font_size_label.text() == "Font Size:"