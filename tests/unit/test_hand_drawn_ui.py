"""Hand-drawn style: toolbar toggle, canvas operation, undo/redo and new-annotation default."""

from PIL import Image

from signer.history import ChangeHandDrawnAction
from signer.objects import AnnotationType, VectorAnnotation


def open_page(main_window):
    main_window.canvas.set_pages([Image.new("RGB", (1000, 1000), "white")])
    main_window.canvas.clear_history()


def add(main_window, ann_type, **kwargs):
    annotation = VectorAnnotation(ann_type, 100, 100, **kwargs)
    main_window.canvas.add_object(annotation)
    return annotation


class TestCanvasOperation:
    def test_toggle_is_undoable_and_redoable(self, main_window):
        open_page(main_window)
        rectangle = add(main_window, AnnotationType.RECTANGLE)

        main_window.canvas.set_hand_drawn_selected(True)
        assert rectangle.hand_drawn is True

        assert main_window.canvas.undo()
        assert rectangle.hand_drawn is False
        assert main_window.canvas.redo()
        assert rectangle.hand_drawn is True

    def test_toggling_keeps_the_same_look(self, main_window):
        open_page(main_window)
        ellipse = add(main_window, AnnotationType.ELLIPSE)
        seed = ellipse.hand_drawn_seed
        main_window.canvas.set_hand_drawn_selected(True)
        main_window.canvas.set_hand_drawn_selected(False)
        main_window.canvas.set_hand_drawn_selected(True)
        assert ellipse.hand_drawn_seed == seed

    def test_multi_selection_is_one_undo_entry_and_skips_unsupported(self, main_window):
        open_page(main_window)
        line = add(main_window, AnnotationType.LINE)
        arrow = add(main_window, AnnotationType.ARROW)
        text = add(main_window, AnnotationType.TEXT, text="Hello")
        main_window.canvas.select_all_on_page()
        main_window.canvas.clear_history()

        main_window.canvas.set_hand_drawn_selected(True)
        assert line.hand_drawn and arrow.hand_drawn
        assert text.hand_drawn is False

        assert main_window.canvas.undo()
        assert not line.hand_drawn and not arrow.hand_drawn
        assert not main_window.canvas.undo()

    def test_no_history_entry_when_nothing_changes(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.LINE, hand_drawn=True)
        main_window.canvas.clear_history()
        main_window.canvas.set_hand_drawn_selected(True)
        assert not main_window.canvas.undo()

    def test_action_serializes_with_previous_value(self):
        action = ChangeHandDrawnAction(object_id=3, hand_drawn=True, from_hand_drawn=False)
        assert action.data == {"hand_drawn": True, "object_id": 3, "from_hand_drawn": False}
        restored = ChangeHandDrawnAction.from_data(action.data)
        assert restored.data == action.data


class TestToolbarToggle:
    def test_hidden_without_selection_and_for_text(self, main_window):
        open_page(main_window)
        main_window.canvas.clear_selection()
        assert not main_window._hand_drawn_btn.isVisible()

        add(main_window, AnnotationType.TEXT, text="Hello")
        assert not main_window._hand_drawn_btn.isVisible()

    def test_visible_for_every_stroke_type(self, main_window):
        main_window.resize(1400, 700)
        open_page(main_window)
        for ann_type in (
            AnnotationType.CHECKMARK, AnnotationType.CROSSMARK, AnnotationType.LINE,
            AnnotationType.ARROW, AnnotationType.RECTANGLE, AnnotationType.ELLIPSE,
        ):
            add(main_window, ann_type)
            assert main_window._hand_drawn_btn.isVisible(), ann_type

    def test_visible_when_only_some_of_a_multi_selection_support_it(self, main_window):
        main_window.resize(1400, 700)
        open_page(main_window)
        add(main_window, AnnotationType.TEXT, text="Hello")
        add(main_window, AnnotationType.LINE)
        main_window.canvas.select_all_on_page()
        assert main_window._hand_drawn_btn.isVisible()

    def test_shows_the_selected_annotations_value(self, main_window):
        main_window.resize(1400, 700)
        open_page(main_window)
        add(main_window, AnnotationType.LINE, hand_drawn=True)
        assert main_window._hand_drawn_btn.isChecked()
        add(main_window, AnnotationType.RECTANGLE)
        assert not main_window._hand_drawn_btn.isChecked()

    def test_clicking_applies_to_selection_and_is_remembered(self, main_window):
        main_window.resize(1400, 700)
        open_page(main_window)
        rectangle = add(main_window, AnnotationType.RECTANGLE)

        main_window._hand_drawn_btn.click()
        assert rectangle.hand_drawn is True
        assert main_window._settings.recent_hand_drawn is True

        main_window._hand_drawn_btn.click()
        assert rectangle.hand_drawn is False
        assert main_window._settings.recent_hand_drawn is False


