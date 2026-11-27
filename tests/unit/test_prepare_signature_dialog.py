"""Unit tests for the Prepare Signature tool dialog."""

import itertools
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

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


@pytest.fixture(autouse=True)
def no_modal_message_boxes(monkeypatch):
    """A message box that is not mocked by a test must never block the run."""
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)


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
    assert dialog._scale_status_label.text().startswith("Regular character height:")


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



# --- Prepare Signature follows the specification (Version 1.8.4) ---------------------------

ENCRYPTED_PDF = Path(__file__).resolve().parents[2] / "examples" / "document-encrypted.pdf"


def _solid_scan(color) -> Image.Image:
    return Image.new("RGB", (200, 200), color)


def _load_scan(dialog, image, name="scan.png"):
    with patch("signer.prepare_signature_dialog.render_all_pages", return_value=[image]):
        dialog._load_source_path(Path(name))


def _open_tuning(dialog):
    _load_scan(dialog, _make_scan_with_dark_square())
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._go_to_tuning()


def _save_to(dialog, tmp_path):
    save_path = str(tmp_path / "signature.png")
    with patch("signer.prepare_signature_dialog.QFileDialog.getSaveFileName", return_value=(save_path, "")):
        dialog._save()


def test_second_scan_replaces_crop_image_and_selection(qapp):
    dialog = PrepareSignatureDialog()
    first = _solid_scan((10, 20, 30))
    second = _solid_scan((200, 100, 50))
    _load_scan(dialog, first, "first.png")
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)

    _load_scan(dialog, second, "second.png")

    assert dialog._stack.currentIndex() == 1
    assert dialog._crop_widget._image is second
    assert dialog._crop_widget.crop_rect() is None


def test_reloading_same_file_page_after_back_keeps_selection(qapp):
    dialog = PrepareSignatureDialog()
    _load_scan(dialog, _solid_scan((10, 20, 30)))
    dialog._crop_widget._rect = QRectF(70, 70, 60, 40)
    dialog._stack.setCurrentIndex(0)

    dialog._go_to_crop()

    assert dialog._crop_widget.crop_rect() == QRectF(70, 70, 60, 40)


def test_scale_checkbox_label_is_exactly_fit_12pt(qapp):
    dialog = PrepareSignatureDialog()
    assert dialog._fit_range_checkbox.text() == "Scale signature to fit 12pt"


def test_scale_status_shows_height_and_factor_and_clears_when_unchecked(qapp):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    dialog._color_method_checkbox.setChecked(False)

    text = dialog._scale_status_label.text()
    assert text.startswith("Regular character height: ")
    assert "pt, scaling factor " in text
    band = dialog._last_guide_band
    height_pt = height_px_to_pt(band[1] - band[0])
    assert f"{height_pt:.1f}pt" in text
    assert f"scaling factor {12.0 / height_pt:.2f}" in text

    dialog._fit_range_checkbox.setChecked(False)
    assert dialog._scale_status_label.text() == ""
    dialog._fit_range_checkbox.setChecked(True)
    assert dialog._scale_status_label.text() == text


def test_escape_without_opened_scan_closes_without_prompt(qapp):
    dialog = PrepareSignatureDialog()
    dialog.show()
    with patch.object(QMessageBox, "question") as question:
        QTest.keyClick(dialog, Qt.Key_Escape)
    question.assert_not_called()
    assert not dialog.isVisible()


def test_escape_after_opening_scan_asks_and_no_keeps_dialog_open(qapp):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    dialog.show()
    with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question:
        QTest.keyClick(dialog, Qt.Key_Escape)
    question.assert_called_once()
    args = question.call_args.args
    assert args[2] == "You have not saved the prepared signature. Close anyway?"
    assert args[4] == QMessageBox.No
    assert dialog.isVisible()
    dialog.hide()


def test_escape_after_opening_scan_yes_closes_dialog(qapp):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    dialog.show()
    with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
        QTest.keyClick(dialog, Qt.Key_Escape)
    assert not dialog.isVisible()
    assert dialog.result() == QDialog.Rejected


def test_reject_asks_for_confirmation_when_unsaved(qapp):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question:
        dialog.reject()
    question.assert_called_once()


def test_close_after_save_without_changes_does_not_prompt(qapp, tmp_path):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    _save_to(dialog, tmp_path)
    dialog.show()
    with patch.object(QMessageBox, "question") as question:
        dialog.reject()
    question.assert_not_called()
    assert not dialog.isVisible()


