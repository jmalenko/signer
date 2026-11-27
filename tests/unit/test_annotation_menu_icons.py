"""Regression tests for the Line and Arrow menu symbols."""

import sys
from statistics import median

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter


def _stem_thickness(menu, action, foreground="black", background="white"):
    image = QImage(64, 64, QImage.Format_ARGB32)
    image.fill(QColor(background))
    painter = QPainter(image)
    painter.setFont(menu.font())
    painter.setPen(QColor(foreground))
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, action.text().split()[0])
    painter.end()
    pixels = [
        (x, y)
        for x in range(image.width())
        for y in range(image.height())
        if abs(image.pixelColor(x, y).lightness() - QColor(background).lightness()) > 128
    ]
    assert pixels
    left = min(x for x, _ in pixels)
    right = max(x for x, _ in pixels)
    stem_columns = range(left, left + max(1, (right - left + 1) // 3))
    return median(sum(x == column for x, _ in pixels) for column in stem_columns)


def _line_and_arrow(menu):
    actions = menu.actions()
    return (
        next(action for action in actions if action.text().endswith(" Line")),
        next(action for action in actions if action.text().endswith(" Arrow")),
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="The Windows menu font draws the arrow glyph with a different stroke than the dash "
    "glyph, which makes this pixel measurement meaningless there (the menu looks right).",
)
@pytest.mark.parametrize(
    ("foreground", "background"), [("black", "white"), ("white", "black")]
)
def test_line_and_arrow_stems_have_similar_thickness(main_window, foreground, background):
    menu = main_window._toolbar_add_annotation_btn.menu()
    line, arrow = _line_and_arrow(menu)
    assert abs(
        _stem_thickness(menu, line, foreground, background)
        - _stem_thickness(menu, arrow, foreground, background)
    ) <= 1


