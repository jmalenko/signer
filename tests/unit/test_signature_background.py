"""Unit tests for signer.signature_background (pure image-processing helpers)."""

from __future__ import annotations

from PIL import Image
import pytest

from signer.signature_background import (
    RECOMMENDED_MAX_PT,
    RECOMMENDED_MIN_PT,
    auto_trim,
    fit_to_recommended_range,
    height_px_to_pt,
    remove_background,
    remove_background_by_color,
    remove_background_combined,
    resize_to_height_pt,
)


def test_remove_background_white_becomes_transparent():
    img = Image.new("RGB", (10, 10), (255, 255, 255))
    result = remove_background(img)
    assert result.mode == "RGBA"
    assert result.getpixel((5, 5))[3] == 0


def test_remove_background_black_stays_opaque():
    img = Image.new("RGB", (10, 10), (0, 0, 0))
    result = remove_background(img)
    assert result.getpixel((5, 5))[3] == 255


def test_remove_background_mid_gray_is_partially_transparent_with_default_softness():
    # Default threshold 200, softness 40 => band is [180, 220]; 200 is exactly the midpoint.
    img = Image.new("RGB", (4, 4), (200, 200, 200))
    result = remove_background(img)
    alpha = result.getpixel((0, 0))[3]
    assert 100 < alpha < 155


def test_remove_background_never_increases_existing_transparency():
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 50))  # dark but already mostly transparent
    result = remove_background(img)
    assert result.getpixel((0, 0))[3] <= 50


def test_remove_background_threshold_and_softness_affect_cutoff():
    img = Image.new("RGB", (4, 4), (150, 150, 150))
    # With default params, luminance 150 is below the band (opaque).
    assert remove_background(img).getpixel((0, 0))[3] == 255
    # Lowering the threshold moves the band down, making the same pixel transparent.
    assert remove_background(img, threshold=100, softness=10).getpixel((0, 0))[3] == 0


def test_auto_trim_removes_transparent_border():
    img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    for x in range(4, 6):
        for y in range(4, 6):
            img.putpixel((x, y), (0, 0, 0, 255))
    trimmed = auto_trim(img)
    assert trimmed.size == (2, 2)


def test_auto_trim_no_op_when_fully_opaque():
    img = Image.new("RGBA", (5, 5), (0, 0, 0, 255))
    trimmed = auto_trim(img)
    assert trimmed.size == (5, 5)


def test_auto_trim_non_rgba_returned_unchanged():
    img = Image.new("RGB", (5, 5), (255, 0, 0))
    assert auto_trim(img).size == (5, 5)


def test_height_px_to_pt_at_300_dpi():
    # 300 px at 300 DPI == 1 inch == 72pt.
    assert height_px_to_pt(300, dpi=300) == 72.0


def test_resize_to_height_pt_preserves_aspect_ratio():
    img = Image.new("RGBA", (200, 100), (0, 0, 0, 255))  # 2:1 aspect ratio
    resized = resize_to_height_pt(img, target_height_pt=36.0, dpi=300)  # 150px tall
    assert resized.height == 150
    assert resized.width == 300


def test_fit_to_recommended_range_scales_down_oversized_signature():
    tall = Image.new("RGBA", (100, 300), (0, 0, 0, 255))  # 72pt tall at 300 DPI
    fitted = fit_to_recommended_range(tall)
    assert height_px_to_pt(fitted.height) == pytest.approx(RECOMMENDED_MAX_PT, abs=0.1)


def test_fit_to_recommended_range_scales_up_undersized_signature():
    tiny = Image.new("RGBA", (10, 20), (0, 0, 0, 255))  # ~4.8pt tall at 300 DPI
    fitted = fit_to_recommended_range(tiny)
    assert height_px_to_pt(fitted.height) == pytest.approx(RECOMMENDED_MIN_PT, abs=0.1)


def test_fit_to_recommended_range_leaves_in_range_signature_untouched():
    # 60px tall at 300 DPI == 14.4pt, inside [10, 24].
    img = Image.new("RGBA", (60, 60), (0, 0, 0, 255))
    fitted = fit_to_recommended_range(img)
    assert fitted.size == img.size


def test_remove_background_by_color_keeps_matching_hue():
    blue = (20, 40, 160)
    img = Image.new("RGB", (4, 4), blue)
    result = remove_background_by_color(img, target_rgb=blue)
    assert result.getpixel((0, 0))[3] == 255


def test_remove_background_by_color_drops_black_text():
    # Blue ink pixel next to black text: only the blue pixel should stay opaque.
    blue = (20, 40, 160)
    img = Image.new("RGB", (2, 1))
    img.putpixel((0, 0), blue)
    img.putpixel((1, 0), (0, 0, 0))
    result = remove_background_by_color(img, target_rgb=blue)
    assert result.getpixel((0, 0))[3] == 255
    assert result.getpixel((1, 0))[3] == 0


def test_remove_background_by_color_drops_white_background():
    blue = (20, 40, 160)
    img = Image.new("RGB", (1, 1), (255, 255, 255))
    result = remove_background_by_color(img, target_rgb=blue)
    assert result.getpixel((0, 0))[3] == 0


def test_remove_background_by_color_drops_far_hue():
    blue = (20, 40, 160)
    red = (200, 20, 20)
    img = Image.new("RGB", (1, 1), red)
    result = remove_background_by_color(img, target_rgb=blue, tolerance=30, softness=10)
    assert result.getpixel((0, 0))[3] == 0


def test_remove_background_by_color_never_increases_existing_transparency():
    blue = (20, 40, 160)
    img = Image.new("RGBA", (1, 1), (*blue, 40))
    result = remove_background_by_color(img, target_rgb=blue)
    assert result.getpixel((0, 0))[3] <= 40


def test_combined_removal_requires_both_luminance_and_color_matches():
    blue = (20, 40, 160)
    img = Image.new("RGB", (2, 1))
    img.putpixel((0, 0), blue)
    img.putpixel((1, 0), (255, 0, 0))

    result = remove_background_combined(
        img,
        threshold=100,
        luminance_softness=10,
        target_rgb=blue,
        tolerance=30,
        color_softness=10,
    )
    assert result.getpixel((0, 0))[3] == 255
    assert result.getpixel((1, 0))[3] == 0


def test_combined_removal_applies_luminance_to_matching_ink_too():
    # A pale blue pixel matches the target hue but fails the luminance filter.
    pale_blue = (180, 190, 255)
    img = Image.new("RGB", (1, 1), pale_blue)
    result = remove_background_combined(
        img,
        threshold=100,
        luminance_softness=10,
        target_rgb=pale_blue,
        tolerance=30,
        color_softness=10,
    )
    assert result.getpixel((0, 0))[3] == 0
