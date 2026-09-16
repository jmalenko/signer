"""Unit tests for discrete step sizes of `[` / `]` keyboard shortcuts (v1.2.32)."""

import pytest
from signer.canvas import DocumentCanvas
from signer.objects import (
    VectorAnnotation,
    AnnotationType,
    FONT_SIZE_STEPS_PT,
    LINE_WIDTH_STEPS_PT,
    step_size,
)


class TestStepSizeHelper:
    """Test the generic step_size() function used by both properties."""

    def test_increase_moves_to_next_step(self):
        assert step_size(11, FONT_SIZE_STEPS_PT, 'increase') == 12

    def test_decrease_moves_to_previous_step(self):
        assert step_size(12, FONT_SIZE_STEPS_PT, 'decrease') == 11

    def test_increase_then_decrease_returns_to_start(self):
        for value in FONT_SIZE_STEPS_PT[1:-1]:
            increased = step_size(value, FONT_SIZE_STEPS_PT, 'increase')
            assert step_size(increased, FONT_SIZE_STEPS_PT, 'decrease') == value

    def test_decrease_then_increase_returns_to_start(self):
        for value in FONT_SIZE_STEPS_PT[1:-1]:
            decreased = step_size(value, FONT_SIZE_STEPS_PT, 'decrease')
            assert step_size(decreased, FONT_SIZE_STEPS_PT, 'increase') == value

    def test_clamped_at_maximum(self):
        maximum = FONT_SIZE_STEPS_PT[-1]
        assert step_size(maximum, FONT_SIZE_STEPS_PT, 'increase') == maximum

    def test_clamped_at_minimum(self):
        minimum = FONT_SIZE_STEPS_PT[0]
        assert step_size(minimum, FONT_SIZE_STEPS_PT, 'decrease') == minimum

    def test_snaps_up_from_off_list_value(self):
        assert step_size(13, FONT_SIZE_STEPS_PT, 'increase') == 14

    def test_snaps_down_from_off_list_value(self):
        assert step_size(13, FONT_SIZE_STEPS_PT, 'decrease') == 12

    def test_font_size_steps_have_no_ten_point_five(self):
        assert 10.5 not in FONT_SIZE_STEPS_PT

    def test_line_width_steps_reversible(self):
        for value in LINE_WIDTH_STEPS_PT[1:-1]:
            increased = step_size(value, LINE_WIDTH_STEPS_PT, 'increase')
            assert step_size(increased, LINE_WIDTH_STEPS_PT, 'decrease') == value


class TestAdjustAnnotationProperty:
    """Test DocumentCanvas._adjust_annotation_property with the real code path."""

    def _canvas_with(self, obj, qtbot):
        canvas = DocumentCanvas()
        qtbot.addWidget(canvas)
        canvas._page_objects[0] = [obj]
        return canvas

    def test_bracket_right_steps_font_size(self, qtbot):
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 11
        canvas = self._canvas_with(text, qtbot)

        canvas._adjust_annotation_property([text], 'increase')

        assert text._font_size_pt == 12

    def test_bracket_left_steps_font_size(self, qtbot):
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 12
        canvas = self._canvas_with(text, qtbot)

        canvas._adjust_annotation_property([text], 'decrease')

        assert text._font_size_pt == 11

    def test_bracket_right_then_left_returns_to_same_font_size(self, qtbot):
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 11
        canvas = self._canvas_with(text, qtbot)

        canvas._adjust_annotation_property([text], 'increase')
        canvas._adjust_annotation_property([text], 'decrease')

        assert text._font_size_pt == 11

    def test_bracket_left_then_right_returns_to_same_line_width(self, qtbot):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 1.5
        canvas = self._canvas_with(line, qtbot)

        canvas._adjust_annotation_property([line], 'decrease')
        canvas._adjust_annotation_property([line], 'increase')

        assert line._line_width_pt == 1.5

    def test_bracket_right_steps_line_width_significantly(self, qtbot):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 1.5
        canvas = self._canvas_with(line, qtbot)

        canvas._adjust_annotation_property([line], 'increase')

        assert line._line_width_pt == 2
