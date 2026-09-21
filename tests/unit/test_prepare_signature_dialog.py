"""Unit tests for the Prepare Signature tool dialog."""

import itertools
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QApplication, QMessageBox

from signer.prepare_signature_dialog import PrepareSignatureDialog
from signer.signature_background import (
    RECOMMENDED_MAX_PT,
    RECOMMENDED_MIN_PT,
    alpha_row_histogram,
    height_px_to_pt,
)


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_scan_with_dark_square() -> Image.Image:
    # A light-gray page with a small black square standing in for a signature.
    img = Image.new("RGB", (200, 200), (240, 240, 240))
    for x in range(80, 120):
        for y in range(80, 100):
            img.putpixel((x, y), (0, 0, 0))
    return img


def _make_scan_with_blue_ink_over_black_text() -> Image.Image:
    # White page, black "text" block, with a blue "signature" stroke crossing over it.
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    for x in range(20, 80):
        for y in range(40, 60):
            img.putpixel((x, y), (0, 0, 0))
    for x in range(10, 90):
        for y in range(45, 50):
            img.putpixel((x, y), (20, 40, 160))
    return img


def test_dialog_starts_on_stage1(qapp):
    dialog = PrepareSignatureDialog()
    assert dialog._stack.currentIndex() == 0


def test_debug_mode_does_not_auto_open_signature_tool(qapp, monkeypatch):
    monkeypatch.setenv("DEBUG", "1")
    dialog = PrepareSignatureDialog()
    assert dialog._stack.currentIndex() == 0
    assert dialog._source_path is None


def test_show_boundary_checkbox_is_checked_by_default(qapp):
    dialog = PrepareSignatureDialog()
    assert dialog._show_boundary_checkbox.isChecked() is True


