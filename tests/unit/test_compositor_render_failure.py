"""Regression tests for silent-failure review finding #5: a render failure for one
annotation during export must surface as an error, not be silently skipped while the
rest of the export "succeeds" with that annotation missing.
"""

import pytest
from PIL import Image

from signer.compositor import _composite_objects


class _BrokenObject:
    """Duck-typed object whose render always fails (e.g. a signature whose source
    image file is no longer available)."""

    def __init__(self, x: float = 0, y: float = 0) -> None:
        self.x = x
        self.y = y

    def render_to_pil(self) -> Image.Image:
        raise OSError("source image file not found")


def test_composite_objects_raises_on_render_failure():
    """Expected behavior: a broken annotation must abort compositing with an error."""
    base = Image.new("RGBA", (20, 20), (255, 255, 255, 255))

    with pytest.raises(RuntimeError):
        _composite_objects(base, [_BrokenObject()])
