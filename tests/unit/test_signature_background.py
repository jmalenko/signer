"""Unit tests for signer.signature_background (pure image-processing helpers)."""

from __future__ import annotations

from PIL import Image
import pytest

from signer.debug import debug_print
from signer.signature_background import (
    RECOMMENDED_MAX_PT,
    RECOMMENDED_MIN_PT,
    CHARACTER_TARGET_PT,
    alpha_row_histogram,
    auto_trim,
    calculate_character_scaling_factor,
    estimate_regular_character_band,
    expansion_bands_for_character,
    fit_to_recommended_range,
    height_px_to_pt,
    histogram_mass_percentile_indices,
    histogram_mass_percentile_positions,
    histogram_cumulative_mass_at_fractions,
    remove_background,
    remove_background_by_color,
    remove_background_combined,
    resize_to_height_pt,
    resize_by_factor,
)


def test_debug_print_uses_caller_filename_by_default(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")

    debug_print("message")

    assert capsys.readouterr().out == "[test_signature_background] message\n"


def test_debug_print_accepts_explicit_tag(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")

    debug_print("message", tag="/tmp/custom_source.py")

    assert capsys.readouterr().out == "[custom_source] message\n"


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


def test_estimate_regular_character_band_uses_top_sixty_percent():
    image = Image.new("RGBA", (20, 100), (0, 0, 0, 0))
    for y in range(10, 40):
        for x in range(5, 15):
            image.putpixel((x, y), (0, 0, 0, 255))
    for y in range(75, 100):
        image.putpixel((10, y), (0, 0, 0, 255))

    band = estimate_regular_character_band(image)

    assert band is not None
    assert band[0] <= 10
    assert band[1] >= 40
    assert band[1] < 75


def test_alpha_row_histogram_returns_visible_bounds_and_row_sums():
    image = Image.new("RGBA", (5, 6), (0, 0, 0, 0))
    image.putpixel((2, 1), (0, 0, 0, 255))
    image.putpixel((1, 2), (0, 0, 0, 128))
    image.putpixel((2, 2), (0, 0, 0, 255))

    result = alpha_row_histogram(image)

    assert result is not None
    bbox, values = result
    assert bbox == (1, 1, 3, 3)
    assert values == [255, 383]


def test_histogram_percentiles_follow_ink_mass_not_row_spacing():
    values = [100, 100, 800, 100, 100]

    indices = histogram_mass_percentile_indices(values, [0, 10, 50, 90, 100])

    assert indices[0] == 0
    assert indices[-1] == 4
    assert indices[1] == 1
    assert indices[2] == 2
    assert indices[3] == 3


def test_histogram_percentile_positions_interpolate_within_rows():
    values = [100, 100, 800, 100, 100]

    positions = histogram_mass_percentile_positions(values, [0, 10, 50, 80, 90, 100])

    assert positions[0] == 0.0
    assert positions[-1] == 5.0
    assert positions[1] == pytest.approx(1.2)
    assert positions[2] == pytest.approx(2.5)
    assert positions[3] == pytest.approx(2.95)
    assert positions[4] == pytest.approx(3.8)


def test_histogram_coverage_is_reported_at_fixed_expansion_ranges():
    values = [100, 100, 800, 100, 100]

    coverage = histogram_cumulative_mass_at_fractions(
        values,
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    )

    assert coverage == [0.0, pytest.approx(8.3333, abs=0.01),
                        pytest.approx(16.6667, abs=0.01),
                        pytest.approx(83.3333, abs=0.01),
                        pytest.approx(91.6667, abs=0.01),
                        pytest.approx(100.0, abs=0.01)]


def test_expansion_bands_grow_outward_from_character_band():
    values = [50, 50, 100, 100, 100, 50, 50]
    bands = expansion_bands_for_character(values, (2, 5), [10, 50, 90])

    assert all(start >= 0 and end <= len(values) for start, end in bands)
    assert bands[0][1] - bands[0][0] <= bands[1][1] - bands[1][0]
    assert bands[1][1] - bands[1][0] <= bands[2][1] - bands[2][0]


def test_expansion_debug_output_explains_each_decision(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")
    expansion_bands_for_character([10, 20, 30, 20, 10], (2, 3), [10])
    output = capsys.readouterr().out
    assert "Cumulative range " in output
    assert "(pixels " in output
    assert "considering adding" in output
    assert "which adds" in output
    assert "Chose" in output
    assert "Drawing bar for 10% expansion with range=" in output


def test_character_scaling_factor_targets_twelve_points():
    factor = calculate_character_scaling_factor(100)
    assert factor == pytest.approx((CHARACTER_TARGET_PT * 300 / 72) / 100)


def test_resize_by_factor_preserves_tall_strokes():
    image = Image.new("RGBA", (20, 100), (0, 0, 0, 255))
    resized = resize_by_factor(image, 0.5)
    assert resized.size == (10, 50)


def test_signature_debug_output_reports_histogram_and_scaling(
    monkeypatch, capsys
):
    monkeypatch.setenv("DEBUG", "1")
    image = Image.new("RGBA", (10, 20), (0, 0, 0, 0))
    for y in range(2, 10):
        image.putpixel((5, y), (0, 0, 0, 255))

    estimate_regular_character_band(image)
    calculate_character_scaling_factor(8)
    output = capsys.readouterr().out

    assert "histogram row=" in output
    assert "cumulative=" in output
    assert "incremental=" in output
    assert "selected=" in output
    assert "scaling factor:" in output


def test_histogram_debug_stars_visualize_incremental_coverage(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")
    image = Image.new("RGBA", (1, 2), (0, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 0, 255))
    image.putpixel((0, 1), (0, 0, 0, 128))

    estimate_regular_character_band(image)
    lines = [line for line in capsys.readouterr().out.splitlines()
             if "histogram row=" in line]

    assert len(lines) == 2
    assert "incremental=" in lines[0]
    assert "*" in lines[0]
    assert lines[0].index("*") == lines[1].index("*")


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
