"""Regression tests for the keyboard/window-command plumbing on the canvas.

See CODE_REVIEW_PLAN.md sections C1 and C2.
"""

from PIL import Image
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from signer.canvas import DocumentCanvas


class _RecordingWindow:
    """Stand-in for MainWindow that records which command the canvas invoked."""

    def __init__(self):
        self.calls = []

    def undo(self):
        self.calls.append("undo")

    def redo(self):
        self.calls.append("redo")


def _key_event(key, modifiers=Qt.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.KeyPress, key, modifiers)


def _canvas_with_window(qapp, monkeypatch):
    canvas = DocumentCanvas()
    canvas.set_pages([Image.new("RGB", (400, 400), "white")])
    window = _RecordingWindow()
    monkeypatch.setattr(canvas, "parent", lambda: window)
    return canvas, window


def test_ctrl_shift_z_redoes(qapp, monkeypatch):
    """Ctrl+Shift+Z is the conventional redo chord; it must not undo."""
    canvas, window = _canvas_with_window(qapp, monkeypatch)

    canvas.keyPressEvent(_key_event(Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier))

    assert window.calls == ["redo"]


def test_ctrl_z_undoes(qapp, monkeypatch):
    canvas, window = _canvas_with_window(qapp, monkeypatch)

    canvas.keyPressEvent(_key_event(Qt.Key_Z, Qt.ControlModifier))

    assert window.calls == ["undo"]


def test_ctrl_y_redoes(qapp, monkeypatch):
    canvas, window = _canvas_with_window(qapp, monkeypatch)

    canvas.keyPressEvent(_key_event(Qt.Key_Y, Qt.ControlModifier))

    assert window.calls == ["redo"]


def test_ctrl_plus_is_not_a_redo_shortcut(qapp, monkeypatch):
    """`+` opens the Add Annotation menu; Ctrl++ was never meant to redo."""
    canvas, window = _canvas_with_window(qapp, monkeypatch)

    canvas.keyPressEvent(_key_event(Qt.Key_Plus, Qt.ControlModifier))

    assert window.calls == []


def test_missing_window_command_is_logged(qapp, monkeypatch, caplog):
    """A canvas whose parent can't handle the command must leave a trace instead
    of making the shortcut silently dead."""
    canvas = DocumentCanvas()
    canvas.set_pages([Image.new("RGB", (400, 400), "white")])
    monkeypatch.setattr(canvas, "parent", lambda: object())

    with caplog.at_level("WARNING"):
        canvas.keyPressEvent(_key_event(Qt.Key_Z, Qt.ControlModifier))

    assert any("undo" in r.message for r in caplog.records)
