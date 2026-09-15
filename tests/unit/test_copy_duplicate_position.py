"""Regression tests for copy/paste and duplicate positioning."""

from PIL import Image

from signer.objects import AnnotationType, VectorAnnotation


def _copy_move_paste_and_duplicate(canvas):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white")])
    page_objects = canvas._page_objects.setdefault(0, [])

    copied = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    page_objects.append(copied)
    canvas.select_annotation(copied)
    canvas.copy_selected()
    canvas.move_selected(100, 100)
    canvas.paste_selected()
    pasted = canvas.current_page_objects()[-1]

    duplicate_source = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0)
    page_objects.append(duplicate_source)
    canvas.select_annotation(duplicate_source)
    canvas.duplicate_selected()
    duplicated = canvas.current_page_objects()[-1]

    return copied, pasted, duplicated


def test_paste_uses_copied_position_and_matches_duplicate_offset(canvas):
    copied, pasted, duplicated = _copy_move_paste_and_duplicate(canvas)

    assert (copied.x, copied.y) == (200, 200)
    assert (pasted.x, pasted.y) == (120, 120)
    assert (pasted.x, pasted.y) == (duplicated.x, duplicated.y)


def test_multi_duplicate_uses_same_offset(canvas):
    canvas.set_pages([Image.new("RGB", (800, 800), color="white")])
    originals = [
        VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, page=0),
        VectorAnnotation(AnnotationType.CROSSMARK, 200, 100, page=0),
    ]
    canvas._page_objects[0] = originals.copy()
    canvas.select_all_on_page()

    canvas.duplicate_selected()

    duplicates = canvas.current_page_objects()[2:]
    assert [(obj.x, obj.y) for obj in duplicates] == [(120, 120), (220, 120)]