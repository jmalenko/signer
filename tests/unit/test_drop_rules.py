"""Dropping files on the canvas (spec §4.3)."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF

from signer.objects import SignatureObject


@pytest.fixture(autouse=True)
def no_modal_error_boxes():
    """A message box would wait for a click; a failing test must fail instead of hanging."""
    with patch("signer.main_window.QMessageBox.critical"):
        yield


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    return main_window


@pytest.fixture
def small_image(tmp_path):
    path = tmp_path / "stamp.png"
    Image.new("RGBA", (200, 100), (255, 0, 0, 255)).save(path)
    return path


def test_a_small_image_is_placed_centered_on_the_drop_position(window, small_image):
    window._on_file_drop(str(small_image), QPointF(800, 900))

    obj = window.canvas.current_page_objects()[-1]
    assert isinstance(obj, SignatureObject)
    assert (obj.x + obj.scaled_width / 2, obj.y + obj.scaled_height / 2) == pytest.approx((800, 900))


def test_a_small_image_dropped_near_the_edge_stays_on_the_page(window, small_image):
    window._on_file_drop(str(small_image), QPointF(5, 5))

    obj = window.canvas.current_page_objects()[-1]
    assert obj.x >= 0 and obj.y >= 0


def test_the_canvas_passes_the_drop_position_to_the_window(window, small_image):
    from PySide6.QtCore import QMimeData, QUrl, Qt
    from PySide6.QtGui import QDropEvent

    canvas = window.canvas
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(small_image))])
    received = []
    canvas.fileDrop.connect(lambda path, point: received.append((path, point)))

    canvas.dropEvent(QDropEvent(QPointF(120, 150), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))

    assert Path(received[0][0]) == small_image  # Qt URLs use forward slashes
    assert received[0][1] == canvas._view_to_doc(QPointF(120, 150))


@pytest.mark.parametrize("name", ["document.docx", "document.odt", "document.doc"])
def test_a_dropped_word_or_odt_document_is_opened_like_open_does(window, sample_pdf, name):
    source = sample_pdf.parent / name
    with patch.object(window, "open_document") as open_document:
        window._on_file_drop(str(source))
    open_document.assert_called_once_with(str(source))


def test_a_dropped_project_is_opened_like_open_does(window, tmp_path):
    project = tmp_path / "p.signer"
    project.write_text("{}")
    with patch.object(window, "open_document") as open_document:
        window._on_file_drop(str(project))
    open_document.assert_called_once_with(str(project))
