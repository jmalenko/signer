"""Changing the colour from the toolbar applies to every selected annotation that has a colour,
is undoable in one step, and counts as a change of the document (spec §7.8, §11)."""

from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtGui import QColor

from signer.objects import AnnotationType, SignatureObject, VectorAnnotation


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    return main_window


def pick(window, color):
    with patch("signer.main_window.QColorDialog.getColor", return_value=QColor(color)):
        window._pick_color()


def test_colour_applies_to_every_selected_annotation_and_is_one_undo_step(window):
    canvas = window.canvas
    first = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    second = VectorAnnotation(AnnotationType.ELLIPSE, 600, 100)
    canvas.add_object(first)
    canvas.add_object(second)
    canvas.select_all_on_page()
    before = (first.color.name(), second.color.name())
    window._has_unsaved_changes = False
    undo_depth = len(canvas.history.undo_stack)

    pick(window, "#0000ff")

    assert (first.color.name(), second.color.name()) == ("#0000ff", "#0000ff")
    assert window._has_unsaved_changes is True
    assert len(canvas.history.undo_stack) == undo_depth + 1
    assert canvas.undo()
    assert (first.color.name(), second.color.name()) == before
    assert canvas.redo()
    assert (first.color.name(), second.color.name()) == ("#0000ff", "#0000ff")


def test_colour_leaves_selected_images_alone(window):
    canvas = window.canvas
    line = VectorAnnotation(AnnotationType.LINE, 100, 100)
    image = SignatureObject(Image.new("RGBA", (50, 50), "black"), "sig.png", 600, 100)
    canvas.add_object(line)
    canvas.add_object(image)
    canvas.select_all_on_page()
    image_color = image.color.name()

    pick(window, "#00aa00")

    assert line.color.name() == "#00aa00"
    assert image.color.name() == image_color
