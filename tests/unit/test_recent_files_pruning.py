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


def test_load_signature_file_uses_signature_default_position(main_window, sample_pdf, sample_signature):
    """Regression test (silent-failure review finding #3): loading a signature via
    the Signature submenu ("From file...", recent files - at_default_position=False)
    must use the 80%-down-the-page position documented in
    FUNCTIONAL_SPECIFICATION.md #7.7, not the generic center-of-page position used
    for other annotation types.
    """
    main_window.open_document(str(sample_pdf))

    result = main_window._load_signature_file(str(sample_signature), at_default_position=False)

    assert result is True
    obj = main_window.canvas.selected
    expected_x, expected_y = main_window.canvas.default_signature_position_for(obj)
    assert obj.x == expected_x
    assert obj.y == expected_y
