"""The seed of an annotation survives every copy of it, also while the hand-drawn style is off,
so turning the style on later gives the look the annotation would have had (spec §7.10)."""

import pytest

from signer.objects import HAND_DRAWN_TYPES, AnnotationType, ProjectFile, VectorAnnotation


@pytest.mark.parametrize("ann_type", sorted(HAND_DRAWN_TYPES, key=lambda t: t.value))
def test_seed_survives_a_copy_while_the_style_is_off(ann_type):
    original = VectorAnnotation(ann_type, 10, 20, hand_drawn=False, hand_drawn_seed=1234)

    from_dict = VectorAnnotation.from_dict(original.to_dict())
    project = ProjectFile.from_annotations(document_path="doc.pdf", annotations=[original])
    from_project = ProjectFile.load_annotations(project)[0]

    assert from_dict.hand_drawn_seed == 1234
    assert from_project.hand_drawn_seed == 1234
    assert from_dict.hand_drawn is False and from_project.hand_drawn is False


def test_annotations_that_cannot_be_hand_drawn_store_no_seed():
    text = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="x")
    assert "hand_drawn_seed" not in text.to_dict()
