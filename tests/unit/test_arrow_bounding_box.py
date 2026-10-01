"""Tests for the arrow's visible-content bounding box."""

import math

import pytest

from signer.constants import DPI_SCALE
from signer.objects import (
    ARROW_HEAD_ANGLE_DEG,
    ARROW_HEAD_LENGTH_FACTOR,
    ARROW_SHAFT_LENGTH_FACTOR,
    AnnotationType,
    VectorAnnotation,
)


def test_arrow_boundary_is_minimal_rectangle_containing_stroked_arrow():
    arrow = VectorAnnotation(AnnotationType.ARROW, 0, 0)
    arrow.set_scaled_size(200, 200)

    boundary = arrow.boundary_points_viewport(0, 0, 200, 200, 0)

    pen_radius = arrow._line_width_pt * DPI_SCALE / 2.0
    shaft = 200 * ARROW_SHAFT_LENGTH_FACTOR
    half_head_height = (
        200
        * ARROW_HEAD_LENGTH_FACTOR
        * math.sin(math.radians(ARROW_HEAD_ANGLE_DEG))
    )
    assert [(point.x(), point.y()) for point in boundary] == pytest.approx([
        (100 - shaft - pen_radius, 100 - half_head_height - pen_radius),
        (100 + shaft + pen_radius, 100 - half_head_height - pen_radius),
        (100 + shaft + pen_radius, 100 + half_head_height + pen_radius),
        (100 - shaft - pen_radius, 100 + half_head_height + pen_radius),
    ])