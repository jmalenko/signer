"""Image comparison utilities for pixel-perfect testing."""

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageChops, ImageDraw


def compare_images(
    actual_path: str | Path,
    expected_path: str | Path,
    tolerance: int = 0,
    diff_output_path: Optional[str | Path] = None,
) -> Tuple[bool, float, Optional[Image.Image]]:
    """
    Compare two images pixel by pixel.
    
    Args:
        actual_path: Path to the actual (generated) image
        expected_path: Path to the expected (reference) image
        tolerance: Maximum allowed difference per channel (0-255). Default 0 = pixel-perfect.
        diff_output_path: Optional path to save diff image on mismatch
        
    Returns:
        Tuple of (images_match, mismatch_percentage, diff_image)
    """
    actual = Image.open(actual_path).convert("RGBA")
    expected = Image.open(expected_path).convert("RGBA")
    
    # Check dimensions
    if actual.size != expected.size:
        if diff_output_path:
            diff_img = _create_size_diff_image(actual, expected)
            diff_img.save(diff_output_path)
        return False, 100.0, None
    
    # Calculate difference
    diff = ImageChops.difference(actual, expected)
    
    # Check if images are identical (within tolerance)
    if tolerance == 0:
        # Pixel-perfect comparison
        if diff.getbbox() is None:
            return True, 0.0, None
    else:
        # Tolerance-based comparison
        diff_pixels = 0
        total_pixels = actual.width * actual.height
        for pixel in diff.getdata():
            # Check if any channel exceeds tolerance
            if any(c > tolerance for c in pixel[:3]):  # Ignore alpha for tolerance
                diff_pixels += 1
        
        mismatch_pct = (diff_pixels / total_pixels) * 100
        if mismatch_pct == 0:
            return True, 0.0, None
    
    # Create diff image for visualization
    diff_img = _create_diff_image(actual, expected, diff)
    
    if diff_output_path:
        diff_img.save(diff_output_path)
    
    # Calculate mismatch percentage
    diff_bbox = diff.getbbox()
    if diff_bbox:
        diff_area = (diff_bbox[2] - diff_bbox[0]) * (diff_bbox[3] - diff_bbox[1])
        total_area = actual.width * actual.height
        mismatch_pct = (diff_area / total_area) * 100
    else:
        mismatch_pct = 0.0
    
    return False, mismatch_pct, diff_img


def _create_diff_image(actual: Image.Image, expected: Image.Image, diff: Image.Image) -> Image.Image:
    """Create a visualization of the differences between two images."""
    # Create a side-by-side comparison with diff highlighted
    width = actual.width * 3 + 20
    height = max(actual.height, expected.height) + 40
    
    result = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    
    # Paste actual
    result.paste(actual, (0, 40))
    # Paste expected
    result.paste(expected, (actual.width + 10, 40))
    # Paste diff (highlighted in red)
    diff_highlighted = _highlight_diff(diff)
    result.paste(diff_highlighted, (actual.width * 2 + 20, 40))
    
    # Add labels
    draw = ImageDraw.Draw(result)
    draw.text((0, 10), "Actual", fill=(0, 0, 0, 255))
    draw.text((actual.width + 10, 10), "Expected", fill=(0, 0, 0, 255))
    draw.text((actual.width * 2 + 20, 10), "Difference", fill=(0, 0, 0, 255))
    
    return result


def _highlight_diff(diff: Image.Image) -> Image.Image:
    """Highlight differences in red."""
    highlighted = Image.new("RGBA", diff.size, (0, 0, 0, 0))
    pixels = diff.load()
    highlight_pixels = highlighted.load()
    
    for y in range(diff.height):
        for x in range(diff.width):
            r, g, b, a = pixels[x, y]
            if r > 0 or g > 0 or b > 0:
                # Difference found - highlight in red with intensity based on difference
                intensity = max(r, g, b)
                highlight_pixels[x, y] = (255, 0, 0, min(255, intensity * 2))
            else:
                highlight_pixels[x, y] = (0, 0, 0, 0)
    
    return highlighted


def _create_size_diff_image(actual: Image.Image, expected: Image.Image) -> Image.Image:
    """Create a diff image showing size mismatch."""
    width = max(actual.width, expected.width) * 2 + 10
    height = max(actual.height, expected.height) + 40
    
    result = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    result.paste(actual, (0, 40))
    result.paste(expected, (max(actual.width, expected.width) + 10, 40))
    
    draw = ImageDraw.Draw(result)
    draw.text((0, 10), f"Actual: {actual.size}", fill=(0, 0, 0, 255))
    draw.text((max(actual.width, expected.width) + 10, 10), f"Expected: {expected.size}", fill=(0, 0, 0, 255))
    draw.text((0, height - 25), "SIZE MISMATCH", fill=(255, 0, 0, 255))
    
    return result


def assert_images_equal(
    actual_path: str | Path,
    expected_path: str | Path,
    tolerance: int = 0,
    diff_output_path: Optional[str | Path] = None,
) -> None:
    """
    Assert that two images are equal (pixel-perfect by default).
    
    Raises:
        AssertionError: If images don't match, with details about the mismatch
    """
    match, mismatch_pct, diff_img = compare_images(
        actual_path, expected_path, tolerance, diff_output_path
    )
    
    if not match:
        msg = f"Images do not match. Mismatch: {mismatch_pct:.2f}%"
        if diff_output_path:
            msg += f"\nDiff image saved to: {diff_output_path}"
        raise AssertionError(msg)


def create_reference_image(
    source_path: str | Path,
    output_path: str | Path,
    annotations: list = None,
) -> None:
    """
    Helper to create a reference image by manually composing annotations.
    This is a utility for creating expected reference images.
    """
    from signer.compositor import composite_objects_to_jpg
    from signer.objects import CanvasObject
    from PIL import Image
    
    page_image = Image.open(source_path).convert("RGB")
    
    if annotations:
        composite_objects_to_jpg(page_image, annotations, output_path)
    else:
        page_image.save(output_path, format="JPEG", quality=95, optimize=True)