"""Regression tests for silent-failure review finding #6: `composite_objects_to_format()`
must not silently mis-encode an unhandled export format as JPG.
"""

import pytest
from PIL import Image

from signer.compositor import ExportFormat, composite_objects_to_format


def test_composite_objects_to_format_raises_for_single_file_formats(temp_dir):
    """Expected behavior: PDF/TIFF are multi-page, single-file formats with their own
    dedicated `composite_pages_to_pdf`/`composite_pages_to_tiff` functions and must
    never be silently written as JPG bytes by this per-page function.
    """
    page = Image.new("RGB", (100, 100), (255, 255, 255))

    with pytest.raises(ValueError):
        composite_objects_to_format(page, [], temp_dir / "out.pdf", ExportFormat.PDF)

