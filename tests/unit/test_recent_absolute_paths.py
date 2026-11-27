"""Bug: a file opened via a relative path (e.g. `-signature examples/sig.png` on the command
line) was stored in the recent lists as that relative path.

Steps: start from a folder with `-signature sig.png`, then open the same file through the file
dialog. Expected: one entry, with the absolute path. Actual: a relative entry (meaningless from
another working directory) next to the absolute one.
"""

import shutil
from pathlib import Path


def _relative_signature(tmp_path, sample_signature, monkeypatch):
    shutil.copy(sample_signature, tmp_path / "sig.png")
    monkeypatch.chdir(tmp_path)
    return "sig.png", str((tmp_path / "sig.png").absolute())


def _relative_document(tmp_path, sample_pdf, monkeypatch):
    shutil.copy(sample_pdf, tmp_path / "doc.pdf")
    monkeypatch.chdir(tmp_path)
    return "doc.pdf", str((tmp_path / "doc.pdf").absolute())


# ---- expected behavior (regression tests)

def test_relative_signature_path_is_recorded_as_absolute(main_window, tmp_path, sample_signature, monkeypatch):
    relative, absolute = _relative_signature(tmp_path, sample_signature, monkeypatch)

    main_window._load_signature_file(relative)

    assert main_window._settings.recent_signature_paths == [absolute]


def test_relative_and_absolute_signature_path_make_one_entry(main_window, tmp_path, sample_signature, monkeypatch):
    relative, absolute = _relative_signature(tmp_path, sample_signature, monkeypatch)

    main_window._load_signature_file(relative)
    main_window._load_signature_file(absolute)

    assert main_window._settings.recent_signature_paths == [absolute]


def test_relative_document_path_is_recorded_as_absolute(main_window, tmp_path, sample_pdf, monkeypatch):
    relative, absolute = _relative_document(tmp_path, sample_pdf, monkeypatch)

    main_window.open_document(relative)

    assert main_window._settings.recent_document_paths == [absolute]
