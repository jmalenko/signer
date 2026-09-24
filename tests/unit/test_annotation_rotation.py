"""Tests for free annotation rotation and page-relative rotation."""

import math
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QDialog

from signer.history import RotateAnnotationAction
from signer.objects import AnnotationType, SignatureObject, VectorAnnotation


class _MouseMoveEvent:
    def __init__(self, position: QPointF, modifiers=Qt.NoModifier):
        self._position = position
        self._modifiers = modifiers

    def position(self):
        return self._position

    def modifiers(self):
        return self._modifiers


def test_rotation_defaults_to_zero_and_roundtrips_for_all_annotation_kinds():
    vector = VectorAnnotation(AnnotationType.RECTANGLE, 10, 20)
    signature = SignatureObject(Image.new("RGBA", (40, 20), "black"), "signature.png", 30, 40)

    assert vector.rotation == 0
    assert signature.rotation == 0

    vector.rotation = 345
    signature.rotation = 15

    restored_vector = VectorAnnotation.from_dict(vector.to_dict())
    restored_signature = SignatureObject.from_dict(signature.to_dict())

    assert restored_vector.rotation == 345
    assert restored_signature.rotation == 15


def test_rotation_is_backward_compatible_and_preserved_by_duplicate():
    data = VectorAnnotation(AnnotationType.CHECKMARK, 10, 20).to_dict()
    data.pop("rotation")

    restored = VectorAnnotation.from_dict(data)
    restored.rotation = 30
    duplicate = restored.duplicate()

    assert VectorAnnotation.from_dict(data).rotation == 0
    assert duplicate.rotation == 30


def test_rotation_snaps_to_fifteen_degrees_unless_shift_is_held():
    from signer.canvas import DocumentCanvas

    assert DocumentCanvas._snap_rotation_angle(22.0, shift_pressed=False) == 15
    assert DocumentCanvas._snap_rotation_angle(23.0, shift_pressed=False) == 30
    assert DocumentCanvas._snap_rotation_angle(22.0, shift_pressed=True) == 22.0


def test_rotate_selection_uses_shared_center_and_preserves_relative_angles(canvas):
    canvas.set_pages([Image.new("RGB", (500, 500), "white")])
    first = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    second = VectorAnnotation(AnnotationType.RECTANGLE, 200, 100)
    second.rotation = 30
    canvas.add_object(first)
    canvas.add_object(second)
    canvas._selected = first
    canvas._selected_multiple = {first, second}
    canvas.clear_history()
    old_bounds = canvas._selection_doc_bounds([first, second])
    old_first_center = QPointF(
        first.x + first.scaled_width / 2.0,
        first.y + first.scaled_height / 2.0,
    )

    canvas.rotate_selected_to(90)

    assert first.rotation == 90
    assert second.rotation == 120
    expected_first_center = first._rotate_point(
        old_first_center, old_bounds.center(), 90
    )
    assert (
        first.x + first.scaled_width / 2.0,
        first.y + first.scaled_height / 2.0,
    ) == pytest.approx((expected_first_center.x(), expected_first_center.y()))

    assert canvas.undo()
    assert (first.x, first.y, first.rotation) == pytest.approx((100, 100, 0))
    assert (second.x, second.y, second.rotation) == pytest.approx((200, 100, 30))

    assert canvas.redo()
    assert first.rotation == 90
    assert second.rotation == 120


def test_group_rotation_uses_complete_selection_boundary_center(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    small = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100)
    large = VectorAnnotation(AnnotationType.RECTANGLE, 300, 100)
    canvas.add_object(small)
    canvas.add_object(large)
    canvas._selected = small
    canvas._selected_multiple = {small, large}
    canvas.clear_history()

    old_bounds = canvas._selection_doc_bounds([small, large])
    canvas.rotate_selected_to(90)
    new_bounds = canvas._selection_doc_bounds([small, large])

    assert (new_bounds.center().x(), new_bounds.center().y()) == pytest.approx(
        (old_bounds.center().x(), old_bounds.center().y())
    )


def test_rotate_annotation_action_restores_position_and_angle(canvas):
    canvas.set_pages([Image.new("RGB", (500, 500), "white")])
    annotation = VectorAnnotation(AnnotationType.RECTANGLE, 20, 30)
    canvas.add_object(annotation)
    object_id = canvas._stable_id_for(annotation)
    canvas.clear_history()

    action = RotateAnnotationAction(
        object_id=object_id,
        from_x=20,
        from_y=30,
        from_rotation=0,
        to_x=40,
        to_y=50,
        to_rotation=45,
    )
    action.execute(canvas)
    assert (annotation.x, annotation.y, annotation.rotation) == (40, 50, 45)

    action.undo(canvas)
    assert (annotation.x, annotation.y, annotation.rotation) == (20, 30, 0)


