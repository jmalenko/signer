"""The pages and the number of copies chosen in the print dialog are honored (spec §12)."""

import pytest
from PySide6.QtPrintSupport import QPrinter

from signer.main_window import pages_to_print


def test_all_pages_in_order():
    assert pages_to_print(4, QPrinter.AllPages, 0, 0, 1, current_page=0) == [0, 1, 2, 3]


def test_a_page_range_uses_the_one_based_numbers_of_the_dialog():
    assert pages_to_print(5, QPrinter.PageRange, 2, 4, 1, current_page=0) == [1, 2, 3]


def test_a_range_beyond_the_document_is_cut_to_it():
    assert pages_to_print(3, QPrinter.PageRange, 2, 9, 1, current_page=0) == [1, 2]


def test_the_current_page_only():
    assert pages_to_print(5, QPrinter.CurrentPage, 0, 0, 1, current_page=3) == [3]


def test_copies_repeat_the_sequence():
    assert pages_to_print(3, QPrinter.PageRange, 1, 2, 2, current_page=0) == [0, 1, 0, 1]
