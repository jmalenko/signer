"""Tests for the bug where a signature loaded via the command line appears
selected (its boundary is drawn) but keyboard actions (Delete, arrow-key
move, etc.) don't reach it because the window/canvas never explicitly
requests real activation and keyboard focus after the CLI startup load.
"""

from unittest.mock import patch

from signer.canvas import DocumentCanvas
from signer.main_window import MainWindow


def _run_startup_load(main_window, qapp, document, signature):
    main_window.run_startup_load(document=str(document), signature=str(signature))
    for _ in range(5):
        qapp.processEvents()


class TestCliSignatureSelection:
    def test_signature_loaded_from_cli_gets_keyboard_focus(
        self, qapp, main_window, sample_pdf, sample_signature
    ):
        """Expected behavior: after a CLI startup load, the window is
        activated and the canvas is given keyboard focus so the
        newly-selected signature can actually be manipulated (deleted,
        moved, etc.), not just shown as selected."""
        with patch.object(MainWindow, "raise_", autospec=True) as mock_raise, \
             patch.object(MainWindow, "activateWindow", autospec=True) as mock_activate, \
             patch.object(DocumentCanvas, "setFocus", autospec=True) as mock_set_focus:
            _run_startup_load(main_window, qapp, sample_pdf, sample_signature)

        assert main_window.canvas.selected is not None
        assert mock_raise.called
        assert mock_activate.called
        assert mock_set_focus.called
