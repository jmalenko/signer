"""Feature test: every stroke-based annotation type in the hand-drawn style.

The fixture places six differently sized, rotated, colored and weighted shapes of each type on
the third page of the example document, each with an explicit seed so the wobble is
reproducible. The reference image is meant to be judged by eye as well as compared pixel by pixel.
"""

import json
from collections import Counter

from PySide6.QtWidgets import QApplication

from tests.conftest import FIXTURES_DIR
from tests.recording.action_player import play_actions_from_file
from tests.utils.image_comparison import assert_images_equal_with_results

ACTIONS_FILE = FIXTURES_DIR / "hand_drawn_annotations.json"
REFERENCE_PAGE = FIXTURES_DIR / "hand_drawn_annotations" / "document-signed-p3.png"
STROKE_TYPES = {"checkmark", "crossmark", "line", "arrow", "rectangle", "ellipse"}
SHAPES_PER_TYPE = 6


def load_added_annotations() -> list[dict]:
    with open(ACTIONS_FILE) as f:
        actions = json.load(f)["actions"]
    return [action for action in actions if action.get("type") == "add_annotation"]


class TestHandDrawnAnnotations:
    def test_pixel_perfect(self, main_window, temp_dir):
        output_base = temp_dir / "document-signed.png"

        play_actions_from_file(main_window, ACTIONS_FILE, output_path=output_base)
        QApplication.processEvents()

        output_page = temp_dir / "document-signed-p3.png"
        assert output_page.exists(), f"Output page not found: {output_page}"
        assert REFERENCE_PAGE.exists(), f"Reference page not found: {REFERENCE_PAGE}"
        assert_images_equal_with_results(
            output_page, REFERENCE_PAGE, test_name="hand_drawn_annotations", save_results=True,
        )

    def test_shows_several_hand_drawn_shapes_of_every_stroke_type(self):
        added = load_added_annotations()
        assert all(action["hand_drawn"] is True for action in added)
        counts = Counter(action["annotation_type"] for action in added)
        assert set(counts) == STROKE_TYPES
        assert all(count >= SHAPES_PER_TYPE for count in counts.values()), counts

    def test_every_shape_has_its_own_seed(self):
        seeds = [action["hand_drawn_seed"] for action in load_added_annotations()]
        assert len(seeds) == len(set(seeds))

    def test_playback_creates_hand_drawn_annotations(self, main_window, temp_dir):
        play_actions_from_file(main_window, ACTIONS_FILE, output_path=temp_dir / "document-signed.png")
        annotations = main_window.canvas.current_page_objects()
        assert len(annotations) == len(load_added_annotations())
        assert all(annotation.hand_drawn for annotation in annotations)