def test_close_via_x_after_save_without_changes_does_not_prompt(qapp, tmp_path):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    _save_to(dialog, tmp_path)
    with patch.object(QMessageBox, "question") as question:
        dialog.close()
    question.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d._threshold_slider.setValue(d._threshold_slider.value() - 20),
        lambda d: d._softness_slider.setValue(d._softness_slider.value() + 10),
        lambda d: d._color_tolerance_slider.setValue(d._color_tolerance_slider.value() + 10),
        lambda d: d._color_softness_slider.setValue(d._color_softness_slider.value() + 10),
        lambda d: d._luminance_method_checkbox.setChecked(False),
        lambda d: d._color_method_checkbox.setChecked(False),
        lambda d: d._set_ink_color((200, 0, 0)),
        lambda d: d._fit_range_checkbox.setChecked(False),
    ],
    ids=["threshold", "softness", "tolerance", "color-softness", "method1", "method2", "ink", "scale"],
)
def test_change_after_save_rearms_unsaved_prompt(qapp, tmp_path, change):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    _save_to(dialog, tmp_path)
    assert dialog._dirty is False

    change(dialog)

    assert dialog._dirty is True
    with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question:
        dialog.close()
    question.assert_called_once()


def test_crop_change_after_save_rearms_unsaved_prompt(qapp, tmp_path):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    _save_to(dialog, tmp_path)
    dialog._stack.setCurrentIndex(1)
    dialog._crop_widget._rect = QRectF(60, 60, 80, 60)
    dialog._go_to_tuning()

    assert dialog._dirty is True


def test_reentering_stage3_after_save_without_changes_stays_clean(qapp, tmp_path):
    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    _save_to(dialog, tmp_path)
    dialog._stack.setCurrentIndex(1)
    dialog._go_to_tuning()

    assert dialog._dirty is False


def _drag_widget(rect: QRectF, mode: str):
    from signer.prepare_signature_dialog import _CropWidget

    widget = _CropWidget()
    widget.set_image(Image.new("RGB", (400, 400), "white"))
    widget._rect = QRectF(rect)
    widget._rect_at_drag_start = QRectF(rect)
    widget._drag_mode = mode
    return widget


def test_dragging_left_edge_past_right_edge_keeps_right_edge_anchored(qapp):
    widget = _drag_widget(QRectF(100, 100, 100, 50), "ml")
    for x in (150, 199, 210, 250):
        widget.update_selection(QPointF(x, 120))
    rect = widget.crop_rect()
    assert (rect.left(), rect.right()) == (200, 250)
    assert (rect.top(), rect.bottom()) == (100, 150)


def test_dragging_edge_back_over_start_flips_again_without_creeping(qapp):
    widget = _drag_widget(QRectF(100, 100, 100, 50), "ml")
    widget.update_selection(QPointF(250, 120))
    widget.update_selection(QPointF(120, 120))
    rect = widget.crop_rect()
    assert (rect.left(), rect.right()) == (120, 200)


@pytest.mark.parametrize(
    "mode,steps,expected",
    [
        ("mr", [(60, 120), (40, 120)], (40, 100, 100, 150)),
        ("tm", [(150, 160), (150, 200)], (100, 150, 200, 200)),
        ("bm", [(150, 90), (150, 20)], (100, 20, 200, 100)),
        ("br", [(90, 90), (30, 20)], (30, 20, 100, 100)),
        ("tl", [(250, 200), (300, 300)], (200, 150, 300, 300)),
    ],
)
def test_dragging_edge_or_corner_past_opposite_keeps_opposite_anchored(qapp, mode, steps, expected):
    widget = _drag_widget(QRectF(100, 100, 100, 50), mode)
    for x, y in steps:
        widget.update_selection(QPointF(x, y))
    rect = widget.crop_rect()
    assert (rect.left(), rect.top(), rect.right(), rect.bottom()) == expected


def test_dragging_edge_with_mouse_events_keeps_opposite_edge_anchored(qapp):
    from PySide6.QtCore import QPoint

    widget = _drag_widget(QRectF(100, 100, 100, 50), "ml")
    widget._rect_at_drag_start = None
    widget._drag_mode = None
    QTest.mousePress(widget, Qt.LeftButton, Qt.NoModifier, QPoint(100, 125))
    for x in (150, 250, 300):
        QTest.mouseMove(widget, QPoint(x, 125))
    QTest.mouseRelease(widget, Qt.LeftButton, Qt.NoModifier, QPoint(300, 125))
    rect = widget.crop_rect()
    assert (rect.left(), rect.right()) == (200, 300)


