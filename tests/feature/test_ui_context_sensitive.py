"""Feature tests for context-sensitive UI behavior (spec §2.3)."""

import pytest

from signer.objects import AnnotationType, VectorAnnotation

# Which toolbar controls each type shows (spec §2.3): color, width, font group, hand-drawn.
CONTROLS_PER_TYPE = {
    AnnotationType.CHECKMARK: dict(color=True, width=True, font=False, hand_drawn=True),
    AnnotationType.CROSSMARK: dict(color=True, width=True, font=False, hand_drawn=True),
    AnnotationType.LINE: dict(color=True, width=True, font=False, hand_drawn=True),
    AnnotationType.ARROW: dict(color=True, width=True, font=False, hand_drawn=True),
    AnnotationType.RECTANGLE: dict(color=True, width=True, font=False, hand_drawn=True),
    AnnotationType.ELLIPSE: dict(color=True, width=True, font=False, hand_drawn=True),
    AnnotationType.TEXT: dict(color=True, width=False, font=True, hand_drawn=False),
}


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    return main_window


class TestControlVisibilityPerType:
    """The selection-properties controls shown for each annotation type."""

    @pytest.mark.parametrize("ann_type", list(CONTROLS_PER_TYPE))
    def test_controls_shown_for_the_selected_type(self, window, ann_type):
        window.canvas.add_object(VectorAnnotation(ann_type, 100, 100, text="Test"))
        window._update_annotation_action_state()
        shown = window._context_conceptually_visible
        expected = CONTROLS_PER_TYPE[ann_type]

        assert (window._color_btn_action in shown or window._color_btn_action.isVisibleTo(window)) is expected["color"]
        assert (window._width_group in shown) is expected["width"]
        assert (window._font_size_group in shown) is expected["font"]
        assert (window._font_family_group in shown) is expected["font"]
        assert (window._character_spacing_group in shown) is expected["font"]
        assert (window._hand_drawn_btn in shown) is expected["hand_drawn"]
        assert window._angle_group in shown  # every type can be rotated


class TestControlsShowTheSelectedAnnotation:
    """Selecting an annotation puts its values into the controls, without editing it."""

    def test_width_spinner_shows_the_selected_line_width(self, window):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, line_width_pt=2.5)
        window.canvas.add_object(line)
        depth = len(window.canvas.history.undo_stack)

        window._update_annotation_action_state()

        assert window._width_spinner.value() == pytest.approx(2.5)
        assert len(window.canvas.history.undo_stack) == depth, "showing a value is not an edit"
        assert line._line_width_pt == 2.5

    def test_text_controls_show_the_selected_text(self, window):
        text = VectorAnnotation(
            AnnotationType.TEXT, 100, 100, text="Test", font_size_pt=32, character_spacing_pt=2.0
        )
        window.canvas.add_object(text)

        window._update_annotation_action_state()

        assert window._font_size_spinner.value() == 32
        assert window._character_spacing_spinner.value() == pytest.approx(2.0)

    def test_switching_the_selection_switches_the_controls(self, window):
        line = VectorAnnotation(AnnotationType.LINE, 100, 100)
        text = VectorAnnotation(AnnotationType.TEXT, 500, 500, text="Test")
        window.canvas.add_object(line)
        window.canvas.add_object(text)

        window.canvas.select_annotation(line)
        window._update_annotation_action_state()
        assert window._width_group in window._context_conceptually_visible
        assert window._font_size_group not in window._context_conceptually_visible

        window.canvas.select_annotation(text)
        window._update_annotation_action_state()
        assert window._font_size_group in window._context_conceptually_visible
        assert window._width_group not in window._context_conceptually_visible


class TestPropertyBounds:
    """The spinners limit what can be entered."""

    def test_width_spinner_range(self, window):
        assert window._width_spinner.minimum() == 0.5
        assert window._width_spinner.maximum() == 16.0

    def test_font_size_spinner_range(self, window):
        assert window._font_size_spinner.minimum() == 6
        assert window._font_size_spinner.maximum() == 72

    def test_a_value_beyond_the_range_is_clamped(self, window):
        window._width_spinner.setValue(99)
        assert window._width_spinner.value() == 16.0


