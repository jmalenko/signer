"""Regression tests for the Add toolbar button's plus glyph."""

import sys

import pytest
from PySide6.QtGui import QColor, QIcon, QPalette


@pytest.mark.parametrize(
    ("foreground", "background"), [("white", "black"), ("black", "white")]
)
@pytest.mark.parametrize(("group", "mode"), [(QPalette.Active, QIcon.Normal), (QPalette.Disabled, QIcon.Disabled)])
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific glyph")
def test_add_plus_contrasts_with_toolbar_background(main_window, foreground, background, group, mode):
    button = main_window._toolbar_add_annotation_btn
    palette = button.palette()
    palette.setColor(group, QPalette.ButtonText, QColor(foreground))
    button.setPalette(palette)
    image = button.icon().pixmap(button.iconSize(), mode).toImage()
    pixels = [
        image.pixelColor(x, y)
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 200
    ]
    assert pixels
    assert all(
        abs(pixel.lightness() - QColor(background).lightness()) > 128 for pixel in pixels
    )
