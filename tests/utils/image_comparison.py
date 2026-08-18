"""Image comparison utilities for pixel-perfect testing."""

from pathlib import Path
from typing import Optional, Tuple
from shutil import copy2

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
        diff_output_path: Optional path to save diff image (always generated for visualization)
        
    Returns:
        Tuple of (images_match, mismatch_percentage, diff_image)
    """
    actual = Image.open(actual_path).convert("RGB")
    expected = Image.open(expected_path).convert("RGB")
    
    # Check dimensions
    if actual.size != expected.size:
        if diff_output_path:
            diff_img = _create_diff_image(actual, expected)
            diff_img.save(diff_output_path)
        return False, 100.0, None
    
    # Calculate difference
    diff = ImageChops.difference(actual, expected)
    
    # Create diff image for visualization (always, regardless of match/mismatch)
    diff_img = _create_diff_image(actual, expected)
    
    if diff_output_path:
        diff_img.save(diff_output_path)
    
    # Check if images are identical (within tolerance)
    if tolerance == 0:
        # Pixel-perfect comparison
        if diff.getbbox() is None:
            return True, 0.0, diff_img
    else:
        # Tolerance-based comparison
        diff_pixels = 0
        total_pixels = actual.width * actual.height
        for pixel in diff.getdata():
            # Check if any channel exceeds tolerance
            if any(c > tolerance for c in pixel[:3]):  # For RGB, only 3 channels
                diff_pixels += 1
        
        mismatch_pct = (diff_pixels / total_pixels) * 100
        if mismatch_pct == 0:
            return True, 0.0, diff_img
    
    # Calculate mismatch percentage
    diff_bbox = diff.getbbox()
    if diff_bbox:
        diff_area = (diff_bbox[2] - diff_bbox[0]) * (diff_bbox[3] - diff_bbox[1])
        total_area = actual.width * actual.height
        mismatch_pct = (diff_area / total_area) * 100
    else:
        mismatch_pct = 0.0
    
    return False, mismatch_pct, diff_img


def _create_diff_image(actual: Image.Image, expected: Image.Image) -> Image.Image:
    """Create a pixel-level diff visualization for pixel-perfect comparison.
    
    Args:
        actual: Actual rendered image (RGB)
        expected: Expected reference image (RGB)
        
    Returns:
        Diff image with white pixels for matches, red pixels for differences
    """
    # Create white background (same size as images)
    diff_img = Image.new("RGB", actual.size, (255, 255, 255))
    
    # Ensure images are RGB (they should be, but be defensive)
    actual_rgb = actual if actual.mode == "RGB" else actual.convert("RGB")
    expected_rgb = expected if expected.mode == "RGB" else expected.convert("RGB")
    
    # Load pixel data
    actual_pixels = actual_rgb.load()
    expected_pixels = expected_rgb.load()
    diff_pixels = diff_img.load()
    
    # Compare pixel by pixel
    for y in range(actual.height):
        for x in range(actual.width):
            actual_pixel = actual_pixels[x, y]
            expected_pixel = expected_pixels[x, y]
            
            # Mark RED where pixels differ, WHITE where they match
            if actual_pixel != expected_pixel:
                diff_pixels[x, y] = (255, 0, 0)  # RED for different pixels
    
    return diff_img


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


def assert_images_equal_with_results(
    actual_path: str | Path,
    expected_path: str | Path,
    test_name: str,
    tolerance: int = 0,
    save_results: bool = True,
) -> None:
    """
    Assert images are equal and automatically save comparison results.
    
    Saves to test-results/:
    - actual/ subdirectory: Contains the generated test images
    - diff.png: Pixel-level diff visualization (white=same, red=different)
    
    Args:
        actual_path: Path to the actual (generated) image
        expected_path: Path to the expected (reference) image
        test_name: Name for organizing results (stored in actual/ subdirectory)
        tolerance: Pixel difference tolerance (default 0 = pixel-perfect)
        save_results: Whether to save results even on pass
        
    Raises:
        AssertionError: If images don't match
    """
    from . import test_results as tr
    import tempfile
    
    actual_path = Path(actual_path)
    expected_path = Path(expected_path)
    
    # Create temp directory for diff file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        diff_path = tmpdir / "diff.png"
        
        # Compare images and always generate diff for visualization
        match, mismatch_pct, _ = compare_images(
            actual_path, expected_path, tolerance, diff_output_path=diff_path
        )
        
        # Organize results (always save diff if save_results=True)
        if not match or save_results:
            tr.organize_test_output(
                test_name,
                actual_image=actual_path if actual_path.exists() else None,
                expected_image=expected_path if expected_path.exists() else None,
                diff_image=diff_path if diff_path.exists() else None,
                match=match,
                mismatch_pct=mismatch_pct,
            )
        
        # Raise assertion error if mismatch
        if not match:
            results_dir = tr.get_test_results_dir()
            msg = (
                f"Images do not match (mismatch: {mismatch_pct:.2f}%)\n"
                f"Results saved to: {results_dir}/{test_name}/"
            )
            raise AssertionError(msg)