"""Regression test for compositor edge-clamping (CODE_REVIEW_PLAN.md §3.3).

Bug: `_composite_objects()` clamped destination coordinates to `[0, pw-1]`/`[0, ph-1]`
instead of `[0, pw]`/`[0, ph]`. For an object placed fully past the page's right/bottom
edge (x >= pw or y >= ph, which normally can't happen once `clamp_to_page()` has run,
but can for hand-edited/legacy project data), the old clamp pulled it back onto the
canvas by one pixel, making a sliver of it incorrectly visible instead of leaving it
fully clipped off-page.
"""

from PIL import Image

from signer.compositor import _composite_objects


class _FakeObject:
    """Minimal duck-typed object with a solid-color overlay at a fixed position."""

    def __init__(self, x: float, y: float, size: int = 4) -> None:
        self.x = x
        self.y = y
        self._size = size

    def render_to_pil(self) -> Image.Image:
        return Image.new("RGBA", (self._size, self._size), (255, 0, 0, 255))


def test_object_fully_past_right_edge_does_not_bleed_onto_canvas():
    pw, ph = 20, 20
    background = (255, 255, 255, 255)
    base = Image.new("RGBA", (pw, ph), background)
    obj = _FakeObject(x=pw, y=0, size=4)  # left edge already at/past the right page boundary

    _composite_objects(base, [obj])

    assert base.getpixel((pw - 1, 0)) == background, "object past the edge must not bleed onto the last visible column"


def test_object_fully_past_bottom_edge_does_not_bleed_onto_canvas():
    pw, ph = 20, 20
    background = (255, 255, 255, 255)
    base = Image.new("RGBA", (pw, ph), background)
    obj = _FakeObject(x=0, y=ph, size=4)  # top edge already at/past the bottom page boundary

    _composite_objects(base, [obj])

    assert base.getpixel((0, ph - 1)) == background, "object past the edge must not bleed onto the last visible row"