def test_page_rotation_transforms_complete_annotation_geometry(canvas):
    canvas.set_pages([Image.new("RGB", (400, 500), "white")])
    annotation = VectorAnnotation(AnnotationType.RECTANGLE, 20, 120)
    annotation.rotation = 30
    canvas._page_objects[0] = [annotation]
    canvas._page_rotations[0] = 90

    rotated = canvas.page_objects_with_rotation_at(0)[0]

    assert rotated is not annotation
    assert rotated.rotation == 300
    assert rotated.x == pytest.approx(120)
    assert rotated.y == pytest.approx(46.6666666666667)
    assert annotation.rotation == 30


def test_page_rotation_preserves_arrow_endpoint_anchors(canvas):
    canvas.set_pages([Image.new("RGB", (800, 600), "white")])
    arrow = VectorAnnotation(AnnotationType.ARROW, 100, 150)
    arrow.rotation = 30
    canvas._page_objects[0] = [arrow]
    original_endpoints = arrow.endpoint_points_doc()
    canvas._page_rotations[0] = 90

    rotated = canvas.page_objects_with_rotation_at(0)[0]
    rotated_endpoints = rotated.endpoint_points_doc()
    expected = [
        canvas._transform_doc_coords_by_rotation(point.x(), point.y(), 90, 800, 600)
        for point in original_endpoints
    ]

    for actual, (expected_x, expected_y) in zip(rotated_endpoints, expected):
        assert (actual.x(), actual.y()) == pytest.approx((expected_x, expected_y))


def test_rotated_boundary_and_hit_testing_use_inverse_transform():
    signature = SignatureObject(Image.new("RGBA", (40, 20), "black"), "signature.png", 100, 100)
    signature.rotation = 90

    corners = signature.boundary_points_viewport(100, 100, 40, 20)
    assert [(point.x(), point.y()) for point in corners] == pytest.approx(
        [(130, 90), (130, 130), (110, 130), (110, 90)]
    )
    assert signature.hit_test_point(100, 100, 40, 20, QPointF(120, 125))
    assert not signature.hit_test_point(100, 100, 40, 20, QPointF(140, 110))


def test_composite_render_rotates_clockwise_without_moving_center():
    image = Image.new("RGBA", (40, 20), (255, 0, 0, 255))
    signature = SignatureObject(image, "signature.png", 100, 200)
    signature.rotation = 90

    overlay, x, y = signature.render_for_compositing()

    assert overlay.size == (20, 40)
    assert (x, y) == pytest.approx((110, 190))


