"""Deterministic hand-drawn ("wobbly") stroke geometry.

How wobbly a stroke is, is set by the constants below (see DESIGN.md, "Wobbliness"): the
amplitude constants say how far a stroke may leave its ideal path, the knot spacings say how
often it changes direction, and BOW_SHARE says how much of the deviation is one smooth bend
rather than jitter. `deviation_amplitude_pt()` combines the amplitude constants.

Every function is a pure function of its arguments: the same seed, geometry and `unit`
always produce the same path. Lengths and deviations are computed in PDF points and
converted to viewport pixels with `unit` (pixels per point), so the shape looks identical at
every zoom level and in print/export, where only `unit` differs.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath

# --- Wobbliness: how often a stroke changes direction -------------------------------------
# Distance between neighbouring spline knots along a stroke (smaller = busier wobble).
KNOT_SPACING_PT = 12.0
ELLIPSE_KNOT_SPACING_PT = 14.0
MIN_ELLIPSE_KNOTS = 8

# --- Wobbliness: how far a stroke may leave its ideal path ---------------------------------
# deviation = AMPLITUDE_PER_LENGTH * length + AMPLITUDE_PER_LINE_WIDTH * line width,
# then capped (see MAX_AMPLITUDE_*); all in points.
AMPLITUDE_PER_LENGTH = 0.012
AMPLITUDE_PER_LINE_WIDTH = 0.4
MAX_AMPLITUDE_PER_LENGTH = 0.04
# Rectangle/ellipse deviation relative to the shorter side/radius, so thin shapes stay thin.
MAX_AMPLITUDE_PER_SHORT_SIDE = 0.06

# Share of the deviation that is a single gentle bow rather than independent knot jitter.
BOW_SHARE = 0.6

# Ellipse only: the outline also gets a slow sine-shaped irregularity ("egg" shape) that makes up
# a random share of each knot's deviation; the rest is jitter. Harmonic = lumps per revolution.
ELLIPSE_HARMONICS = (1, 2, 3)
ELLIPSE_HARMONIC_SHARE_RANGE = (0.25, 0.5)


def stroke_random(seed: int, stroke_index: int) -> random.Random:
    """Return the random source of one stroke; separate strokes get independent noise."""
    return random.Random((int(seed) & 0x7FFFFFFF) * 1_000_003 + stroke_index)


def deviation_amplitude_pt(length_pt: float, line_width_pt: float, cap_pt: float | None = None) -> float:
    """Largest distance (pt) a knot of a stroke of `length_pt` may leave its ideal path."""
    amplitude = AMPLITUDE_PER_LENGTH * length_pt + AMPLITUDE_PER_LINE_WIDTH * line_width_pt
    amplitude = min(amplitude, MAX_AMPLITUDE_PER_LENGTH * length_pt)
    if cap_pt is not None:
        amplitude = min(amplitude, cap_pt)
    return max(0.0, amplitude)


def _lerp(a: QPointF, b: QPointF, t: float) -> QPointF:
    return QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)


def wobbly_knots(
    start: QPointF,
    end: QPointF,
    rng: random.Random,
    unit: float,
    amplitude_pt: float,
) -> list[QPointF]:
    """Knots from `start` to `end` (both exact) displaced sideways by bow plus jitter."""
    dx, dy = end.x() - start.x(), end.y() - start.y()
    length_px = math.hypot(dx, dy)
    if length_px < 1e-9 or unit <= 0.0:
        return [QPointF(start), QPointF(end)]
    count = max(2, round(length_px / unit / KNOT_SPACING_PT))
    normal = QPointF(-dy / length_px, dx / length_px)
    amplitude_px = amplitude_pt * unit
    bow = rng.uniform(-1.0, 1.0) * BOW_SHARE * amplitude_px
    jitter_scale = (1.0 - BOW_SHARE) * amplitude_px
    knots = [QPointF(start)]
    for index in range(1, count):
        t = index / count
        offset = bow * math.sin(math.pi * t) + rng.uniform(-1.0, 1.0) * jitter_scale
        base = _lerp(start, end, t)
        knots.append(QPointF(base.x() + normal.x() * offset, base.y() + normal.y() * offset))
    knots.append(QPointF(end))
    return knots


def _append_open_spline(path: QPainterPath, knots: Sequence[QPointF]) -> None:
    """Append a Catmull-Rom spline through `knots`; the path must already be at knots[0]."""
    last = len(knots) - 1
    for i in range(last):
        p0 = knots[max(i - 1, 0)]
        p1, p2 = knots[i], knots[i + 1]
        p3 = knots[min(i + 2, last)]
        path.cubicTo(
            QPointF(p1.x() + (p2.x() - p0.x()) / 6.0, p1.y() + (p2.y() - p0.y()) / 6.0),
            QPointF(p2.x() - (p3.x() - p1.x()) / 6.0, p2.y() - (p3.y() - p1.y()) / 6.0),
            p2,
        )


def add_wobbly_polyline(
    path: QPainterPath,
    points: Sequence[QPointF],
    seed: int,
    first_stroke_index: int,
    unit: float,
    line_width_pt: float,
    closed: bool = False,
    cap_pt: float | None = None,
) -> None:
    """Add a new subpath that follows `points` with each segment drawn as its own wobbly line.

    Segment endpoints are exact, so neighbouring segments meet at the ideal vertices.
    """
    corners = list(points) + ([points[0]] if closed else [])
    path.moveTo(corners[0])
    for index in range(len(corners) - 1):
        start, end = corners[index], corners[index + 1]
        length_pt = math.hypot(end.x() - start.x(), end.y() - start.y()) / unit if unit > 0 else 0.0
        amplitude = deviation_amplitude_pt(length_pt, line_width_pt, cap_pt)
        knots = wobbly_knots(start, end, stroke_random(seed, first_stroke_index + index), unit, amplitude)
        _append_open_spline(path, knots)
    if closed:
        path.closeSubpath()


def wobbly_rectangle_path(
    rect: QRectF,
    seed: int,
    unit: float,
    line_width_pt: float,
) -> QPainterPath:
    """Rectangle whose four sides are separate wobbly lines meeting at the corners of `rect`."""
    cap = MAX_AMPLITUDE_PER_SHORT_SIDE * min(rect.width(), rect.height()) / unit if unit > 0 else 0.0
    corners = [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]
    path = QPainterPath()
    add_wobbly_polyline(path, corners, seed, 0, unit, line_width_pt, closed=True, cap_pt=cap)
    return path


def ellipse_deviation_pt(rx_px: float, ry_px: float, unit: float, line_width_pt: float) -> float:
    """Largest radial deviation of a wobbly ellipse knot, in points."""
    if unit <= 0.0:
        return 0.0
    rx_pt, ry_pt = rx_px / unit, ry_px / unit
    cap = MAX_AMPLITUDE_PER_SHORT_SIDE * min(rx_pt, ry_pt) * 2.0
    perimeter_pt = _ellipse_perimeter(rx_pt, ry_pt)
    return deviation_amplitude_pt(perimeter_pt / 4.0, line_width_pt, cap)


def _ellipse_perimeter(rx: float, ry: float) -> float:
    """Ramanujan's approximation."""
    h = ((rx - ry) ** 2) / ((rx + ry) ** 2) if rx + ry > 0 else 0.0
    return math.pi * (rx + ry) * (1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h)))


