"""Guard test: opening a document must not leave any state from the previous one.

A2 was exactly this class of bug — `set_pages()` reset six per-document fields
and silently missed `_page_rotations`. Rather than asserting one field at a time,
this compares the canvas's whole attribute state after a heavily-used document is
replaced against a canvas that has only ever seen the replacement document. A new
per-document field that `_reset_document_state()` forgets shows up here as a diff.
"""

from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, SignalInstance
from PySide6.QtGui import QMouseEvent

from signer.canvas import DocumentCanvas
from signer.history import HistoryStack
from signer.objects import AnnotationType, VectorAnnotation

# State that is intentionally not per-document, or not comparable by value.
_NOT_PER_DOCUMENT = {
    "_pages",            # the new document's own pages
    "_page_pixmaps",     # QPixmap objects, compared via _pages instead
    "_cached_copy_data",  # the clipboard deliberately survives a document change
}


def _pages(count=3, size=(600, 800)):
    return [Image.new("RGB", size, color="white") for _ in range(count)]


def _comparable_state(canvas: DocumentCanvas) -> dict:
    state = {}
    for name, value in vars(canvas).items():
        if name in _NOT_PER_DOCUMENT or isinstance(value, SignalInstance):
            continue
        if isinstance(value, HistoryStack):
            state[name] = (len(value.undo_stack), len(value.redo_stack))
        elif isinstance(value, QPointF):
            state[name] = (value.x(), value.y())
        else:
            state[name] = repr(value)
    return state


def _use_document_heavily(canvas):
    """Touch as much per-document state as a real session would."""
    canvas.set_pages(_pages())
    first = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
    second = VectorAnnotation(AnnotationType.CROSSMARK, 200, 200, 0)
    canvas.add_object(first)
    canvas.add_object(second)
    canvas.select_all_on_page()
    canvas.copy_selected()
    canvas.rotate_current_page_left()
    canvas.goto_page(1)
    canvas.rotate_all_pages_right()
    canvas.goto_page(0)
    canvas.select_annotation(first)
    press = QPointF(first.x + first.scaled_width / 2, first.y + first.scaled_height / 2)
    canvas.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, press, press, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    ))
    canvas.move_selected(5, 5)


def test_opening_a_document_leaves_no_state_from_the_previous_one(qtbot):
    used = DocumentCanvas()
    qtbot.addWidget(used)
    _use_document_heavily(used)
    used.set_pages(_pages(count=2, size=(400, 500)))

    fresh = DocumentCanvas()
    qtbot.addWidget(fresh)
    fresh.set_pages(_pages(count=2, size=(400, 500)))

    assert _comparable_state(used) == _comparable_state(fresh)


def test_the_replacement_documents_own_pages_are_installed(qtbot):
    canvas = DocumentCanvas()
    qtbot.addWidget(canvas)
    _use_document_heavily(canvas)

    canvas.set_pages(_pages(count=2, size=(400, 500)))

    assert canvas.page_count == 2
    assert canvas._pages[0].size == (400, 500)
    assert (canvas._page_pixmaps[0].width(), canvas._page_pixmaps[0].height()) == (400, 500)


def test_history_from_the_previous_document_is_not_undoable(qtbot):
    """Stale undo entries would operate on objects that no longer exist."""
    canvas = DocumentCanvas()
    qtbot.addWidget(canvas)
    _use_document_heavily(canvas)

    canvas.set_pages(_pages(count=1))

    assert canvas.can_undo() is False
    assert canvas.can_redo() is False


def test_clipboard_survives_but_loses_its_page_association(qtbot):
    """The documented exception to the reset."""
    canvas = DocumentCanvas()
    qtbot.addWidget(canvas)
    _use_document_heavily(canvas)

    canvas.set_pages(_pages(count=1))

    assert canvas._cached_copy_data, "copied annotations stay pasteable"
    assert all(item["page"] is None for item in canvas._cached_copy_data)
