"""Regression tests for undo/redo correctness bugs found during code review.

See CODE_REVIEW_PLAN.md sections 0, 1.1, 1.2, 1.3, 1.4 for the detailed analysis.
"""

from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


def _setup_page(canvas):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white")])


def test_drag_after_delete_undoes_the_correct_object(canvas):
    """§1.1: add A, add B, delete A, drag B, undo the drag -> B moves back, A stays deleted."""
    _setup_page(canvas)
    a = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    b = VectorAnnotation(AnnotationType.CROSSMARK, 200, 200, page=0)
    canvas.add_object(a)
    canvas.add_object(b)

    canvas.select_annotation(a)
    canvas.remove_selected()
    assert canvas.current_page_objects() == [b]

    # Simulate a drag of B by directly recording a move action the way
    # mouseMoveEvent does (full-format action using the stable id helper).
    from signer.history import MoveAnnotationAction

    obj_id = canvas._stable_id_for(b)
    b.x, b.y = 300, 300
    action = MoveAnnotationAction(object_id=obj_id, from_x=200, from_y=200, to_x=300, to_y=300)
    canvas.history.record_action(action)

    canvas.undo()

    assert (b.x, b.y) == (200, 200), "B should move back to its pre-drag position"
    assert canvas.current_page_objects() == [b], "A must stay deleted"


def test_multi_delete_is_a_single_undo_unit(canvas):
    """§1.2: deleting 3 selected annotations and pressing undo once restores all 3."""
    _setup_page(canvas)
    objs = [
        VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0),
        VectorAnnotation(AnnotationType.CROSSMARK, 200, 100, page=0),
        VectorAnnotation(AnnotationType.LINE, 300, 100, page=0),
    ]
    canvas._page_objects[0] = objs.copy()
    canvas.select_all_on_page()

    canvas.delete_selected()
    assert canvas.current_page_objects() == []

    undone = canvas.undo()
    assert undone is True
    assert len(canvas.current_page_objects()) == 3
    assert not canvas.can_undo(), "a single undo should have restored all 3 objects"

    redone = canvas.redo()
    assert redone is True
    assert canvas.current_page_objects() == []
    assert not canvas.can_redo(), "a single redo should have removed all 3 objects again"


def test_multi_duplicate_is_a_single_undo_unit(canvas):
    """§1.3: duplicating 2 selected annotations and pressing undo once removes both duplicates."""
    _setup_page(canvas)
    objs = [
        VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0),
        VectorAnnotation(AnnotationType.CROSSMARK, 200, 100, page=0),
    ]
    canvas._page_objects[0] = objs.copy()
    canvas.select_all_on_page()

    canvas.duplicate_selected()
    assert len(canvas.current_page_objects()) == 4

    undone = canvas.undo()
    assert undone is True
    assert len(canvas.current_page_objects()) == 2, "a single undo should remove both duplicates"
    assert not canvas.can_undo()


def test_paste_action_undo_removes_only_pasted_objects():
    """§1.4: PasteAnnotationAction.undo() must remove exactly the objects it
    pasted, not merely the last N objects currently in the page's list.

    Reproduces the scenario where something else appends an object to the
    page after the paste (e.g. a restore/redo path) without that append
    being the most-recently-recorded history entry.
    """
    from unittest.mock import Mock

    from signer.history import PasteAnnotationAction

    a = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    b = VectorAnnotation(AnnotationType.CROSSMARK, 200, 100, page=0)
    unrelated = VectorAnnotation(AnnotationType.LINE, 400, 400, page=0)

    page_objects = [a, b]
    canvas = Mock()
    canvas.current_page_objects.return_value = page_objects

    action = PasteAnnotationAction(pasted_objects_data=[a.to_dict(), b.to_dict()])
    action._pasted_objects = [a, b]

    # An object shows up in the list after the paste without being the most
    # recent history entry (e.g. appended by unrelated code).
    page_objects.append(unrelated)

    action.undo(canvas)

    assert page_objects == [unrelated], "only the pasted objects should be removed"
