"""Exported files must follow the specification's format promises (spec §5.1): TIFF is LZW
compressed and every format carries the 300 DPI resolution, so a page keeps its physical size."""

import pymupdf
import pytest
from PIL import Image

from signer.compositor import (
    composite_objects_to_bmp,
    composite_objects_to_jpg,
    composite_objects_to_png,
    composite_pages_to_pdf,
    composite_pages_to_tiff,
)

A4_300_DPI = (2480, 3508)
TIFF_COMPRESSION_TAG = 259
TIFF_LZW = 5


@pytest.fixture
def page():
    return Image.new("RGB", A4_300_DPI, "white")


def test_tiff_is_lzw_compressed(page, tmp_path):
    path = tmp_path / "out.tiff"
    composite_pages_to_tiff([page, page], [[], []], path)
    with Image.open(path) as tiff:
        assert tiff.tag_v2[TIFF_COMPRESSION_TAG] == TIFF_LZW
        assert tiff.n_frames == 2


@pytest.mark.parametrize("name, export", [
    ("out.jpg", composite_objects_to_jpg),
    ("out.png", composite_objects_to_png),
    ("out.bmp", composite_objects_to_bmp),
])
def test_images_carry_300_dpi(page, tmp_path, name, export):
    path = tmp_path / name
    export(page, [], path)
    with Image.open(path) as image:
        assert image.info["dpi"] == pytest.approx((300, 300), abs=0.5)


def test_tiff_carries_300_dpi(page, tmp_path):
    path = tmp_path / "out.tiff"
    composite_pages_to_tiff([page], [[]], path)
    with Image.open(path) as tiff:
        assert tiff.info["dpi"] == pytest.approx((300, 300), abs=0.5)


def test_pdf_pages_keep_their_physical_size(page, tmp_path):
    path = tmp_path / "out.pdf"
    composite_pages_to_pdf([page], [[]], path)
    with pymupdf.open(path) as pdf:
        width_pt, height_pt = pdf[0].rect.width, pdf[0].rect.height
    assert (width_pt, height_pt) == pytest.approx((595, 842), abs=1.5)
