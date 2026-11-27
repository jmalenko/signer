"""Zoom shortcuts and panning with Space + drag (spec §4.6, §13)."""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtTest import QTest


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    main_window.show()
    return main_window


@pytest.mark.parametrize("key, modifier", [
    (Qt.Key_Equal, Qt.ControlModifier), (Qt.Key_Plus, Qt.ControlModifier), (Qt.Key_Equal, Qt.NoModifier),
])
def test_zoom_in_shortcuts(window, key, modifier):
    before = window.canvas.zoom

    QTest.keyClick(window.canvas, key, modifier)

    assert window.canvas.zoom > before


@pytest.mark.parametrize("modifier", [Qt.ControlModifier, Qt.NoModifier])
def test_zoom_out_and_fit_shortcuts(window, modifier):
    canvas = window.canvas
    canvas.zoom_in()
    canvas.zoom_in()
    zoomed = canvas.zoom

    QTest.keyClick(canvas, Qt.Key_Minus, modifier)
    assert canvas.zoom < zoomed

    QTest.keyClick(canvas, Qt.Key_0, modifier)
    assert canvas.is_fit_to_window


def test_the_plus_key_still_opens_the_add_menu(window):
    from unittest.mock import patch

    with patch.object(window, "show_annotation_menu") as show:
        QTest.keyClick(window.canvas, Qt.Key_Plus, Qt.NoModifier)
    show.assert_called_once()


def mouse(kind, pos, button=Qt.LeftButton, buttons=Qt.LeftButton):
    return QMouseEvent(kind, QPointF(*pos), QPointF(*pos), button, buttons, Qt.NoModifier)


def test_space_and_left_drag_pans_the_zoomed_page(window):
    canvas = window.canvas
    for _ in range(4):
        canvas.zoom_in()
    start = (canvas._pan_x, canvas._pan_y)
    window._has_unsaved_changes = False

    canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Space, Qt.NoModifier))
    canvas.mousePressEvent(mouse(QEvent.MouseButtonPress, (300, 300)))
    canvas.mouseMoveEvent(mouse(QEvent.MouseMove, (250, 260), Qt.NoButton))
    canvas.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, (250, 260), Qt.LeftButton, Qt.NoButton))
    canvas.keyReleaseEvent(QKeyEvent(QEvent.KeyRelease, Qt.Key_Space, Qt.NoModifier))

    assert (canvas._pan_x, canvas._pan_y) != start
    assert not canvas._panning
    assert window._has_unsaved_changes is False, "panning only changes the view"


def test_a_left_drag_without_space_does_not_pan(window):
    canvas = window.canvas
    for _ in range(4):
        canvas.zoom_in()
    start = (canvas._pan_x, canvas._pan_y)

    canvas.mousePressEvent(mouse(QEvent.MouseButtonPress, (300, 300)))
    canvas.mouseMoveEvent(mouse(QEvent.MouseMove, (250, 260), Qt.NoButton))
    canvas.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, (250, 260), Qt.LeftButton, Qt.NoButton))

    assert (canvas._pan_x, canvas._pan_y) == start
