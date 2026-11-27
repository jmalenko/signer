"""Tests that mark strokes reach their annotation bounding-box edges."""

import pytest

from signer.objects import AnnotationType, VectorAnnotation


@pytest.mark.parametrize(
    "ann_type",
    [AnnotationType.CHECKMARK, AnnotationType.CROSSMARK],
)
@pytest.mark.parametrize("hand_drawn", [False, True])
def test_mark_strokes_reach_bounding_box_edges(ann_type, hand_drawn):
    annotation = VectorAnnotation(
        ann_type,
        0,
        0,
        hand_drawn=hand_drawn,
        hand_drawn_seed=17,
    )
    alpha = annotation.render_to_pil().split()[3]

    assert alpha.getbbox() == (0, 0, alpha.width, alpha.height)
