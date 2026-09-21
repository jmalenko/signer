"""Image comparison utilities for pixel-perfect testing."""

from pathlib import Path

from PIL import Image, ImageChops


def compare_images(
    actual_path: str | Path,
    expected_path: str | Path,
    diff_output_path: str | Path | None = None,
) -> tuple[bool, Image.Image | None]:
    """
    Compare two images pixel by pixel (exact match required).
    
    Args:
        actual_path: Path to the actual (generated) image
        expected_path: Path to the expected (reference) image
        diff_output_path: Optional path to save diff image (always generated for visualization)
        
    Returns:
        Tuple of (images_match, diff_image)
    """
    actual = Image.open(actual_path).convert("RGB")
    expected = Image.open(expected_path).convert("RGB")
    
    # Check dimensions
    if actual.size != expected.size:
        diff_img = _create_diff_image(actual, expected)
        if diff_output_path:
            diff_img.save(diff_output_path)
        return False, diff_img
    
    # Calculate difference
    diff = ImageChops.difference(actual, expected)
    
    # Create diff image for visualization (always, regardless of match/mismatch)
    diff_img = _create_diff_image(actual, expected)
    
    if diff_output_path:
        diff_img.save(diff_output_path)
    
    # Pixel-perfect comparison (exact match required)
    if diff.getbbox() is None:
        return True, diff_img
    
    return False, diff_img


def _create_diff_image(actual: Image.Image, expected: Image.Image) -> Image.Image:
    """Create a pixel-level diff visualization for pixel-perfect comparison.
    
    Args:
        actual: Actual rendered image (RGB)
        expected: Expected reference image (RGB)
        
    Returns:
        Diff image with white pixels for matches, and color-coded differences:
        - Red (255, 0, 0): expected pixel is white and actual image is non-white
        - Violet (238, 130, 238): expected pixel is non-white and actual image is white
        - Orange (255, 165, 0): expected pixel is non-white and actual image is non-white
        - White (255, 255, 255): matching pixels
    """
    max_w = max(actual.width, expected.width)
    max_h = max(actual.height, expected.height)
    diff_img = Image.new("RGB", (max_w, max_h), (255, 255, 255))
    
    # Fast path if identical dimensions and exact match
    if actual.size == expected.size:
        diff = ImageChops.difference(actual.convert("RGB"), expected.convert("RGB"))
        if diff.getbbox() is None:
            return diff_img
    
    # Ensure images are RGB (they should be, but be defensive)
    actual_rgb = actual if actual.mode == "RGB" else actual.convert("RGB")
    expected_rgb = expected if expected.mode == "RGB" else expected.convert("RGB")
    
    # Load pixel data
    actual_pixels = actual_rgb.load()
    expected_pixels = expected_rgb.load()
    diff_pixels = diff_img.load()
    
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    VIOLET = (238, 130, 238)
    ORANGE = (255, 165, 0)
    
    # Compare pixel by pixel
    for y in range(max_h):
        for x in range(max_w):
            actual_pixel = actual_pixels[x, y] if (x < actual.width and y < actual.height) else WHITE
            expected_pixel = expected_pixels[x, y] if (x < expected.width and y < expected.height) else WHITE
            
            if actual_pixel != expected_pixel:
                if expected_pixel == WHITE:
                    diff_pixels[x, y] = RED
                elif actual_pixel == WHITE:
                    diff_pixels[x, y] = VIOLET
                else:
                    diff_pixels[x, y] = ORANGE
            else:
                diff_pixels[x, y] = WHITE
    
    return diff_img


def assert_images_equal(
    actual_path: str | Path,
    expected_path: str | Path,
    diff_output_path: str | Path | None = None,
) -> None:
    """
    Assert that two images are equal (pixel-perfect, exact match required).
    
    Raises:
        AssertionError: If images don't match, with details about the mismatch
    """
    match, diff_img = compare_images(
        actual_path, expected_path, diff_output_path
    )
    
    if not match:
        msg = "Images do not match."
        if diff_output_path:
            msg += f"\nDiff image saved to: {diff_output_path}"
        raise AssertionError(msg)


def create_reference_image(
    source_path: str | Path,
    output_path: str | Path,
    annotations: list | None = None,
) -> None:
    """
    Helper to create a reference image by manually composing annotations.
    This is a utility for creating expected reference images.
    """
    from PIL import Image

    from signer.compositor import composite_objects_to_jpg
    
    page_image = Image.open(source_path).convert("RGB")
    
    if annotations:
        composite_objects_to_jpg(page_image, annotations, output_path)
    else:
        page_image.save(output_path, format="JPEG", quality=95, optimize=True)


def assert_images_equal_with_results(
    actual_path: str | Path,
    expected_path: str | Path,
    test_name: str,
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
        save_results: Whether to save results even on pass
        
    Raises:
        AssertionError: If images don't match
    """
    import tempfile

    from . import test_results as tr
    
    actual_path = Path(actual_path)
    expected_path = Path(expected_path)
    
    # Create temp directory for diff file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        diff_path = tmpdir / "diff.png"
        
        # Compare images and always generate diff for visualization (pixel-perfect)
        match, _ = compare_images(
            actual_path, expected_path, diff_output_path=diff_path
        )
        
        # Organize results (always save diff if save_results=True)
        if not match or save_results:
            tr.organize_test_output(
                test_name,
                actual_image=actual_path if actual_path.exists() else None,
                expected_image=expected_path if expected_path.exists() else None,
                diff_image=diff_path if diff_path.exists() else None,
                match=match,
            )
        
        # Raise assertion error if mismatch
        if not match:
            results_dir = tr.get_test_results_dir()
            msg = (
                f"Images do not match.\n"
                f"Results saved to: {results_dir}/{test_name}/"
            )
            raise AssertionError(msg)