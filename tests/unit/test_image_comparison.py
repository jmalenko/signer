"""Unit tests for image comparison diff visualization and test report generation."""

from PIL import Image

from tests.utils.image_comparison import _create_diff_image, compare_images
from tests.utils.test_results import _generate_html_report


def test_diff_image_expected_white_actual_nonwhite():
    """If expected pixel is white and actual image is non-white, diff pixel is RED."""
    expected = Image.new("RGB", (10, 10), (255, 255, 255))
    actual = Image.new("RGB", (10, 10), (255, 255, 255))
    actual.putpixel((5, 5), (0, 0, 0))  # Black pixel on white

    diff = _create_diff_image(actual, expected)
    assert diff.getpixel((5, 5)) == (255, 0, 0)  # RED
    assert diff.getpixel((0, 0)) == (255, 255, 255)  # WHITE match


def test_diff_image_expected_nonwhite_actual_white():
    """If expected pixel is non-white and actual image is white, diff pixel is VIOLET."""
    expected = Image.new("RGB", (10, 10), (255, 255, 255))
    expected.putpixel((5, 5), (0, 0, 0))  # Black pixel in expected
    actual = Image.new("RGB", (10, 10), (255, 255, 255))

    diff = _create_diff_image(actual, expected)
    assert diff.getpixel((5, 5)) == (238, 130, 238)  # VIOLET
    assert diff.getpixel((0, 0)) == (255, 255, 255)  # WHITE match


def test_diff_image_expected_nonwhite_actual_nonwhite_differ():
    """If expected pixel is non-white and actual is non-white (differing), diff pixel is ORANGE."""
    expected = Image.new("RGB", (10, 10), (255, 255, 255))
    expected.putpixel((5, 5), (10, 20, 30))
    actual = Image.new("RGB", (10, 10), (255, 255, 255))
    actual.putpixel((5, 5), (40, 50, 60))

    diff = _create_diff_image(actual, expected)
    assert diff.getpixel((5, 5)) == (255, 165, 0)  # ORANGE
    assert diff.getpixel((0, 0)) == (255, 255, 255)  # WHITE match


def test_diff_image_matching_pixels_are_white():
    """Matching non-white pixels remain WHITE in diff image."""
    expected = Image.new("RGB", (10, 10), (50, 50, 50))
    actual = Image.new("RGB", (10, 10), (50, 50, 50))

    diff = _create_diff_image(actual, expected)
    # All pixels match, so all pixels must be WHITE (255, 255, 255)
    for y in range(10):
        for x in range(10):
            assert diff.getpixel((x, y)) == (255, 255, 255)


def test_diff_image_different_sizes():
    """Images of different sizes are compared gracefully with expanded canvas."""
    expected = Image.new("RGB", (5, 5), (255, 255, 255))
    actual = Image.new("RGB", (10, 10), (255, 255, 255))
    actual.putpixel((8, 8), (0, 0, 0))

    diff = _create_diff_image(actual, expected)
    assert diff.size == (10, 10)
    assert diff.getpixel((8, 8)) == (255, 0, 0)  # RED (expected is out of bounds / white)


def test_compare_images_outputs_color_coded_diff(tmp_path):
    """compare_images saves the color-coded diff image to diff_output_path."""
    exp_path = tmp_path / "expected.png"
    act_path = tmp_path / "actual.png"
    diff_path = tmp_path / "diff.png"

    expected = Image.new("RGB", (10, 10), (255, 255, 255))
    expected.putpixel((2, 2), (0, 0, 0))  # missing in actual -> violet
    expected.save(exp_path)

    actual = Image.new("RGB", (10, 10), (255, 255, 255))
    actual.putpixel((4, 4), (0, 0, 0))  # extra in actual -> red
    actual.save(act_path)

    match, diff_img = compare_images(act_path, exp_path, diff_output_path=diff_path)
    assert match is False
    assert diff_path.exists()

    saved_diff = Image.open(diff_path).convert("RGB")
    assert saved_diff.getpixel((4, 4)) == (255, 0, 0)  # Red (extra in actual)
    assert saved_diff.getpixel((2, 2)) == (238, 130, 238)  # Violet (missing from actual)


def test_html_report_contains_color_legend_and_zoom_script(tmp_path):
    """Generated HTML report contains diff legend and mouse wheel zoom script."""
    results = [
        {
            "test_name": "sample_test",
            "match": False,
            "expected_base": "sample_test",
        }
    ]
    test_dir = tmp_path / "sample_test"
    test_dir.mkdir()
    exp_img = test_dir / "sample_test_expected.png"
    act_img = test_dir / "sample_test_actual.png"
    diff_img = test_dir / "sample_test_diff.png"
    Image.new("RGB", (10, 10), (255, 255, 255)).save(exp_img)
    Image.new("RGB", (10, 10), (255, 255, 255)).save(act_img)
    Image.new("RGB", (10, 10), (255, 255, 255)).save(diff_img)

    html = _generate_html_report(results, tmp_path)
    assert "<h4>Diff</h4>" in html
    assert "Diff Color Legend" in html
    assert "Red" in html
    assert "Violet" in html
    assert "Orange" in html
    assert "wheel" in html
    assert "scale" in html
    assert "imageModal" in html