def test_reset_restores_sliders_and_keeps_ink_color_and_method_checkboxes(qapp):
    from signer.signature_background import (
        DEFAULT_COLOR_SOFTNESS,
        DEFAULT_COLOR_TOLERANCE,
        DEFAULT_SOFTNESS,
        DEFAULT_THRESHOLD,
    )

    dialog = PrepareSignatureDialog()
    _open_tuning(dialog)
    dialog._set_ink_color((200, 10, 10))
    dialog._luminance_method_checkbox.setChecked(False)
    dialog._color_method_checkbox.setChecked(True)
    dialog._fit_range_checkbox.setChecked(False)
    dialog._threshold_slider.setValue(33)
    dialog._softness_slider.setValue(77)
    dialog._color_tolerance_slider.setValue(11)
    dialog._color_softness_slider.setValue(99)

    dialog._reset_sliders()

    assert dialog._threshold_slider.value() == int(DEFAULT_THRESHOLD)
    assert dialog._softness_slider.value() == int(DEFAULT_SOFTNESS)
    assert dialog._color_tolerance_slider.value() == int(DEFAULT_COLOR_TOLERANCE)
    assert dialog._color_softness_slider.value() == int(DEFAULT_COLOR_SOFTNESS)
    assert dialog._ink_color == (200, 10, 10)
    assert dialog._luminance_method_checkbox.isChecked() is False
    assert dialog._color_method_checkbox.isChecked() is True
    assert dialog._fit_range_checkbox.isChecked() is False


class _ScriptedPasswordDialog:
    """Stands in for the modal password dialog: replays typed passwords, then cancels."""

    typed: list[str] = []
    shown = 0

    def __init__(self, parent, pdf_filename):
        self.filename = pdf_filename

    def exec(self):
        type(self).shown += 1
        return QDialog.Accepted if type(self).typed else QDialog.Rejected

    def password(self):
        return type(self).typed.pop(0)


@pytest.fixture
def scripted_passwords(monkeypatch):
    import signer.main_window as main_window

    _ScriptedPasswordDialog.typed = []
    _ScriptedPasswordDialog.shown = 0
    monkeypatch.setattr(main_window, "_PasswordDialog", _ScriptedPasswordDialog)
    return _ScriptedPasswordDialog


def test_encrypted_pdf_opens_with_password_typed_at_first_prompt(qapp, scripted_passwords):
    scripted_passwords.typed = ["key123"]
    dialog = PrepareSignatureDialog()
    dialog._load_source_path(ENCRYPTED_PDF)

    assert dialog._pages
    assert dialog._source_path == ENCRYPTED_PDF
    assert scripted_passwords.shown == 1


def test_encrypted_pdf_opens_with_correct_password_at_third_prompt(qapp, scripted_passwords):
    scripted_passwords.typed = ["wrong1", "wrong2", "key123"]
    dialog = PrepareSignatureDialog()
    with patch.object(QMessageBox, "critical") as critical:
        dialog._load_source_path(ENCRYPTED_PDF)

    assert dialog._pages
    assert scripted_passwords.shown == 3
    critical.assert_not_called()


def test_encrypted_pdf_gives_up_after_three_wrong_passwords(qapp, scripted_passwords):
    scripted_passwords.typed = ["a", "b", "c", "key123"]
    dialog = PrepareSignatureDialog()
    with patch.object(QMessageBox, "critical") as critical:
        dialog._load_source_path(ENCRYPTED_PDF)

    assert dialog._pages == []
    assert dialog._source_path is None
    assert scripted_passwords.shown == 3
    critical.assert_called_once()
    assert critical.call_args.args[2] == "Incorrect password or maximum attempts exceeded."


def test_encrypted_pdf_cancelled_password_prompt_opens_nothing_silently(qapp, scripted_passwords):
    dialog = PrepareSignatureDialog()
    with patch.object(QMessageBox, "critical") as critical:
        dialog._load_source_path(ENCRYPTED_PDF)

    assert dialog._pages == []
    assert dialog._stack.currentIndex() == 0
    critical.assert_not_called()


def test_unencrypted_file_never_asks_for_password(qapp, scripted_passwords):
    dialog = PrepareSignatureDialog()
    _load_scan(dialog, _solid_scan((1, 2, 3)))
    assert scripted_passwords.shown == 0
