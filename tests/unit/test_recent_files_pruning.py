"""Regression test: recent document/signature entries that no longer exist on
disk should be pruned automatically instead of repeatedly showing the same
"file not found" error forever.
"""

from unittest.mock import patch


def test_open_document_prunes_stale_recent_entry(main_window, tmp_path):
    missing = str(tmp_path / "no-longer-there.pdf")
    main_window._settings.recent_document_paths = [missing, "/other/kept.pdf"]

    with patch("signer.main_window.QMessageBox.critical"):
        result = main_window.open_document(missing)

    assert result is False
    assert missing not in main_window._settings.recent_document_paths
    assert "/other/kept.pdf" in main_window._settings.recent_document_paths


def test_load_signature_file_prunes_stale_recent_entry(main_window, tmp_path):
    missing = str(tmp_path / "no-longer-there.png")
    main_window._settings.recent_signature_paths = [missing, "/other/kept.png"]

    with patch("signer.main_window.QMessageBox.warning"):
        result = main_window._load_signature_file(missing, at_default_position=True)

    assert result is False
    assert missing not in main_window._settings.recent_signature_paths
    assert "/other/kept.png" in main_window._settings.recent_signature_paths
