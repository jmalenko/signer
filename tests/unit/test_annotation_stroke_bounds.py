"""Tests that mark strokes reach their annotation bounding-box edges."""

import pytest

from signer.objects import AnnotationType, VectorAnnotation
from tests.utils.test_helpers import export_to_page


@pytest.mark.parametrize(
    "ann_type",
    [AnnotationType.CHECKMARK, AnnotationType.CROSSMARK],
)
@pytest.mark.parametrize("hand_drawn", [False, True])
def test_mark_strokes_reach_bounding_box_edges(ann_type, hand_drawn):
    annotation = VectorAnnotation(
        ann_type,
        100,
        100,
        hand_drawn=hand_drawn,
        hand_drawn_seed=17,
    )
    left, top, right, bottom = export_to_page(annotation).split()[3].getbbox()

    # Round caps may extend past the box, but the strokes must reach all four edges.
    assert left <= 100 and top <= 100
    assert right >= 100 + annotation.scaled_width and bottom >= 100 + annotation.scaled_height