def test_resizing_rotated_annotation_keeps_opposite_handle_fixed(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    annotation = VectorAnnotation(AnnotationType.CHECKMARK, 200, 200)
    annotation.rotation = 45
    canvas.add_object(annotation)
    old_anchor = annotation.boundary_points_viewport(
        annotation.x,
        annotation.y,
        annotation.scaled_width,
        annotation.scaled_height,
    )[0]
    dragged_handle = annotation.boundary_points_viewport(
        annotation.x,
        annotation.y,
        annotation.scaled_width,
        annotation.scaled_height,
    )[2]

    canvas._start_handle_drag(7, dragged_handle)
    canvas.mouseMoveEvent(_MouseMoveEvent(QPointF(
        dragged_handle.x() + 40,
        dragged_handle.y() + 40,
    )))

    new_anchor = annotation.boundary_points_viewport(
        annotation.x,
        annotation.y,
        annotation.scaled_width,
        annotation.scaled_height,
    )[0]
    assert (new_anchor.x(), new_anchor.y()) == pytest.approx(
        (old_anchor.x(), old_anchor.y())
    )


def test_rotation_handle_drag_snaps_by_default_and_shift_disables_it(canvas):
    canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    canvas._fit_scale = 1.0
    canvas._doc_offset_x = 0.0
    canvas._doc_offset_y = 0.0
    annotation = VectorAnnotation(AnnotationType.RECTANGLE, 200, 200)
    canvas.add_object(annotation)
    rect = canvas._object_view_rect(annotation)
    start = annotation.rotation_handle_center_viewport(
        rect.x(), rect.y(), rect.width(), rect.height()
    )
    pivot = rect.center()
    radius = 100.0

    canvas._start_rotation_drag(start)
    snapped_pointer_angle = math.radians(-68)
    canvas._apply_rotation_drag(QPointF(
        pivot.x() + math.cos(snapped_pointer_angle) * radius,
        pivot.y() + math.sin(snapped_pointer_angle) * radius,
    ), shift_pressed=False)
    assert annotation.rotation == 15

    annotation.rotation = 0
    canvas._start_rotation_drag(start)
    canvas._apply_rotation_drag(QPointF(
        pivot.x() + math.cos(snapped_pointer_angle) * radius,
        pivot.y() + math.sin(snapped_pointer_angle) * radius,
    ), shift_pressed=True)
    assert annotation.rotation == pytest.approx(22)


def test_angle_toolbar_edits_and_resets_selected_annotation(main_window):
    main_window.canvas.set_pages([Image.new("RGB", (500, 500), "white")])
    annotation = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    main_window.canvas.add_object(annotation)
    main_window.canvas.clear_history()

    assert main_window._angle_spinner.isVisible()
    assert main_window._angle_spinner.value() == 0

    main_window._angle_spinner.setValue(17)
    assert annotation.rotation == 17
    assert main_window.canvas.undo()
    assert annotation.rotation == 0

    main_window._angle_spinner.setValue(45)
    main_window._reset_angle_btn.click()
    assert annotation.rotation == 0


def test_angle_toolbar_is_hidden_without_selection(main_window):
    main_window.canvas.set_pages([Image.new("RGB", (500, 500), "white")])
    main_window.canvas.clear_selection()

    assert not main_window._angle_spinner.isVisible()
    assert not main_window._reset_angle_btn.isVisible()

# We must mock QPainter.begin/end globally for the print dialog test because
# the test patches QPrintDialog.exec to return Accepted without showing a
# real printer dialog. Without the mock, QPainter.begin() on the real QPrinter
# would return False (no printer available) and the print operation would fail
# early. However, a naive mock (return_value=True) would also affect QPainter
# instances used elsewhere (e.g., when rendering annotations to QImage in
# VectorAnnotation.render_to_pil()), causing a Qt abort because the painter
# would think it is active without being properly initialized. Therefore we
# install a conditional mock that returns True only for QPrinter devices and
# delegates to the original implementation for all other devices.

_original_qpainter_begin = QPainter.begin
_original_qpainter_end = QPainter.end


def _mock_printer_qpainter_begin(self, device):
    """Return True for the QPrinter used by print_document, but let real
    initialization happen for other devices (e.g. annotation QImages)."""
    if isinstance(device, QPrinter):
        return True
    else:
        return _original_qpainter_begin(self, device)


def _mock_printer_qpainter_end(self):
    """Do nothing for the QPrinter used by print_document, but let real
    ending happen for other devices (e.g. annotation QImages)."""
    if isinstance(self.device(), QPrinter):
        return
    else:
        return _original_qpainter_end(self)


def test_print_uses_rotated_page_and_annotation_geometry(main_window):
    main_window.canvas.set_pages([Image.new("RGB", (500, 400), "white")])
    annotation = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100)
    main_window.canvas.add_object(annotation)
    main_window.canvas._page_rotations[0] = 90

    with (
        patch.object(QPrintDialog, "exec", return_value=QDialog.Accepted),
        patch.object(QPainter, "begin", new=_mock_printer_qpainter_begin),
        patch.object(QPainter, "drawPixmap"),
        patch.object(QPainter, "end", new=_mock_printer_qpainter_end),
        # Real page metrics need an actual system printer/print backend, which
        # isn't guaranteed to exist on CI runners (esp. Windows without a
        # configured printer); fix the page size instead of querying it.
        patch.object(QPrinter, "pageRect", return_value=QRectF(0, 0, 595.0, 842.0)),
        patch.object(
            main_window.canvas,
            "get_page_image_with_rotation",
            wraps=main_window.canvas.get_page_image_with_rotation,
        ) as get_page,
        patch.object(
            main_window.canvas,
            "page_objects_with_rotation_at",
            wraps=main_window.canvas.page_objects_with_rotation_at,
        ) as get_objects,
    ):
        main_window.print_document()

    get_page.assert_called_once_with(0)
    get_objects.assert_called_once_with(0)
