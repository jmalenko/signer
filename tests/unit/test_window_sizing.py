A4_ASPECT_RATIO = 210 / 297


def test_window_starts_with_a4_sized_canvas(main_window, qapp):
    qapp.processEvents()

    canvas_size = main_window.canvas.size()
    assert canvas_size.height() >= 640
    canvas_aspect_ratio = canvas_size.width() / canvas_size.height()
    assert abs(canvas_aspect_ratio - A4_ASPECT_RATIO) < 0.01

    initial_window_size = main_window.size()
    main_window._adjust_window_to_document(2481, 3509)
    qapp.processEvents()
    actual_window_size = main_window.size()
    assert actual_window_size == initial_window_size
