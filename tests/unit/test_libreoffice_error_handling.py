"""Regression tests for LibreOfficeLoader subprocess error handling (CODE_REVIEW_PLAN.md §3.6)."""

import subprocess
from unittest.mock import patch

import pytest

from signer.document_loader import LibreOfficeLoader


def _loader_with_fake_executable():
    loader = LibreOfficeLoader()
    patch.object(loader, "_find_libreoffice", return_value="/fake/soffice").start()
    return loader


def test_libreoffice_timeout_raises_clear_value_error():
    loader = _loader_with_fake_executable()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=30)):
        with pytest.raises(ValueError, match="timed out"):
            loader.load("document.docx")


def test_libreoffice_conversion_failure_includes_file_path():
    loader = _loader_with_fake_executable()
    error = subprocess.CalledProcessError(1, "soffice", stderr=b"boom")
    with patch("subprocess.run", side_effect=error):
        with pytest.raises(ValueError, match="document.docx"):
            loader.load("document.docx")
