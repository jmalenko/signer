"""Hand-drawn style: stroke geometry, annotation model, serialization and rendering."""

import math

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath

from signer.hand_drawn import (
    add_wobbly_polyline,
    ellipse_deviation_pt,
    wobbly_ellipse_path,
    wobbly_rectangle_path,
)
from signer.objects import (
    HAND_DRAWN_TYPES,
    AnnotationType,
    ProjectFile,
    VectorAnnotation,
    canvas_object_from_dict,
)

UNIT = 300.0 / 72.0  # pixels per point at 300 DPI

STROKE_TYPES = [
    AnnotationType.CHECKMARK,
    AnnotationType.CROSSMARK,
    AnnotationType.LINE,
    AnnotationType.ARROW,
    AnnotationType.RECTANGLE,
    AnnotationType.ELLIPSE,
]


def elements(path: QPainterPath) -> list[tuple[float, float]]:
    return [(path.elementAt(i).x, path.elementAt(i).y) for i in range(path.elementCount())]


def scaled(points: list[tuple[float, float]], factor: float) -> list[tuple[float, float]]:
    return [(x * factor, y * factor) for x, y in points]


def assert_points_close(actual, expected, tolerance=1e-6):
    assert len(actual) == len(expected)
    for (ax, ay), (ex, ey) in zip(actual, expected):
        assert ax == pytest.approx(ex, abs=tolerance)
        assert ay == pytest.approx(ey, abs=tolerance)


def line_path(seed: int, unit: float = UNIT) -> QPainterPath:
    path = QPainterPath()
    add_wobbly_polyline(path, [QPointF(0, 0), QPointF(80 * unit, 0)], seed, 0, unit, 1.5)
    return path


class TestWobblyStrokes:
    def test_same_seed_gives_identical_path(self):
        assert elements(line_path(7)) == elements(line_path(7))

    def test_different_seeds_give_different_paths(self):
        assert elements(line_path(7)) != elements(line_path(8))

    def test_path_is_independent_of_zoom(self):
        # Viewport pixels scale with the zoom, the shape in points must not change.
        base = elements(line_path(11, UNIT))
        zoomed = elements(line_path(11, UNIT * 2.5))
        assert_points_close(zoomed, scaled(base, 2.5))

    def test_segment_endpoints_stay_exact(self):
        path = QPainterPath()
        corners = [QPointF(10, 20), QPointF(90, 150), QPointF(300, 40)]
        add_wobbly_polyline(path, corners, 3, 0, UNIT, 1.5)
        points = elements(path)
        assert points[0] == (10, 20)
        assert points[-1] == (300, 40)
        assert (90, 150) in points

    def test_stroke_actually_wobbles_but_only_slightly(self):
        path = line_path(5)
        ys = [y for _, y in elements(path)]
        assert max(abs(y) for y in ys) > 0.1
        # Deviation is a small share of the 80pt length
        assert max(abs(y) for y in ys) < 0.05 * 80 * UNIT

    def test_deviation_grows_with_line_width(self):
        thin, thick = QPainterPath(), QPainterPath()
        corners = [QPointF(0, 0), QPointF(20 * UNIT, 0)]
        add_wobbly_polyline(thin, corners, 5, 0, UNIT, 0.5)
        add_wobbly_polyline(thick, corners, 5, 0, UNIT, 8.0)
        assert max(abs(y) for _, y in elements(thick)) > max(abs(y) for _, y in elements(thin))

    def test_closed_polyline_returns_to_start(self):
        path = wobbly_rectangle_path(QRectF(10, 10, 400, 300), 9, UNIT, 1.5)
        points = elements(path)
        assert points[0] == (10, 10)
        assert (410, 10) in points and (410, 310) in points and (10, 310) in points


