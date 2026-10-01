"""Tests for the Line annotation's minimum bounding box."""

import pytest
from PySide6.QtCore import QPointF

from signer.constants import DPI_SCALE
from signer.objects import (
    ARROW_HEAD_SPREAD_FACTOR,
    AnnotationType,
    VectorAnnotation,
)


@pytest.mark.parametrize(
    ("angle", "expected_width", "expected_height"),
    [
        (0.0, 200 + 1.5 * DPI_SCALE, None),
        (90.0, None, 200 + 1.5 * DPI_SCALE),
    ],
)
def test_line_boundary_contains_stroke_and_has_arrow_head_minimum_size(
    angle,
    expected_width,
    expected_height,
):
    line = VectorAnnotation(AnnotationType.LINE, 0, 0)
    line._angle = angle
    line.set_scaled_size(200, 200)

    boundary = line.boundary_points_viewport(0, 0, 200, 200, 0)
    left = min(point.x() for point in boundary)
    right = max(point.x() for point in boundary)
    top = min(point.y() for point in boundary)
    bottom = max(point.y() for point in boundary)
    minimum_size = 200 * ARROW_HEAD_SPREAD_FACTOR

    assert right - left == pytest.approx(expected_width or minimum_size)
    assert bottom - top == pytest.approx(expected_height or minimum_size)
    assert (left + right) / 2.0 == pytest.approx(100)
    assert (top + bottom) / 2.0 == pytest.approx(100)


def test_horizontal_line_hit_testing_uses_centered_minimum_boundary():
    line = VectorAnnotation(AnnotationType.LINE, 0, 0)
    line._angle = 0.0
    line.set_scaled_size(200, 200)
    half_minimum_size = 200 * ARROW_HEAD_SPREAD_FACTOR / 2.0

    assert line.contains_viewport_point(
        0, 0, 200, 200, QPointF(100, 100 + half_minimum_size - 0.1), 0
    )
    assert not line.contains_viewport_point(
        0, 0, 200, 200, QPointF(100, 100 + half_minimum_size + 0.1), 0
    )