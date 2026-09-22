"""Pure image-processing helpers for the "Prepare Signature" tool.

These functions have no Qt dependency so they can be unit tested directly on small
synthetic images. See FUNCTIONAL_SPECIFICATION.md §17 for the behavior they implement.
"""

from __future__ import annotations

import colorsys

from PIL import Image, ImageChops

from signer.debug import debug_print

# Luminance (0-255) cutoff: pixels lighter than this become fully transparent by default.
DEFAULT_THRESHOLD: float = 200.0
# Width (in luminance units) of the gradient band around the threshold.
DEFAULT_SOFTNESS: float = 40.0

# "Keep ink color" mode: default target color (typical ballpoint-pen blue) and tolerance.
DEFAULT_INK_COLOR: tuple[int, int, int] = (20, 40, 160)
# Hue distance (degrees, 0-180) cutoff: pixels further from the target hue become transparent.
DEFAULT_COLOR_TOLERANCE: float = 60.0
DEFAULT_COLOR_SOFTNESS: float = 30.0
# Pixels less saturated than this are treated as achromatic (black/white/gray) and dropped,
# regardless of hue, so black text/dots never get mistaken for the (saturated) ink color.
DEFAULT_MIN_SATURATION: float = 0.15

# Recommended signature height range, in points, so it reads naturally next to document text
# without needing to be resized after insertion (see FUNCTIONAL_SPECIFICATION.md §17.4).
RECOMMENDED_MIN_PT: float = 10.0
RECOMMENDED_MAX_PT: float = 24.0

# Rendering convention shared with the rest of the app (see objects.py DPI_SCALE).
DPI: int = 300
CHARACTER_BAND_TOP_FRACTION: float = 0.70
CHARACTER_TARGET_PT: float = 12.0
CHARACTER_EXPANSION_BASELINE_PERCENT: float = 60.0


def _apply_alpha_mask(rgba: Image.Image, computed_alpha: Image.Image) -> Image.Image:
    """Combine a computed visibility mask with existing source transparency."""
    combined_alpha = ImageChops.darker(computed_alpha, rgba.getchannel("A"))
    result = rgba.copy()
    result.putalpha(combined_alpha)
    return result


def remove_background(image: Image.Image, threshold: float = DEFAULT_THRESHOLD, softness: float = DEFAULT_SOFTNESS) -> Image.Image:
    """Return an RGBA copy of `image` with a luminance-based alpha channel.

    Pixels lighter than `threshold + softness/2` become fully transparent; pixels darker
    than `threshold - softness/2` stay fully opaque; in between, alpha ramps linearly,
    producing anti-aliased edges instead of a hard cutout.

    If `image` already has an alpha channel, the computed alpha is combined with the
    existing one (the more transparent of the two wins) so pre-existing transparency is
    never made more opaque.
    """
    rgba = image.convert("RGBA")
    luminance = rgba.convert("L")

    softness = max(softness, 1e-6)
    black_point = threshold - softness / 2.0
    white_point = threshold + softness / 2.0
    span = white_point - black_point

    lut = []
    for level in range(256):
        if level <= black_point:
            alpha = 255
        elif level >= white_point:
            alpha = 0
        else:
            alpha = round(255 * (white_point - level) / span)
        lut.append(alpha)

    computed_alpha = luminance.point(lut)

    return _apply_alpha_mask(rgba, computed_alpha)


