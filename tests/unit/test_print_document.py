"""Tests for print_document(), covering the previously-untested QPrintDialog
interaction. Any test exercising this method MUST mock QPrintDialog.exec —
otherwise it opens a real modal dialog and hangs waiting for user input.
"""

from unittest.mock import patch

from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtWidgets import QDialog


class TestPrintDocument:
    def test_print_document_cancelled_does_nothing(self, main_window, sample_pdf):
        """Cancelling the print dialog should not touch the printer/painter."""
        main_window.open_document(str(sample_pdf))

        with patch.object(QPrintDialog, "exec", return_value=QDialog.Rejected):
            main_window.print_document()  # Should return early without raising.

    def test_print_document_accepted_does_not_crash(self, main_window, sample_pdf):
        """Accepting the print dialog should proceed without raising, even if
        the (headless test) printer backend can't actually render pages."""
        main_window.open_document(str(sample_pdf))

        with patch.object(QPrintDialog, "exec", return_value=QDialog.Accepted):
            main_window.print_document()  # Should not raise.

    def test_print_document_without_open_document_does_nothing(self, main_window):
        """No document open: should return early without showing the print dialog."""
        with patch.object(QPrintDialog, "exec") as mock_exec:
            main_window.print_document()

        assert not mock_exec.called
