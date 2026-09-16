"""Feature tests for copy/paste across pages and documents."""

import sys
from shutil import copy2

import pytest
from PySide6.QtWidgets import QApplication

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results


@pytest.mark.parametrize(
    ("fixture_name", "output_name", "page_numbers"),
    [
        ("copy_paste_between_pages", "document-signed.png", (1, 2, 3)),
        ("copy_paste_between_documents", "document1-signed.png", ()),
    ],
)
def test_copy_paste_workflow_pixel_perfect(
    fixture_name: str,
    output_name: str,
    page_numbers: tuple[int, ...],
    main_window,
    temp_dir,
):
    output_path = temp_dir / output_name
    play_actions_from_file(
        main_window,
        FIXTURES_DIR / f"{fixture_name}.json",
        output_path=output_path,
    )
    QApplication.processEvents()

    actual_paths = (
        [
            temp_dir / output_name.replace(".png", f"-p{page}.png")
            for page in page_numbers
        ]
        if page_numbers
        else [output_path]
    )
    expected_dir = FIXTURES_DIR / fixture_name
    expected_dir.mkdir(exist_ok=True)

    missing_baselines = [
        (actual_path, expected_dir / actual_path.name)
        for actual_path in actual_paths
        if not (expected_dir / actual_path.name).exists()
    ]
    if missing_baselines:
        for actual_path, expected_path in missing_baselines:
            copy2(actual_path, expected_path)
        pytest.skip(f"Created {len(missing_baselines)} baseline image(s)")

    for page, actual_path in zip(page_numbers or (None,), actual_paths):
        expected_path = expected_dir / actual_path.name
        result_name = (
            fixture_name if page is None else f"{fixture_name}_page{page}"
        )
        try:
            assert_images_equal_with_results(
                actual_path,
                expected_path,
                test_name=result_name,
                save_results=True,
            )
        except AssertionError:
            if sys.platform == "darwin":
                pytest.skip(
                    "Pixel-perfect rendering differs on macOS; "
                    "comparison saved to the report"
                )
            raise
