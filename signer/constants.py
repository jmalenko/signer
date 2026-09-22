"""Shared application defaults."""

from __future__ import annotations

DEFAULT_COLOR: str = "#cc0000"
DEFAULT_LINE_WIDTH_PT: float = 1.5
DEFAULT_FONT_FAMILY: str = "Arial"
DEFAULT_TEXT_FONT_PT: int = 11

# Document is internally rendered at 300 DPI, PDF standard is 72 DPI.
# Converts between the two throughout rendering/export/geometry code.
DPI_SCALE: float = 300.0 / 72.0  # 4.16667

# v1.2.32: Discrete step lists for the `[` / `]` keyboard shortcuts, so each press
# jumps to a "usual" size rather than a small fixed increment.
FONT_SIZE_STEPS_PT: tuple[float, ...] = (
    6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 54, 60, 66, 72,
)
LINE_WIDTH_STEPS_PT: tuple[float, ...] = (
    0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16,
)

SUPPORTED_SIGNATURE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".ico"}
