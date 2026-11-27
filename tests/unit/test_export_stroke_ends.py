"""Bug: export cut off the round caps of strokes that end on the edge of the annotation's box.

A Line's endpoints lie exactly on the edges of its box and its pen has round caps that stick out
half a pen width past each endpoint. Export rendered the annotation into an image of exactly the
box's size, so the caps were cut off flat and the line looked shorter than on screen.
"""

import pytest
from PIL import Image

from signer.compositor import _composite_objects
from signer.objects import AnnotationType, VectorAnnotation

BOX = 100.0  # x/y of the annotation on the page, in pixels
THICK_PT = 8.0


def vertical_line(line_width_pt: float = THICK_PT) -> VectorAnnotation:
    line = VectorAnnotation(AnnotationType.LINE, BOX, BOX, line_width_pt=line_width_pt)
    line._angle = 90.0  # both endpoints are on the top and bottom edges of the box
    return line


def composite(annotation: VectorAnnotation) -> Image.Image:
    page = Image.new("RGBA", (600, 600), (255, 255, 255, 0))
    _composite_objects(page, [annotation])
    return page


def ink_at(page: Image.Image, x: float, y: float) -> bool:
    return page.getpixel((round(x), round(y)))[3] > 0


def test_line_cap_is_exported_beyond_the_box_edge():
    """Expected: the round cap past the top endpoint is part of the export."""
    line = vertical_line()
    page = composite(line)
    center_x = BOX + line.scaled_width / 2.0
    assert ink_at(page, center_x, BOX - 2)
    assert ink_at(page, center_x, BOX + line.scaled_height + 1)


@pytest.mark.parametrize("ann_type", [AnnotationType.CHECKMARK, AnnotationType.CROSSMARK])
def test_thick_marks_are_not_cut_off(ann_type):
    """Their strokes end on the box edges, so the round caps of a thick mark reach past its box."""
    mark = VectorAnnotation(ann_type, BOX, BOX, line_width_pt=16.0)
    left, top, right, bottom = composite(mark).split()[3].getbbox()
    assert left < BOX and top < BOX
    assert right > BOX + mark.scaled_width and bottom > BOX + mark.scaled_height


class _FailingAnnotation(VectorAnnotation):
    def __init__(self, error: Exception) -> None:
        super().__init__(AnnotationType.LINE, BOX, BOX)
        self._error = error

    def draw_for_export(self, painter) -> None:
        raise self._error


def test_a_failing_vector_annotation_is_reported_as_an_export_error():
    page = Image.new("RGBA", (300, 300), (255, 255, 255, 0))
    with pytest.raises(RuntimeError, match="Could not render annotation for export"):
        _composite_objects(page, [VectorAnnotation(AnnotationType.LINE, 10, 10), _FailingAnnotation(ValueError("x"))])


def test_an_unexpected_error_does_not_leave_a_painter_running():
    """The error propagates, and the next export still works (no painter left on a freed layer)."""
    page = Image.new("RGBA", (300, 300), (255, 255, 255, 0))
    with pytest.raises(KeyError):
        _composite_objects(page, [_FailingAnnotation(KeyError("x"))])
    _composite_objects(page, [VectorAnnotation(AnnotationType.LINE, 10, 10)])
    assert page.split()[3].getbbox() is not None
