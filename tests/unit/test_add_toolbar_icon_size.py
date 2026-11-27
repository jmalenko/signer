"""macOS Add icon size regression."""

import sys

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific icon")


def _glyph_size(glyph, font):
    image = QImage(80, 80, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(QRect(0, 0, 80, 80), Qt.AlignCenter, glyph)
    painter.end()
    pixels = [
        (x, y)
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 32
    ]
    assert pixels
    return (
        max(x for x, _ in pixels) - min(x for x, _ in pixels) + 1,
        max(y for _, y in pixels) - min(y for _, y in pixels) + 1,
    )


def _icon_size(button):
    image = button.icon().pixmap(button.iconSize()).toImage()
    pixels = [
        (x, y)
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 32
    ]
    if not pixels:
        return (0, 0)
    return (
        max(x for x, _ in pixels) - min(x for x, _ in pixels) + 1,
        max(y for _, y in pixels) - min(y for _, y in pixels) + 1,
    )


def _reference_size(button):
    sizes = [_glyph_size(glyph, button.font()) for glyph in ("📂", "💾")]
    return tuple(min(size[axis] for size in sizes) for axis in (0, 1))


def test_add_plus_is_comparable_to_open_and_save(main_window):
    button = main_window._toolbar_add_annotation_btn
    assert all(
        actual >= reference * 0.8
        for actual, reference in zip(_icon_size(button), _reference_size(button))
    )