def wobbly_ellipse_path(
    rect: QRectF,
    seed: int,
    unit: float,
    line_width_pt: float,
    amplitude_pt: float | None = None,
) -> QPainterPath:
    """One closed periodic spline around `rect`; it has no start, end, gap or overlap.

    The outline is split into knots, each pushed along the outward normal by noise, and
    the knots are joined by a closed Catmull-Rom spline whose neighbours wrap around, so
    the curve is smooth where the knot list begins and ends.
    """
    center = rect.center()
    rx, ry = rect.width() / 2.0, rect.height() / 2.0
    if unit <= 0.0 or rx <= 0.0 or ry <= 0.0:
        path = QPainterPath()
        path.addEllipse(rect)
        return path
    if amplitude_pt is None:
        amplitude_pt = ellipse_deviation_pt(rx, ry, unit, line_width_pt)
    amplitude_px = amplitude_pt * unit
    count = max(MIN_ELLIPSE_KNOTS, round(_ellipse_perimeter(rx / unit, ry / unit) / ELLIPSE_KNOT_SPACING_PT))

    rng = stroke_random(seed, 0)
    phase = rng.uniform(0.0, 2.0 * math.pi)
    harmonic = rng.choice(ELLIPSE_HARMONICS)
    harmonic_share = rng.uniform(*ELLIPSE_HARMONIC_SHARE_RANGE)
    start_angle = rng.uniform(0.0, 2.0 * math.pi / count)

    knots: list[QPointF] = []
    for index in range(count):
        angle = start_angle + 2.0 * math.pi * index / count
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        nx, ny = cos_a / rx, sin_a / ry
        norm = math.hypot(nx, ny)
        nx, ny = nx / norm, ny / norm
        noise = harmonic_share * math.sin(harmonic * angle + phase) + (1.0 - harmonic_share) * rng.uniform(-1.0, 1.0)
        offset = noise * amplitude_px
        knots.append(QPointF(center.x() + rx * cos_a + nx * offset, center.y() + ry * sin_a + ny * offset))

    path = QPainterPath()
    path.moveTo(knots[0])
    for i in range(count):
        p0, p1 = knots[i - 1], knots[i]
        p2, p3 = knots[(i + 1) % count], knots[(i + 2) % count]
        path.cubicTo(
            QPointF(p1.x() + (p2.x() - p0.x()) / 6.0, p1.y() + (p2.y() - p0.y()) / 6.0),
            QPointF(p2.x() - (p3.x() - p1.x()) / 6.0, p2.y() - (p3.y() - p1.y()) / 6.0),
            p2,
        )
    path.closeSubpath()
    return path
