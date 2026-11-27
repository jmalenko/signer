"""The main toolbar row is always complete (spec §2.1): its minimum width includes the zoom
controls and the hamburger menu, and selecting an annotation does not add a separator to it."""

import pytest


@pytest.fixture
def window(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    main_window.show()
    return main_window


def test_nothing_of_the_main_row_is_pushed_out_at_the_minimum_width(window, qapp):
    window.resize(window.minimumWidth(), window.height())
    qapp.processEvents()
    toolbar = window._main_toolbar
    for action in (
        window._toolbar_zoom_out_action, window._toolbar_fit_to_window_action,
        window._toolbar_zoom_in_action,
    ):
        widget = toolbar.widgetForAction(action)
        assert widget.isVisibleTo(window)
        assert widget.geometry().right() <= toolbar.width()
    hamburger = toolbar.widgetForAction(toolbar.actions()[-1])
    assert hamburger.isVisibleTo(window) and hamburger.geometry().right() <= toolbar.width()


def test_selecting_an_annotation_does_not_add_a_separator_on_a_single_page_document(window):
    from signer.objects import AnnotationType, VectorAnnotation

    assert window.canvas.page_count == 1
    window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 100, 100))
    window._update_annotation_action_state()

    assert not window._toolbar_page_nav_separator_action.isVisible()
