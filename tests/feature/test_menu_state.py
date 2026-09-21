"""Feature tests for context-sensitive hamburger menu item enable/disable state (v1.2.29)."""

from PySide6.QtWidgets import QApplication

from signer.objects import AnnotationType, VectorAnnotation


def _clear_clipboard(window):
    QApplication.clipboard().clear()
    window.canvas._cached_copy_data = None


class TestMenuStateNoDocument:
    """No document open: all document-dependent menu items are disabled."""

    def test_print_disabled(self, main_window):
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._print_action.isEnabled()

    def test_undo_redo_disabled(self, main_window):
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_undo_action.isEnabled()
        assert not main_window._menu_redo_action.isEnabled()

    def test_cut_copy_duplicate_delete_disabled(self, main_window):
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_cut_action.isEnabled()
        assert not main_window._menu_copy_action.isEnabled()
        assert not main_window._menu_duplicate_action.isEnabled()
        assert not main_window._menu_delete_action.isEnabled()

    def test_paste_disabled(self, main_window):
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_paste_action.isEnabled()

    def test_select_all_disabled(self, main_window):
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_select_all_action.isEnabled()

    def test_rotate_actions_disabled(self, main_window):
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_rotate_page_left_action.isEnabled()
        assert not main_window._menu_rotate_page_right_action.isEnabled()
        assert not main_window._menu_rotate_all_left_action.isEnabled()
        assert not main_window._menu_rotate_all_right_action.isEnabled()


class TestMenuStateDocumentNoSelection:
    """Document open, nothing selected."""

    def test_print_and_rotate_enabled(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert main_window._print_action.isEnabled()
        assert main_window._menu_rotate_page_left_action.isEnabled()
        assert main_window._menu_rotate_page_right_action.isEnabled()
        assert main_window._menu_rotate_all_left_action.isEnabled()
        assert main_window._menu_rotate_all_right_action.isEnabled()

    def test_selection_dependent_actions_disabled(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_cut_action.isEnabled()
        assert not main_window._menu_copy_action.isEnabled()
        assert not main_window._menu_duplicate_action.isEnabled()
        assert not main_window._menu_delete_action.isEnabled()

    def test_select_all_disabled_when_no_annotations(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert not main_window._menu_select_all_action.isEnabled()


class TestMenuStateWithSelection:
    """Document open with an annotation selected."""

    def test_cut_copy_duplicate_delete_enabled(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        main_window.canvas._page_objects.setdefault(0, []).append(obj)
        main_window.canvas._selected = obj
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert main_window._menu_cut_action.isEnabled()
        assert main_window._menu_copy_action.isEnabled()
        assert main_window._menu_duplicate_action.isEnabled()
        assert main_window._menu_delete_action.isEnabled()

    def test_select_all_enabled_when_annotations_present(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        main_window.canvas._page_objects.setdefault(0, []).append(obj)
        _clear_clipboard(main_window)
        main_window._update_menu_state()
        assert main_window._menu_select_all_action.isEnabled()


class TestMenuStateUndoRedo:
    """Undo/Redo reflect history availability."""

    def test_undo_enabled_after_action(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        main_window._add_vector(AnnotationType.CHECKMARK)
        main_window._update_menu_state()
        assert main_window._menu_undo_action.isEnabled()

    def test_redo_enabled_after_undo(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        main_window._add_vector(AnnotationType.CHECKMARK)
        main_window.undo()
        assert main_window._menu_redo_action.isEnabled()


class TestMenuStatePaste:
    """Paste reflects clipboard/cached-copy availability."""

    def test_paste_enabled_after_copy(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        main_window.canvas._page_objects.setdefault(0, []).append(obj)
        main_window.canvas._selected = obj
        main_window.canvas.copy_selected()
        main_window._update_menu_state()
        assert main_window._menu_paste_action.isEnabled()
