from signer.canvas import MAX_ZOOM, MIN_ZOOM


def _zoom_actions(main_window):
    return (
        main_window._toolbar_zoom_in_action,
        main_window._toolbar_zoom_out_action,
        main_window._toolbar_fit_to_window_action,
        main_window._menu_zoom_in_action,
        main_window._menu_zoom_out_action,
        main_window._menu_fit_to_window_action,
    )


def test_zoom_actions_at_fit_to_window_are_enabled_as_boundaries_require(
    main_window, sample_pdf
):
    assert main_window.open_document(str(sample_pdf))

    zoom_in, zoom_out, fit, menu_zoom_in, menu_zoom_out, menu_fit = _zoom_actions(main_window)

    assert zoom_in.isEnabled()
    assert not zoom_out.isEnabled()
    assert not fit.isEnabled()
    assert menu_zoom_in.isEnabled()
    assert not menu_zoom_out.isEnabled()
    assert not menu_fit.isEnabled()


def test_zoom_actions_at_intermediate_zoom_are_all_enabled(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    main_window.canvas._set_zoom(2.0)

    assert all(action.isEnabled() for action in _zoom_actions(main_window))


def test_zoom_in_is_disabled_at_maximum_zoom(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    main_window.canvas._set_zoom(MAX_ZOOM)

    zoom_in, zoom_out, fit, menu_zoom_in, menu_zoom_out, menu_fit = _zoom_actions(main_window)

    assert not zoom_in.isEnabled()
    assert zoom_out.isEnabled()
    assert fit.isEnabled()
    assert not menu_zoom_in.isEnabled()
    assert menu_zoom_out.isEnabled()
    assert menu_fit.isEnabled()


def test_zoom_out_and_fit_are_disabled_at_minimum_zoom_with_pan(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    main_window.canvas._set_zoom(MIN_ZOOM)
    main_window.canvas._pan_x = 10.0
    main_window.canvas._recompute_fit()
    main_window.canvas.zoomChanged.emit(main_window.canvas.zoom)

    zoom_in, zoom_out, fit, menu_zoom_in, menu_zoom_out, menu_fit = _zoom_actions(main_window)

    assert zoom_in.isEnabled()
    assert not zoom_out.isEnabled()
    assert fit.isEnabled()
    assert menu_zoom_in.isEnabled()
    assert not menu_zoom_out.isEnabled()
    assert menu_fit.isEnabled()