class TestWobblyEllipse:
    rect = QRectF(20, 30, 300, 200)

    def test_is_deterministic_and_zoom_independent(self):
        a = elements(wobbly_ellipse_path(self.rect, 4, UNIT, 1.5))
        assert a == elements(wobbly_ellipse_path(self.rect, 4, UNIT, 1.5))
        assert a != elements(wobbly_ellipse_path(self.rect, 5, UNIT, 1.5))
        zoomed_rect = QRectF(self.rect.x() * 2, self.rect.y() * 2, self.rect.width() * 2, self.rect.height() * 2)
        zoomed = elements(wobbly_ellipse_path(zoomed_rect, 4, UNIT * 2, 1.5))
        assert_points_close(zoomed, scaled(a, 2))

    def test_curve_has_no_start_or_end(self):
        """The outline is a closed spline: smooth (equal tangent) where it begins and ends."""
        path = wobbly_ellipse_path(self.rect, 21, UNIT, 1.5)
        points = elements(path)
        start = points[0]
        # moveTo, then (c1, c2, end) per segment, then the closing line element
        segments = [points[1 + 3 * i: 4 + 3 * i] for i in range((len(points) - 1) // 3)]
        first_c1 = segments[0][0]
        last_c2, last_end = segments[-1][1], segments[-1][2]
        assert last_end == pytest.approx(start)
        incoming = (start[0] - last_c2[0], start[1] - last_c2[1])
        outgoing = (first_c1[0] - start[0], first_c1[1] - start[1])
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
        assert dot > 0
        assert abs(cross) < 1e-6 * math.hypot(*incoming) * math.hypot(*outgoing)

    def test_segment_count_grows_with_size(self):
        small = wobbly_ellipse_path(QRectF(0, 0, 40, 40), 1, UNIT, 1.5)
        large = wobbly_ellipse_path(QRectF(0, 0, 1000, 800), 1, UNIT, 1.5)
        assert small.elementCount() >= 1 + 3 * 8
        assert large.elementCount() > small.elementCount()

    def test_stays_within_the_deviation_of_the_ideal_ellipse(self):
        deviation = ellipse_deviation_pt(150, 100, UNIT, 1.5) * UNIT
        path = wobbly_ellipse_path(self.rect, 8, UNIT, 1.5)
        bounds = path.boundingRect()
        slack = deviation * 1.5
        assert bounds.left() >= self.rect.left() - slack
        assert bounds.right() <= self.rect.right() + slack
        assert bounds.top() >= self.rect.top() - slack
        assert bounds.bottom() <= self.rect.bottom() + slack


class TestAnnotationModel:
    def test_off_by_default_and_every_stroke_type_supports_it(self):
        assert HAND_DRAWN_TYPES == set(STROKE_TYPES)
        for ann_type in STROKE_TYPES:
            annotation = VectorAnnotation(ann_type, 0, 0)
            assert annotation.supports_hand_drawn
            assert annotation.hand_drawn is False

    def test_text_does_not_support_it(self):
        text = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Hi", hand_drawn=True)
        assert not text.supports_hand_drawn
        assert text.hand_drawn is False

    def test_new_annotations_get_their_own_seed(self):
        seeds = {VectorAnnotation(AnnotationType.LINE, 0, 0).hand_drawn_seed for _ in range(20)}
        assert len(seeds) > 1

    def test_duplicate_keeps_style_and_seed(self):
        original = VectorAnnotation(AnnotationType.ELLIPSE, 0, 0, hand_drawn=True, hand_drawn_seed=1234)
        copy = original.duplicate()
        assert copy.hand_drawn is True
        assert copy.hand_drawn_seed == 1234

    @pytest.mark.parametrize("ann_type", STROKE_TYPES)
    def test_dict_round_trip_keeps_style_and_seed(self, ann_type):
        original = VectorAnnotation(ann_type, 5, 6, hand_drawn=True, hand_drawn_seed=4321)
        restored = canvas_object_from_dict(original.to_dict())
        assert restored.hand_drawn is True
        assert restored.hand_drawn_seed == 4321

    def test_dict_omits_style_when_off_and_loads_as_off(self):
        data = VectorAnnotation(AnnotationType.LINE, 0, 0).to_dict()
        assert "hand_drawn" not in data and "hand_drawn_seed" not in data
        assert canvas_object_from_dict(data).hand_drawn is False

    def test_project_file_round_trip(self):
        on = VectorAnnotation(AnnotationType.ARROW, 5, 6, hand_drawn=True, hand_drawn_seed=99)
        off = VectorAnnotation(AnnotationType.LINE, 5, 6)
        project = ProjectFile.from_annotations(document_path="doc.pdf", annotations=[on, off])
        entries = project["annotations"]
        assert entries[0]["hand_drawn"] is True and entries[0]["hand_drawn_seed"] == 99
        assert "hand_drawn" not in entries[1]
        restored_on, restored_off = ProjectFile.load_annotations(project)
        assert restored_on.hand_drawn is True and restored_on.hand_drawn_seed == 99
        assert restored_off.hand_drawn is False


def alpha_bbox(annotation: VectorAnnotation):
    return annotation.render_to_pil().split()[3].getbbox()


class TestRendering:
    @pytest.mark.parametrize("ann_type", STROKE_TYPES)
    def test_hand_drawn_looks_different_from_straight(self, ann_type):
        straight = VectorAnnotation(ann_type, 0, 0).render_to_pil()
        sketched = VectorAnnotation(ann_type, 0, 0, hand_drawn=True, hand_drawn_seed=17).render_to_pil()
        assert sketched.tobytes() != straight.tobytes()

    @pytest.mark.parametrize("ann_type", STROKE_TYPES)
    def test_rendering_is_stable_and_depends_on_seed(self, ann_type):
        def render(seed):
            return VectorAnnotation(ann_type, 0, 0, hand_drawn=True, hand_drawn_seed=seed).render_to_pil().tobytes()

        assert render(17) == render(17)
        assert render(17) != render(18)

    @pytest.mark.parametrize("line_width_pt", [0.5, 1.5, 6.0, 16.0])
    def test_rectangle_corners_stay_where_the_straight_one_has_them(self, line_width_pt):
        straight = VectorAnnotation(AnnotationType.RECTANGLE, 0, 0, line_width_pt=line_width_pt)
        sketched = VectorAnnotation(
            AnnotationType.RECTANGLE, 0, 0, hand_drawn=True, hand_drawn_seed=5, line_width_pt=line_width_pt,
        )
        width, height = straight.render_to_pil().size
        half_pen = max(1.5, line_width_pt * UNIT) / 2.0
        corners = [
            (half_pen, half_pen), (width - half_pen, half_pen),
            (width - half_pen, height - half_pen), (half_pen, height - half_pen),
        ]
        for x, y in corners:
            # Both draw their stroke through the same corner points: the corner pixel is inked.
            assert straight.render_to_pil().getpixel((round(x), round(y)))[3] > 0
            assert sketched.render_to_pil().getpixel((round(x), round(y)))[3] > 0

    @pytest.mark.parametrize("ann_type", [AnnotationType.RECTANGLE, AnnotationType.ELLIPSE])
    @pytest.mark.parametrize("line_width_pt", [0.5, 1.5, 6.0, 16.0])
    def test_export_render_keeps_the_whole_wobble(self, ann_type, line_width_pt):
        """The box-sized render may cut off wobble that bulges past the box; the export render
        has room around the box, so nothing is cut and the edge pixels stay transparent."""
        for seed in range(25):
            annotation = VectorAnnotation(
                ann_type, 100, 100, hand_drawn=True, hand_drawn_seed=seed, line_width_pt=line_width_pt,
            )
            image, x, y = annotation.render_for_compositing()
            box_w, box_h = annotation.render_to_pil().size
            assert image.width > box_w and image.height > box_h
            assert x < 100 and y < 100
            alpha = image.split()[3]
            assert alpha.getbbox() is not None
            left, top, right, bottom = alpha.getbbox()
            assert left > 0 and top > 0 and right < image.width and bottom < image.height

    def test_export_render_is_unchanged_when_not_hand_drawn(self):
        annotation = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
        image, x, y = annotation.render_for_compositing()
        assert image.size == annotation.render_to_pil().size
        assert (x, y) == (100, 100)

    def test_rotated_export_render_stays_centered_on_the_box(self):
        annotation = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, hand_drawn=True, hand_drawn_seed=3)
        annotation.rotation = 30
        image, x, y = annotation.render_for_compositing()
        center_x = 100 + annotation.scaled_width / 2.0
        center_y = 100 + annotation.scaled_height / 2.0
        assert x + image.width / 2.0 == pytest.approx(center_x)
        assert y + image.height / 2.0 == pytest.approx(center_y)

    def test_thin_rectangle_does_not_collapse(self):
        annotation = VectorAnnotation(AnnotationType.RECTANGLE, 0, 0, hand_drawn=True, hand_drawn_seed=2)
        annotation.set_scaled_size(600, 24)
        image, _, _ = annotation.render_for_compositing()
        assert image.split()[3].getbbox() is not None

    def test_selection_geometry_ignores_the_style(self):
        straight = VectorAnnotation(AnnotationType.ARROW, 0, 0)
        sketched = VectorAnnotation(AnnotationType.ARROW, 0, 0, hand_drawn=True, hand_drawn_seed=3)
        args = (10.0, 20.0, 333.0, 333.0)
        assert straight.boundary_points_viewport(*args) == sketched.boundary_points_viewport(*args)
