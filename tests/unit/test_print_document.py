"""Tests for print_document(), covering the previously-untested QPrintDialog
interaction. Any test exercising this method MUST mock QPrintDialog.exec —
otherwise it opens a real modal dialog and hangs waiting for user input.
"""

from unittest.mock import patch

from PySide6.QtGui import QPainter
from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtWidgets import QDialog


class TestPrintDocument:
    def test_print_document_cancelled_does_nothing(self, main_window, sample_pdf):
        """Cancelling the print dialog should not touch the printer/painter."""
        main_window.open_document(str(sample_pdf))

        with patch.object(QPrintDialog, "exec", return_value=QDialog.Rejected):
            main_window.print_document()  # Should return early without raising.

    def test_print_document_accepted_does_not_crash(self, main_window, sample_pdf):
        """An accepted dialog must not initialize a real printer in tests."""
        main_window.open_document(str(sample_pdf))

        with (
            patch.object(QPrintDialog, "exec", return_value=QDialog.Accepted),
            patch.object(QPainter, "begin", return_value=False) as begin,
        ):
            main_window.print_document()

        begin.assert_called_once()

    def test_print_document_without_open_document_does_nothing(self, main_window):
        """No document open: should return early without showing the print dialog."""
        with patch.object(QPrintDialog, "exec") as mock_exec:
            main_window.print_document()

        assert not mock_exec.called
