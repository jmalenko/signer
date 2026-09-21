"""Performance regression tests for overlapping annotation hit testing."""

import math
import time

import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import QPointF

from signer.objects import SignatureObject

MAX_HIT_TEST_SECONDS = 0.1


def _overlapping_signatures(canvas) -> QPointF:
    canvas.set_pages([Image.new("RGB", (1200, 1600), "white")])
    image = Image.new("RGBA", (854, 417), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.line((40, 200, 810, 210), fill=(0, 0, 0, 255), width=12)

    signatures = []
    for offset in (0, 10):
        signature = SignatureObject(image, "signature.png", offset, offset)
        canvas.add_object(signature)
        signatures.append(signature)

    overlap = canvas._object_view_rect(signatures[0]).intersected(
        canvas._object_view_rect(signatures[1])
    )
    return overlap.center()


def _measure_hit_test(canvas, point: QPointF) -> tuple[float, object]:
    started = time.perf_counter()
    selected = canvas._hit_test_object_at_point(point)
    return time.perf_counter() - started, selected


def _brute_force_distance(image, vx, vy, vw, vh, point):
    nearest = float("inf")
    for y in range(image.height):
        for x in range(image.width):
            if image.getpixel((x, y))[3] > 0:
                px = vx + (x / image.width) * vw
                py = vy + (y / image.height) * vh
                distance = math.hypot(point.x() - px, point.y() - py)
                nearest = min(nearest, distance)
    return nearest


def test_overlapping_annotation_hit_test_meets_interaction_budget(canvas):
    point = _overlapping_signatures(canvas)

    elapsed, selected = _measure_hit_test(canvas, point)

    assert selected is not None
    assert elapsed < MAX_HIT_TEST_SECONDS


def test_alpha_run_distance_matches_brute_force_distance():
    image = Image.new("RGBA", (5, 4), (0, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 0, 255))
    image.putpixel((4, 0), (0, 0, 0, 255))
    image.putpixel((1, 2), (0, 0, 0, 128))
    image.putpixel((2, 2), (0, 0, 0, 255))
    signature = SignatureObject(image, "signature.png", 0, 0)
    viewport = (10.0, 20.0, 15.0, 8.0)

    for point in (QPointF(10, 20), QPointF(20, 23), QPointF(24, 27)):
        expected = _brute_force_distance(image, *viewport, point)
        actual = signature.distance_to_visible_pixel(*viewport, point)
        assert actual == pytest.approx(expected)
