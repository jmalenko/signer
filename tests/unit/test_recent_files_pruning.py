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
        result = main_window._load_signature_file(missing)

    assert result is False
    assert missing not in main_window._settings.recent_signature_paths
    assert "/other/kept.png" in main_window._settings.recent_signature_paths


def test_load_signature_file_uses_default_centered_position(
    main_window, sample_pdf, sample_signature
):
    """Signatures use the same centered placement as every other annotation."""
    main_window.open_document(str(sample_pdf))

    result = main_window._load_signature_file(str(sample_signature))

    assert result is True
    obj = main_window.canvas.selected
    expected_x, expected_y = main_window.canvas.default_position_for(obj)
    assert obj.x == expected_x
    assert obj.y == expected_y
