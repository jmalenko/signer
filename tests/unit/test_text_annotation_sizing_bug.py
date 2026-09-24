"""Regression tests for text annotation sizing and toolbar labels."""

from PySide6.QtGui import QFontMetricsF

from signer.objects import AnnotationType, VectorAnnotation


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


def test_text_box_keeps_rightmost_glyph_inside_for_zero_and_negative_spacing(qapp):
    for spacing in (0.0, -3.0):
        annotation = VectorAnnotation(
            AnnotationType.TEXT,
            0,
            0,
            text="WWW",
            font_size_pt=12,
            character_spacing_pt=spacing,
        )
        image = annotation.render_to_pil()
        alpha = image.getchannel("A")
        assert alpha.getbbox() is not None
        assert alpha.getbbox()[0] >= 0
        assert alpha.getbbox()[2] <= image.width


def test_toolbar_property_labels_do_not_show_units(main_window):
    assert main_window._width_label.text() == "Width:"
    assert main_window._font_size_label.text() == "Font Size:"