class TestDocumentDependentWorkflowButtons:
    """Test document-dependent toolbar/menu control states."""

    def test_buttons_disabled_without_document(self, main_window):
        """Add Annotation and Save As are disabled when no document is open."""
        assert not main_window.canvas.has_document
        assert main_window._toolbar_add_annotation_btn is not None
        assert main_window._toolbar_save_as_action is not None
        assert main_window._menu_save_as_action is not None
        assert main_window._hamburger_annotations_menu is not None

        assert not main_window._toolbar_add_annotation_btn.isEnabled()
        assert not main_window._toolbar_save_as_action.isEnabled()
        assert not main_window._menu_save_as_action.isEnabled()
        assert not main_window._hamburger_annotations_menu.menuAction().isEnabled()

    def test_buttons_enabled_after_open_document(self, main_window, sample_pdf):
        """Add Annotation and Save As become enabled after opening a document."""
        assert main_window.open_document(str(sample_pdf))
        assert main_window.canvas.has_document

        assert main_window._toolbar_add_annotation_btn is not None
        assert main_window._toolbar_save_as_action is not None
        assert main_window._menu_save_as_action is not None
        assert main_window._hamburger_annotations_menu is not None

        assert main_window._toolbar_add_annotation_btn.isEnabled()
        assert main_window._toolbar_save_as_action.isEnabled()
        assert main_window._menu_save_as_action.isEnabled()
        assert main_window._hamburger_annotations_menu.menuAction().isEnabled()

    def test_page_navigation_hidden_for_single_page_document(self, main_window, sample_pdf):
        """Single-page documents should hide the toolbar page navigation controls."""
        assert main_window.open_document(str(sample_pdf))
        assert main_window.canvas.page_count == 1

        assert main_window._toolbar_page_nav_prev_action is not None
        assert main_window._toolbar_page_nav_next_action is not None
        assert main_window._toolbar_page_nav_label is not None
        assert main_window._toolbar_page_nav_prev_action.text() == "◀"
        assert main_window._toolbar_page_nav_next_action.text() == "▶"
        assert not main_window._toolbar_page_nav_prev_action.isVisible()
        assert not main_window._toolbar_page_nav_next_action.isVisible()
        assert not main_window._toolbar_page_nav_label.isVisible()
        assert main_window._toolbar_page_nav_label.width() == 12

    def test_page_navigation_field_jumps_to_entered_page(
        self, main_window, sample_multipage_pdf
    ):
        assert main_window.open_document(str(sample_multipage_pdf))
        assert main_window.canvas.page_count >= 2
        assert main_window._toolbar_page_nav_label.width() == 12 * len(
            str(main_window.canvas.page_count)
        )

        main_window._toolbar_page_nav_label.setText("2")
        main_window._toolbar_page_nav_label.returnPressed.emit()

        assert main_window.canvas.current_page == 1

    def test_page_navigation_field_rejects_out_of_range_page(
        self, main_window, sample_multipage_pdf
    ):
        assert main_window.open_document(str(sample_multipage_pdf))
        current_page = main_window.canvas.current_page

        main_window._toolbar_page_nav_label.setText(str(main_window.canvas.page_count + 1))
        main_window._toolbar_page_nav_label.returnPressed.emit()

        assert main_window.canvas.current_page == current_page
        assert main_window._toolbar_page_nav_label.text() == str(current_page + 1)

    def test_property_controls_hidden_when_no_selection(self, main_window, sample_pdf):
        """No selection should hide all annotation property controls even on a single-page document."""
        assert main_window.open_document(str(sample_pdf))
        assert main_window.canvas.page_count == 1
        assert main_window.canvas.selected is None

        main_window._update_annotation_action_state()

        assert not main_window._color_btn.isVisible()
        assert not main_window._width_spinner.isVisible()
        assert not main_window._width_label.isVisible()
        assert not main_window._font_size_spinner.isVisible()
        assert not main_window._font_size_label.isVisible()
        assert not main_window._font_family_combo.isVisible()
        assert not main_window._font_label.isVisible()
