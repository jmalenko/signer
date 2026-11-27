"""Regression tests for the Rectangle / Square menu symbol."""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter


def _visible_vertical_edges(menu, foreground, background):
    action = next(
        action for action in menu.actions() if action.text().endswith("Rectangle / Square")
    )
    image = QImage(64, 64, QImage.Format_ARGB32)
    background_color = QColor(background)
    image.fill(background_color)
    painter = QPainter(image)
    painter.setFont(menu.font())
    painter.setPen(QColor(foreground))
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, action.text().split()[0])
    painter.end()
    def contrast(x, y):
        return abs(image.pixelColor(x, y).lightness() - background_color.lightness())

    pixels = [
        (x, y)
        for x in range(image.width())
        for y in range(image.height())
        if contrast(x, y) > 35
    ]
    assert pixels
    left = min(x for x, _ in pixels)
    right = max(x for x, _ in pixels)
    top = min(y for _, y in pixels)
    bottom = max(y for _, y in pixels)
    middle = (left + right) // 2
    inner_rows = range(top + 1, bottom)
    return (
        sum(contrast(x, y) > 128 for x in range(left, middle) for y in inner_rows),
        sum(contrast(x, y) > 128 for x in range(middle + 1, right + 1) for y in inner_rows),
    )


@pytest.mark.parametrize(
    ("foreground", "background"), [("black", "white"), ("white", "black")]
)
def test_rectangle_vertical_edges_are_visible(main_window, foreground, background):
    menu = main_window._toolbar_add_annotation_btn.menu()
    assert min(_visible_vertical_edges(menu, foreground, background)) >= 2