def remove_background_by_color(
    image: Image.Image,
    target_rgb: tuple[int, int, int] = DEFAULT_INK_COLOR,
    tolerance: float = DEFAULT_COLOR_TOLERANCE,
    softness: float = DEFAULT_COLOR_SOFTNESS,
    min_saturation: float = DEFAULT_MIN_SATURATION,
) -> Image.Image:
    """Keep only pixels close in hue to `target_rgb`; make everything else transparent.

    Unlike `remove_background` (which keys on how *light* a pixel is), this keys on *hue*,
    so it can isolate colored ink (e.g. blue) even where it overlaps black text or sits on
    a background with dark dots/rules - those are excluded regardless of how dark or light
    they are, since they aren't close in hue to the target color.

    Pixels with saturation below `min_saturation` (near black/white/gray, where hue is
    undefined/noisy) are always made transparent, even if their hue happens to be close.
    Pixels already transparent in `image` are never made more opaque.
    """
    rgba = image.convert("RGBA")
    target_h, _target_s, _target_v = colorsys.rgb_to_hsv(*(c / 255.0 for c in target_rgb))

    softness = max(softness, 1e-6)
    lo = tolerance - softness / 2.0
    hi = tolerance + softness / 2.0
    span = hi - lo

    src = rgba.load()
    width, height = rgba.size
    computed_alpha = Image.new("L", rgba.size)
    dst = computed_alpha.load()
    for y in range(height):
        for x in range(width):
            r, g, b, _existing_alpha = src[x, y]
            hue, saturation, _value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if saturation < min_saturation:
                alpha = 0
            else:
                hue_distance = abs(hue - target_h)
                if hue_distance > 0.5:
                    # Hue is cyclic on [0, 1]; take the shorter way around the circle.
                    hue_distance = 1.0 - hue_distance
                hue_distance_deg = hue_distance * 360.0
                if hue_distance_deg <= lo:
                    alpha = 255
                elif hue_distance_deg >= hi:
                    alpha = 0
                else:
                    alpha = round(255 * (hi - hue_distance_deg) / span)
            dst[x, y] = alpha
    return _apply_alpha_mask(rgba, computed_alpha)


def remove_background_combined(
    image: Image.Image,
    threshold: float = DEFAULT_THRESHOLD,
    luminance_softness: float = DEFAULT_SOFTNESS,
    target_rgb: tuple[int, int, int] = DEFAULT_INK_COLOR,
    tolerance: float = DEFAULT_COLOR_TOLERANCE,
    color_softness: float = DEFAULT_COLOR_SOFTNESS,
    min_saturation: float = DEFAULT_MIN_SATURATION,
) -> Image.Image:
    """Apply luminance removal and ink-color removal as one combined method.

    Each filter contributes an alpha mask; taking the per-pixel minimum means a pixel must
    pass both filters to remain visible. Existing source transparency is preserved by both
    stages.
    """
    luminance_result = remove_background(image, threshold, luminance_softness)
    return remove_background_by_color(
        luminance_result,
        target_rgb,
        tolerance,
        color_softness,
        min_saturation,
    )


