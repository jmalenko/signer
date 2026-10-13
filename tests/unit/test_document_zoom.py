from PIL import Image
from PySide6.QtCore import QPointF


def _pages(count=1):
    return [Image.new("RGB", (400, 300), "white") for _ in range(count)]


def test_zoom_in_and_out_are_reversible(canvas):
    canvas.set_pages(_pages())
    initial_zoom = canvas.zoom

    canvas.zoom_in()
    canvas.zoom_out()

    assert canvas.zoom == initial_zoom


def test_zoom_round_trip_from_fit_restores_the_fit_transform(canvas):
    canvas.resize(500, 500)
    canvas.set_pages(_pages())
    initial_offsets = (canvas._pan_x, canvas._pan_y)

    canvas.zoom_in()
    canvas.zoom_out()

    assert canvas.zoom == 1.0
    assert (canvas._pan_x, canvas._pan_y) == initial_offsets
    assert canvas.is_fit_to_window


def test_zoom_out_and_in_are_reversible(canvas):
    canvas.set_pages(_pages())
    canvas._set_zoom(1.25)
    initial_zoom = canvas.zoom

    canvas.zoom_out()
    canvas.zoom_in()

    assert canvas.zoom == initial_zoom


def test_fit_to_window_resets_zoom_and_pan(canvas):
    canvas.set_pages(_pages())
    canvas._set_zoom(2.0, QPointF(120, 90))

    canvas.fit_to_window()

    assert canvas.zoom == 1.0
    assert canvas._pan_x == 0.0
    assert canvas._pan_y == 0.0


def test_zoom_out_stops_at_fit_to_window(canvas):
    canvas.set_pages(_pages())
    canvas._set_zoom(1.25)

    canvas.zoom_out()
    canvas.zoom_out()

    assert canvas.zoom == 1.0


def test_zoom_out_preserves_the_existing_gray_margin_side(canvas):
    canvas.resize(400, 400)
    canvas.set_pages([Image.new("RGB", (400, 200), "white")])
    canvas._pan_y = 50.0
    canvas._recompute_fit()
    canvas._set_zoom(1.25, QPointF(200, 350))

    canvas.zoom_out()

    assert canvas.zoom == 1.0
    assert canvas._doc_offset_y == 200.0
    assert canvas._doc_offset_y + 200.0 == canvas.height()


def test_zoom_anchor_keeps_document_point_under_pointer(canvas):
    canvas.set_pages(_pages())
    anchor = QPointF(120, 90)
    document_point = canvas._view_to_doc(anchor)

    canvas._set_zoom(2.0, anchor)

    anchored_point = canvas._view_to_doc(anchor)
    assert anchored_point.x() == document_point.x()
    assert anchored_point.y() == document_point.y()


def test_page_change_resets_zoom_and_pan(canvas):
    canvas.set_pages(_pages(2))
    canvas._set_zoom(2.0, QPointF(120, 90))

    canvas.goto_page(1)

    assert canvas.zoom == 1.0
    assert canvas._pan_x == 0.0
    assert canvas._pan_y == 0.0


def test_replacing_document_resets_zoom_and_pan(canvas):
    canvas.set_pages(_pages())
    canvas._set_zoom(2.0, QPointF(120, 90))

    canvas.set_pages(_pages())

    assert canvas.zoom == 1.0
    assert canvas._pan_x == 0.0
    assert canvas._pan_y == 0.0