def test_crop_and_tuning_produces_trimmed_transparent_image(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._page_index = 0
    dialog._go_to_crop()
    assert dialog._stack.currentIndex() == 1

    # Simulate the user having drawn a selection around the dark square (with some slack).
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()
    assert dialog._stack.currentIndex() == 2

    final = dialog._final_image
    assert final is not None
    assert final.mode == "RGBA"
    # The top-60% candidate band is 12px high and scales to 50px; the full output is larger.
    assert final.size == (167, 83)


def test_stage2_fits_source_image_to_available_view(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [Image.new("RGB", (2400, 1600), (255, 255, 255))]
    dialog._go_to_crop()
    dialog._crop_widget.fit_to_view()

    assert dialog._crop_widget._zoom <= 1.0
    assert dialog._crop_widget.width() <= dialog._crop_widget._viewport_provider.viewport().width()
    assert dialog._crop_widget.height() <= dialog._crop_widget._viewport_provider.viewport().height()


def test_stage2_manual_zoom_survives_viewport_resize(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [Image.new("RGB", (2400, 1600), (255, 255, 255))]
    dialog._go_to_crop()
    dialog._crop_widget.zoom_in()
    manual_zoom = dialog._crop_widget._zoom

    dialog._crop_widget._viewport_provider.resize(700, 500)
    qapp.processEvents()

    assert dialog._crop_widget._auto_fit is False
    assert dialog._crop_widget._zoom == manual_zoom


def test_stage3_processes_only_stage2_selection(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    processed = dialog._compute_processed_image()
    assert processed is not None
    assert processed.size == (60, 40)


def test_fit_to_range_toggle_rescales_into_recommended_bounds(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    dialog._fit_range_checkbox.setChecked(True)
    final = dialog._final_image
    assert final is not None
    height_pt = height_px_to_pt(final.height)
    assert RECOMMENDED_MIN_PT - 0.5 <= height_pt <= RECOMMENDED_MAX_PT + 0.5


def test_scale_mode_has_no_height_input(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()

    assert dialog._fit_to_range is True
    assert not hasattr(dialog, "_height_spin")


def test_crop_rectangle_can_be_drawn_from_bottom_right_corner(qapp):
    """Bug: dragging from the bottom-right corner toward top-left must still produce
    the correct rectangle, the same as dragging from top-left toward bottom-right."""
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    widget = dialog._crop_widget

    widget.begin_selection(QPointF(150, 150))
    widget.update_selection(QPointF(100, 100))
    widget.update_selection(QPointF(50, 50))

    rect = widget.crop_rect()
    assert rect.topLeft() == QPointF(50, 50)
    assert rect.bottomRight() == QPointF(150, 150)


def test_combined_method_drops_black_text_under_blue_signature(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_blue_ink_over_black_text()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(0, 0, 100, 100)
    dialog._go_to_tuning()

    dialog._color_method_checkbox.setChecked(True)
    dialog._ink_color = (20, 40, 160)
    dialog._update_preview()

    final = dialog._final_image
    assert final is not None
    rgba = final.convert("RGBA")
    # No fully-black-and-opaque pixel should remain (the black text was removed, only
    # the blue ink stroke stays visible even though it crossed over the black text).
    opaque_pixels = [p for p in rgba.getdata() if p[3] > 0]
    assert opaque_pixels, "expected the blue ink to remain"
    assert all(not (p[0] < 30 and p[1] < 30 and p[2] < 30) for p in opaque_pixels)


def test_preview_histogram_matches_post_method_image(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_blue_ink_over_black_text()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(0, 0, 100, 100)
    dialog._go_to_tuning()

    processed_histogram = alpha_row_histogram(dialog._compute_processed_image())

    assert dialog._last_histogram == processed_histogram


def test_preview_histogram_hidden_when_debug_disabled(qapp, monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    dialog = PrepareSignatureDialog()
    image = Image.new("RGBA", (80, 80), (255, 255, 255, 0))
    histogram = ((0, 0, 80, 80), [10, 20, 30, 40, 50, 60])

    dialog._render_preview(
        image,
        boundary_bbox=(0, 0, 80, 80),
        post_method_histogram=histogram,
    )

    pixmap = dialog._preview_label.pixmap()
    assert pixmap is not None
    img = pixmap.toImage()
    greenish = False
    for y in range(img.height()):
        for x in range(img.width()):
            color = img.pixelColor(x, y)
            r, g, b, a = color.getRgb()
            if g > 140 and r < 120 and b < 120 and a > 0:
                greenish = True
                break
        if greenish:
            break

    assert greenish is False


def test_preview_histogram_hidden_when_scaling_disabled(qapp, monkeypatch):
    monkeypatch.setenv("DEBUG", "1")
    dialog = PrepareSignatureDialog()
    dialog._fit_to_range = False
    image = Image.new("RGBA", (80, 80), (255, 255, 255, 0))
    histogram = ((0, 0, 80, 80), [10, 20, 30, 40, 50, 60])

    dialog._render_preview(
        image,
        boundary_bbox=(0, 0, 80, 80),
        post_method_histogram=histogram,
    )

    pixmap = dialog._preview_label.pixmap()
    assert pixmap is not None
    img = pixmap.toImage()
    greenish = False
    for y in range(img.height()):
        for x in range(img.width()):
            color = img.pixelColor(x, y)
            r, g, b, a = color.getRgb()
            if g > 140 and r < 120 and b < 120 and a > 0:
                greenish = True
                break
        if greenish:
            break

    assert greenish is False


def test_preview_keeps_same_position_when_debug_expansion_bars_are_added(qapp, monkeypatch):
    monkeypatch.setenv("DEBUG", "1")
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    original_pan = QPointF(32, -14)
    dialog._preview_pan = original_pan
    dialog._fit_range_checkbox.setChecked(False)
    dialog._fit_range_checkbox.setChecked(True)

    assert dialog._preview_pan == original_pan


def test_methods_use_independent_checkboxes_and_controls(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_blue_ink_over_black_text()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(0, 0, 100, 100)
    dialog._go_to_tuning()

    assert dialog._luminance_method_checkbox.isChecked() is True
    assert dialog._color_method_checkbox.isChecked() is True
    assert dialog._luminance_controls.isEnabled() is True
    assert dialog._color_controls.isEnabled() is True

    dialog._color_method_checkbox.setChecked(False)
    assert dialog._luminance_method_checkbox.isChecked() is True
    assert dialog._color_method_checkbox.isChecked() is False
    assert dialog._luminance_controls.isEnabled() is True
    assert dialog._color_controls.isEnabled() is False


def test_methods_can_be_disabled_independently(qapp):
    dialog = PrepareSignatureDialog()
    dialog._luminance_method_checkbox.setChecked(False)

    assert dialog._luminance_controls.isEnabled() is False
    assert dialog._color_method_checkbox.isChecked() is True

    dialog._color_method_checkbox.setChecked(True)
    assert dialog._color_controls.isEnabled() is True


def test_height_fit_is_selected_by_default(qapp):
    dialog = PrepareSignatureDialog()
    assert dialog._fit_range_checkbox.isChecked() is True
    assert dialog._fit_to_range is True
    assert dialog._color_method_checkbox.isChecked() is True


def test_scaled_mode_shows_status_and_hides_height_input(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    assert dialog._scale_status_label.isVisible() is False
    assert dialog._scale_status_label.text() == ""


def test_preview_canvas_fits_selection_to_viewport(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(0, 0, 200, 200)
    dialog._go_to_tuning()

    viewport = dialog._preview_scroll.viewport().size()
    assert dialog._preview_label.width() <= viewport.width()
    assert dialog._preview_label.height() <= viewport.height()


def test_preview_canvas_size_is_fixed_to_crop_regardless_of_sliders(qapp):
    """The Stage 3 preview must show the full user-drawn crop at a fixed size; only the
    boundary overlay (not the preview itself) should reflect threshold/softness changes."""
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    size_before = dialog._compute_processed_image().size
    dialog._threshold_slider.setValue(50)
    size_after = dialog._compute_processed_image().size

    assert size_before == size_after == (60, 40)


def test_stage3_preview_uses_full_selection_scroll_area(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()

    assert dialog._preview_scroll.widget() is dialog._preview_label
    assert dialog._preview_label.width() >= 60
    assert dialog._preview_label.height() >= 40


def test_boundary_bbox_matches_final_trimmed_size(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    full = dialog._compute_processed_image()
    bbox = full.split()[3].getbbox()
    left, top, right, bottom = bbox
    assert (right - left, bottom - top) == (40, 20)
    assert dialog._final_image.size == (167, 83)


def test_character_guides_use_full_crop_boundary_coordinates(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    boundary = dialog._last_boundary_bbox
    band = dialog._last_character_band
    assert boundary is not None
    assert band is not None
    assert boundary[1] <= band[0] < band[1] <= boundary[3]


def test_red_guides_use_sixty_percent_expansion_band(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    assert dialog._last_expansion_bands is not None
    assert dialog._last_guide_band == dialog._last_expansion_bands[5]


def test_scaling_summary_reports_character_boundary_and_output_heights(qapp, monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._crop_loaded_page_index = None
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    output = capsys.readouterr().out
    assert "scaling summary:" in output
    assert "Regular character height =" in output
    assert "boundary-box height =" in output
    assert "total output signature height =" in output


def test_expansion_bars_start_at_sixty_percent_and_are_nested(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._color_method_checkbox.setChecked(False)
    dialog._go_to_tuning()

    bands = dialog._last_expansion_bands
    assert bands is not None
    assert len(bands) == 9
    for previous, current in itertools.pairwise(bands):
        assert current[0] <= previous[0]
        assert current[1] >= previous[1]


def test_opening_a_scan_marks_dialog_dirty(qapp):
    dialog = PrepareSignatureDialog()
    assert dialog._dirty is False
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()
    dialog._dirty = True  # simulate what _open_scan sets after a successful load
    assert dialog._dirty is True


def test_close_without_saving_prompts_confirmation(qapp, tmp_path):
    dialog = PrepareSignatureDialog()
    dialog._dirty = True

    with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as mock_question:
        dialog.close()
        mock_question.assert_called_once()
    assert dialog._dirty is True  # unchanged; user chose not to close


def test_close_without_saving_confirmed_closes_dialog(qapp):
    dialog = PrepareSignatureDialog()
    dialog._dirty = True

    with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
        dialog.close()
    assert not dialog.isVisible()


def test_saving_clears_dirty_flag(qapp, tmp_path):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()
    dialog._dirty = True

    save_path = str(tmp_path / "signature.png")
    with patch("signer.prepare_signature_dialog.QFileDialog.getSaveFileName", return_value=(save_path, "")):
        dialog._save()

    assert dialog._dirty is False
    assert dialog._stack.currentIndex() == 2


def test_going_back_and_forth_preserves_crop_selection(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)

    # Back to Stage 1, then Continue again - the crop selection must survive.
    dialog._stack.setCurrentIndex(0)
    dialog._go_to_crop()

    assert dialog._stack.currentIndex() == 1
    assert dialog._crop_widget.crop_rect() == QRectF(70, 70, 60, 40)


def test_going_back_and_forth_preserves_tuning_settings(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()

    dialog._threshold_slider.setValue(42)
    dialog._softness_slider.setValue(17)

    # Back to Stage 2, then Next again - slider values must not reset to defaults.
    dialog._stack.setCurrentIndex(1)
    dialog._go_to_tuning()

    assert dialog._threshold_slider.value() == 42
    assert dialog._softness_slider.value() == 17


def test_dragging_preview_pans_the_composited_image(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()

    assert dialog._preview_pan == QPointF(0, 0)
    dialog._on_preview_dragged(15, -8)
    assert dialog._preview_pan == QPointF(15, -8)


def test_preview_pan_resets_when_crop_size_changes(qapp):
    dialog = PrepareSignatureDialog()
    dialog._pages = [_make_scan_with_dark_square()]
    dialog._go_to_crop()
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()
    dialog._on_preview_dragged(20, 20)
    assert dialog._preview_pan != QPointF(0, 0)

    # Go back, draw a differently-sized selection, and re-enter tuning.
    dialog._stack.setCurrentIndex(1)
    dialog._crop_widget._rect = QRectF(10, 10, 30, 30)
    dialog._go_to_tuning()

    assert dialog._preview_pan == QPointF(0, 0)