class TestNewAnnotationDefault:
    def test_new_annotations_start_off_by_default(self, main_window):
        open_page(main_window)
        main_window._add_vector(AnnotationType.LINE)
        assert main_window.canvas.selected.hand_drawn is False

    def test_new_annotations_use_the_last_used_value(self, main_window):
        main_window.resize(1400, 700)
        open_page(main_window)
        main_window._add_vector(AnnotationType.LINE)
        main_window._hand_drawn_btn.click()

        main_window._add_vector(AnnotationType.ELLIPSE)
        assert main_window.canvas.selected.hand_drawn is True

        main_window._hand_drawn_btn.click()
        main_window._add_vector(AnnotationType.ARROW)
        assert main_window.canvas.selected.hand_drawn is False

    def test_text_is_not_affected_by_the_last_used_value(self, main_window):
        open_page(main_window)
        main_window._settings.recent_hand_drawn = True
        main_window._add_text_annotation("Hello")
        assert main_window.canvas.selected.hand_drawn is False


class TestDefaultFromDocument:
    """A new annotation follows the document's existing annotations before the last-used value."""

    def test_no_supporting_annotation_uses_last_used_value(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.TEXT, text="Hello")
        assert main_window.canvas.hand_drawn_default(last_used=True) is True
        assert main_window.canvas.hand_drawn_default(last_used=False) is False

    def test_all_hand_drawn_gives_hand_drawn_even_if_last_used_is_off(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.LINE, hand_drawn=True)
        add(main_window, AnnotationType.ELLIPSE, hand_drawn=True)
        assert main_window.canvas.hand_drawn_default(last_used=False) is True

    def test_mixed_gives_not_hand_drawn_even_if_last_used_is_on(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.LINE, hand_drawn=True)
        add(main_window, AnnotationType.ELLIPSE)
        assert main_window.canvas.hand_drawn_default(last_used=True) is False

    def test_none_hand_drawn_gives_not_hand_drawn(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.LINE)
        assert main_window.canvas.hand_drawn_default(last_used=True) is False

    def test_text_annotations_are_ignored(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.LINE, hand_drawn=True)
        add(main_window, AnnotationType.TEXT, text="Hello")
        assert main_window.canvas.hand_drawn_default(last_used=False) is True

    def test_annotations_on_other_pages_count(self, main_window):
        main_window.canvas.set_pages([Image.new("RGB", (1000, 1000), "white")] * 2)
        main_window.canvas.clear_history()
        add(main_window, AnnotationType.LINE, hand_drawn=True)
        main_window.canvas.goto_page(1)
        assert main_window.canvas.hand_drawn_default(last_used=False) is True
        add(main_window, AnnotationType.RECTANGLE)
        main_window.canvas.goto_page(0)
        assert main_window.canvas.hand_drawn_default(last_used=True) is False

    def test_add_follows_the_document_not_the_last_used_value(self, main_window):
        """E.g. after opening a project whose annotations are all hand-drawn."""
        open_page(main_window)
        main_window._settings.recent_hand_drawn = False
        add(main_window, AnnotationType.ARROW, hand_drawn=True)
        main_window._add_vector(AnnotationType.ELLIPSE)
        assert main_window.canvas.selected.hand_drawn is True

        main_window._settings.recent_hand_drawn = True
        main_window.canvas.set_hand_drawn_selected(False)
        main_window._add_vector(AnnotationType.LINE)
        assert main_window.canvas.selected.hand_drawn is False

    def test_duplicate_keeps_its_own_value(self, main_window):
        open_page(main_window)
        add(main_window, AnnotationType.LINE)
        add(main_window, AnnotationType.ELLIPSE, hand_drawn=True)
        assert main_window.canvas.selected.duplicate().hand_drawn is True


def test_setting_round_trips_through_the_config_file(settings_store, app_settings):
    app_settings.recent_hand_drawn = True
    settings_store.save(app_settings)
    assert settings_store.load().recent_hand_drawn is True
