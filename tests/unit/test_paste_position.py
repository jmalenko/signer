"""Test multi-selection copy/paste with move scenario."""
from PIL import Image

from signer.objects import DUPLICATE_OFFSET, AnnotationType, VectorAnnotation


def test_paste_preserves_original_position_after_move(canvas):
    """Paste uses copy-time coordinates after the source moves."""
    img1 = Image.new('RGB', (800, 800), color='white')
    img2 = Image.new('RGB', (800, 800), color='white')
    canvas.set_pages([img1, img2])

    ann = VectorAnnotation(
        AnnotationType.CHECKMARK,
        x=100,
        y=100,
        page=0
    )
    objs = canvas._page_objects.setdefault(0, [])
    objs.append(ann)
    canvas.select_annotation(ann)

    canvas.copy_selected()
    canvas.move_selected(100, 100)
    canvas.paste_selected()
    pasted_obj = objs[-1]

    assert len(objs) == 2, "Should have original and pasted annotations"
    assert pasted_obj.x == 100 + DUPLICATE_OFFSET
    assert pasted_obj.y == 100 + DUPLICATE_OFFSET
    assert (ann.x, ann.y) == (200, 200)


def test_paste_to_different_page_preserves_position(canvas):
    """Paste to another page uses copy-time coordinates without an offset."""
    img1 = Image.new('RGB', (800, 800), color='white')
    img2 = Image.new('RGB', (800, 800), color='white')
    canvas.set_pages([img1, img2])

    ann = VectorAnnotation(
        AnnotationType.CHECKMARK,
        x=100,
        y=100,
        page=0
    )
    objs0 = canvas._page_objects.setdefault(0, [])
    objs0.append(ann)
    canvas.select_annotation(ann)

    canvas.copy_selected()
    canvas.move_selected(100, 100)
    canvas.goto_page(1)
    objs1 = canvas._page_objects.setdefault(1, [])
    canvas.paste_selected()

    assert len(objs1) == 1
    pasted_ann = objs1[-1]
    assert (pasted_ann.x, pasted_ann.y) == (100, 100)
    assert pasted_ann.page == 1
