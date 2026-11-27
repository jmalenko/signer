"""Whatever way a property is changed - toolbar, keyboard shortcut, resizing - it becomes the
default of the next new annotation (spec §7.8)."""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from signer.objects import AnnotationType, VectorAnnotation


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    return main_window


def press(canvas, key):
    canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))


def mouse(kind, pos, button=Qt.LeftButton, buttons=Qt.LeftButton):
    return QMouseEvent(kind, QPointF(*pos), QPointF(*pos), button, buttons, Qt.NoModifier)


def test_the_bracket_keys_change_the_default_font_size(window):
    text = VectorAnnotation(AnnotationType.TEXT, 100, 100, text="hello", font_size_pt=11)
    window.canvas.add_object(text)

    press(window.canvas, Qt.Key_BracketRight)

    assert text._font_size_pt == 12
    assert window._settings.recent_font_size_pt == 12


def test_the_bracket_keys_change_the_default_line_width(window):
    line = VectorAnnotation(AnnotationType.LINE, 100, 100)
    window.canvas.add_object(line)

    press(window.canvas, Qt.Key_BracketRight)

    assert window._settings.recent_line_width_pt == line._line_width_pt != 1.5


def test_resizing_a_text_changes_the_default_font_size(window):
    canvas = window.canvas
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = canvas._doc_offset_y = 0.0
    text = VectorAnnotation(AnnotationType.TEXT, 300, 300, text="hello", font_size_pt=11)
    canvas.add_object(text)
    rect = canvas._object_view_rect(text)
    handle = text.handle_rects_viewport(rect.x(), rect.y(), rect.width(), rect.height(), 0.0)[7].center()

    canvas.mousePressEvent(mouse(QEvent.MouseButtonPress, (handle.x(), handle.y())))
    canvas.mouseMoveEvent(mouse(QEvent.MouseMove, (handle.x() + 150, handle.y() + 60), Qt.NoButton))
    canvas.mouseReleaseEvent(mouse(QEvent.MouseButtonRelease, (handle.x() + 150, handle.y() + 60), Qt.LeftButton, Qt.NoButton))

    assert text._font_size_pt > 11
    assert window._settings.recent_font_size_pt == text._font_size_pt
