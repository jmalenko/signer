"""Test overlay mode behavior during app startup, especially with document loading.

This test addresses a reported issue where space was being reserved for the
second toolbar row even when in overlay mode at startup.

See: v1.2.43 toolbar redesign bug fix
"""

import json
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from signer.main_window import MainWindow
from signer.settings import AppSettings, SettingsStore


def test_overlay_mode_no_space_reserved_at_startup(tmp_path, qtbot):
    """In overlay mode at startup, canvas should get full height (y=0) and row_height should be 0."""
    # Setup config to use overlay mode
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"overlay_selection_toolbar": True}))

    # Create a custom SettingsStore pointing to our temp config
    class TestSettingsStore(SettingsStore):
        def __init__(self):
            self._settings_path = config_file

    # Load settings from config
    store = TestSettingsStore()
    settings = store.load()
    assert settings.overlay_selection_toolbar is True, "Config should have overlay=True"

    # Create main window
    w = MainWindow(settings_store=store, settings=settings)
    qtbot.addWidget(w)
    w.resize(600, 700)
    w.show()

    # In overlay mode, _context_toolbar_row_height should be 0 (no space reserved)
    assert w._context_toolbar_row_height == 0, "row_height should be 0 in overlay mode at startup"
    assert w.canvas.geometry().y() == 0, "Canvas y should be 0 in overlay mode (rows float on top)"


def test_overlay_mode_no_space_after_document_load(tmp_path, qtbot):
    """After loading document+signature in overlay mode, canvas should still have no space reserved."""
    # Setup config to use overlay mode
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"overlay_selection_toolbar": True}))

    class TestSettingsStore(SettingsStore):
        def __init__(self):
            self._settings_path = config_file

    store = TestSettingsStore()
    settings = store.load()

    # Create and show window
    w = MainWindow(settings_store=store, settings=settings)
    qtbot.addWidget(w)
    w.resize(600, 700)
    w.show()

    # Get the actual document path
    doc_path = Path(__file__).parent.parent.parent / "examples" / "document.pdf"
    sig_path = Path(__file__).parent.parent.parent / "examples" / "signature.png"

    if doc_path.exists() and sig_path.exists():
        # Load document and signature
        w.open_document(str(doc_path))
        w._load_signature_file(str(sig_path))

        # After loading, canvas should still have no space reserved
        assert w._context_toolbar_row_height == 0, "row_height should stay 0 after document load"
        assert w.canvas.geometry().y() == 0, "Canvas y should stay 0 after document load in overlay mode"


def test_reserve_space_mode_reserves_space(tmp_path, qtbot):
    """In reserve-space mode, canvas should be positioned at y=44 (row1 height) with row_height=44."""
    # Setup config to use reserve-space mode (overlay=False)
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"overlay_selection_toolbar": False}))

    class TestSettingsStore(SettingsStore):
        def __init__(self):
            self._settings_path = config_file

    store = TestSettingsStore()
    settings = store.load()
    assert settings.overlay_selection_toolbar is False, "Config should have overlay=False"

    w = MainWindow(settings_store=store, settings=settings)
    qtbot.addWidget(w)
    w.resize(600, 700)
    w.show()

    # In reserve-space mode, _context_toolbar_row_height should be 44
    assert w._context_toolbar_row_height == 44, "row_height should be 44 in reserve-space mode"
    assert w.canvas.geometry().y() == 44, "Canvas y should be 44 in reserve-space mode (space reserved)"