def auto_trim(image: Image.Image) -> Image.Image:
    """Crop `image` (RGBA) to the bounding box of its non-fully-transparent content.

    Returns the image unchanged if it has no alpha channel or is fully transparent.
    """
    if image.mode != "RGBA":
        return image
    bbox = image.split()[3].getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def alpha_row_histogram(
    image: Image.Image,
) -> tuple[tuple[int, int, int, int], list[int]] | None:
    """Return the visible alpha bounds and alpha-weighted sum for each bound row."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    values = [
        sum(alpha.getpixel((x, y)) for x in range(left, right))
        for y in range(top, bottom)
    ]
    return bbox, values


def histogram_mass_percentile_indices(
    row_values: list[int],
    percentages: list[int],
) -> list[int]:
    """Return row indices at cumulative alpha-mass percentiles."""
    total = sum(row_values)
    if total <= 0 or not row_values:
        return [0 for _ in percentages]
    indices = []
    for percent in percentages:
        target = total * percent / 100.0
        cumulative = 0
        selected = len(row_values) - 1
        for index, value in enumerate(row_values):
            cumulative += value
            if cumulative >= target:
                selected = index
                break
        indices.append(selected)
    return indices


def histogram_mass_percentile_positions(
    row_values: list[int],
    percentages: list[int],
) -> list[float]:
    """Return continuous row positions at cumulative alpha-mass percentiles.

    Position 0 is the top edge of the first row and position ``len(row_values)`` is
    the bottom edge. Interpolation within a row prevents several percentiles from
    collapsing onto one row when the histogram is dense.
    """
    total = sum(row_values)
    if total <= 0 or not row_values:
        return [0.0 for _ in percentages]
    positions = []
    for percent in percentages:
        target = total * percent / 100.0
        if target <= 0:
            positions.append(0.0)
            continue
        if target >= total:
            positions.append(float(len(row_values)))
            continue
        cumulative = 0.0
        position = float(len(row_values))
        for index, value in enumerate(row_values):
            next_cumulative = cumulative + value
            if next_cumulative >= target:
                fraction = (target - cumulative) / value if value else 0.0
                position = index + fraction
                break
            cumulative = next_cumulative
        positions.append(position)
    return positions


def histogram_cumulative_mass_at_fractions(
    row_values: list[int],
    fractions: list[float],
) -> list[float]:
    """Return cumulative ink percentages at fixed geometric row fractions."""
    total = sum(row_values)
    if total <= 0 or not row_values:
        return [0.0 for _ in fractions]
    result = []
    row_count = len(row_values)
    for fraction in fractions:
        row_count_at_fraction = min(
            row_count,
            max(0, round(row_count * fraction)),
        )
        covered = sum(row_values[:row_count_at_fraction])
        result.append(100.0 * covered / total)
    return result


def first_row_at_cumulative_percent(
    row_values: list[int],
    percent: float,
) -> int:
    """Return the first row whose cumulative alpha mass reaches `percent`."""
    total = sum(row_values)
    if total <= 0 or not row_values:
        return 0
    target = total * percent / 100.0
    cumulative = 0
    for index, value in enumerate(row_values):
        cumulative += value
        if cumulative >= target:
            return index
    return len(row_values) - 1


def expansion_bands_for_character(
    row_values: list[int],
    character_band: tuple[int, int],
    percentages: list[int],
) -> list[tuple[int, int]]:
    """Grow the character band greedily until each added-ink target is covered."""
    total = sum(row_values)
    if total <= 0 or not row_values:
        return [character_band for _ in percentages]
    baseline_row = first_row_at_cumulative_percent(
        row_values,
        CHARACTER_EXPANSION_BASELINE_PERCENT,
    )
    row_count = len(row_values)
    expanded_start = baseline_row
    expanded_end = baseline_row
    added_ink = 0
    bands = []
    for percent in percentages:
        target_added = total * percent / 100.0
        while added_ink < target_added and (expanded_start > 0 or expanded_end < row_count):
            top_value = row_values[expanded_start - 1] if expanded_start > 0 else -1
            bottom_value = row_values[expanded_end] if expanded_end < row_count else -1
            candidate_log = (
                f"Considering adding line {expanded_start - 1} "
                f"which adds {100 * max(0, top_value) / total:.2f}% of pixels; "
                f"considering adding line {expanded_end} "
                f"which adds {100 * max(0, bottom_value) / total:.2f}% of pixels. "
            )
            if top_value >= bottom_value and expanded_start > 0:
                expanded_start -= 1
                chosen_value = top_value
                chosen_row = expanded_start
            elif expanded_end < row_count:
                chosen_value = bottom_value
                chosen_row = expanded_end
                expanded_end += 1
            else:
                chosen_value = top_value
                expanded_start -= 1
                chosen_row = expanded_start
            added_ink += max(0, chosen_value)
            start_cumulative = 100.0 * sum(row_values[:expanded_start]) / total
            end_cumulative = 100.0 * sum(row_values[:expanded_end]) / total
            debug_print(
                f"{candidate_log}Chosen {chosen_row}."
            )
            debug_print(
                f"Cumulative range {start_cumulative:.2f}-{end_cumulative:.2f}% "
                f"(pixels {expanded_start}-{expanded_end}), "
                f"contains {end_cumulative - start_cumulative:.2f}% of pixels"
            )
        bands.append((expanded_start, expanded_end))
        debug_print(
            f"Drawing bar for {percent}% expansion with "
            f"range={expanded_start}-{expanded_end}"
        )
    return bands


def estimate_regular_character_band(
    image: Image.Image,
    top_fraction: float = CHARACTER_BAND_TOP_FRACTION,
    minimum_density: float = 0.20,
) -> tuple[int, int] | None:
    """Estimate the regular-character row band from an RGBA alpha histogram.

    The search is limited to the top `top_fraction` of the visible signature bounds so
    long descenders do not dominate the estimate. The densest contiguous row run above
    `minimum_density` of the peak is returned in full-image coordinates.
    """
    histogram = alpha_row_histogram(image)
    if histogram is None:
        debug_print("estimate band: no non-transparent pixels")
        return None
    bbox, row_values = histogram
    left, top, right, bottom = bbox
    search_count = max(1, min(len(row_values), round(len(row_values) * top_fraction)))
    values = row_values[:search_count]
    peak = max(values, default=0)
    debug_print(
        f"estimate band: image={image.size} bbox={bbox} "
        f"visible_height={bottom - top} top_fraction={top_fraction} "
        f"search_rows={search_count} peak_alpha_sum={peak}"
    )
    total_alpha = sum(row_values)
    cumulative_alpha = 0
    previous_cumulative_percent = 0.0
    for row_index, row_value in enumerate(row_values):
        cumulative_alpha += row_value
        cumulative_percent = (
            100.0 * cumulative_alpha / total_alpha if total_alpha else 0.0
        )
        incremental_percent = cumulative_percent - previous_cumulative_percent
        # Debug-only histogram bar: one "*" per 0.1% of cumulative alpha mass.
        star_count = max(0, round(incremental_percent / 0.1))
        stars = "*" * star_count
        debug_print(
            f"histogram row={row_index:4d} alpha_sum={row_value:10d} "
            f"cumulative={cumulative_percent:7.2f}% "
            f"incremental={incremental_percent:6.2f}% {stars}"
        )
        previous_cumulative_percent = cumulative_percent
    if peak <= 0:
        debug_print("estimate band: zero peak")
        return None
    threshold = peak * minimum_density
    runs: list[tuple[int, int, float]] = []
    run_start: int | None = None
    run_score = 0.0
    for index, value in enumerate(values):
        if value >= threshold:
            if run_start is None:
                run_start = index
                run_score = 0.0
            run_score += value
        elif run_start is not None:
            runs.append((run_start, index, run_score))
            run_start = None
    if run_start is not None:
        runs.append((run_start, len(values), run_score))
    if not runs:
        debug_print(
            f"estimate band: no runs threshold={threshold:.2f} minimum_density={minimum_density}"
        )
        return None
    band_start, band_end, _score = max(runs, key=lambda run: run[2])
    result = top + band_start, top + band_end
    debug_print(
        f"estimate band: threshold={threshold:.2f} runs={runs} selected={result} "
        f"height={result[1] - result[0]}"
    )
    return result


def calculate_character_scaling_factor(
    character_height_px: int,
    target_pt: float = CHARACTER_TARGET_PT,
    dpi: int = DPI,
) -> float:
    """Calculate the factor that makes a character band equal `target_pt`."""
    if character_height_px <= 0:
        debug_print("scaling factor: invalid character height, using 1.0")
        return 1.0
    target_height_px = target_pt * dpi / 72.0
    factor = target_height_px / character_height_px
    debug_print(
        f"scaling factor: character_height_px={character_height_px} dpi={dpi} "
        f"target_pt={target_pt} target_height_px={target_height_px:.4f} factor={factor:.6f}"
    )
    return factor


def resize_by_factor(image: Image.Image, factor: float) -> Image.Image:
    """Resize an image by `factor`, preserving aspect ratio and alpha."""
    if factor <= 0 or image.width <= 0 or image.height <= 0:
        return image
    size = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
    return image.resize(size, Image.Resampling.LANCZOS)


def height_px_to_pt(height_px: int, dpi: int = DPI) -> float:
    """Convert a pixel height (at the given DPI) to PDF points (1/72 inch)."""
    return height_px * 72.0 / dpi


def resize_to_height_pt(image: Image.Image, target_height_pt: float, dpi: int = DPI) -> Image.Image:
    """Rescale `image` (aspect ratio locked) so its height equals `target_height_pt`."""
    if image.height <= 0:
        return image
    target_height_px = max(1, round(target_height_pt * dpi / 72.0))
    if target_height_px == image.height:
        return image
    scale = target_height_px / image.height
    target_width_px = max(1, round(image.width * scale))
    return image.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)


def fit_to_recommended_range(
    image: Image.Image,
    dpi: int = DPI,
    min_pt: float = RECOMMENDED_MIN_PT,
    max_pt: float = RECOMMENDED_MAX_PT,
) -> Image.Image:
    """Scale `image` to the nearest bound of [min_pt, max_pt] if it's currently outside it."""
    current_pt = height_px_to_pt(image.height, dpi)
    if current_pt < min_pt:
        return resize_to_height_pt(image, min_pt, dpi)
    if current_pt > max_pt:
        return resize_to_height_pt(image, max_pt, dpi)
    return image
