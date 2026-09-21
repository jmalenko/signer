"""Pure image-processing helpers for the "Prepare Signature" tool.

These functions have no Qt dependency so they can be unit tested directly on small
synthetic images. See FUNCTIONAL_SPECIFICATION.md §17 for the behavior they implement.
"""

from __future__ import annotations

import colorsys

from PIL import Image, ImageChops

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

    existing_alpha = rgba.split()[3]
    # Take the more-transparent (lower) alpha at each pixel, so pre-existing transparency
    # is never made more opaque by the luminance-based computation.
    combined_alpha = ImageChops.darker(computed_alpha, existing_alpha)

    result = rgba.copy()
    result.putalpha(combined_alpha)
    return result


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
    out = Image.new("RGBA", rgba.size)
    dst = out.load()
    for y in range(height):
        for x in range(width):
            r, g, b, existing_alpha = src[x, y]
            hue, saturation, _value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if saturation < min_saturation:
                alpha = 0
            else:
                hue_distance = abs(hue - target_h)
                if hue_distance > 0.5:
                    hue_distance = 1.0 - hue_distance
                hue_distance_deg = hue_distance * 360.0
                if hue_distance_deg <= lo:
                    alpha = 255
                elif hue_distance_deg >= hi:
                    alpha = 0
                else:
                    alpha = round(255 * (hi - hue_distance_deg) / span)
            dst[x, y] = (r, g, b, min(alpha, existing_alpha))
    return out


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
