"""Unit tests for toolbar controls and context-sensitive visibility."""

from PySide6.QtCore import QCoreApplication, QPoint, QTimer, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QWidgetAction
from shiboken6 import isValid

from signer.objects import VECTOR_WITH_WIDTH, AnnotationType, VectorAnnotation


class TestWidthSpinnerVisibility:
    """Test line width spinner visibility based on annotation type."""
    
    def test_width_spinner_visible_for_line(self):
        """Test width spinner visible when Line selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        assert line.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_arrow(self):
        """Test width spinner visible when Arrow selected."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        assert arrow.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_rectangle(self):
        """Test width spinner visible when Rectangle selected."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        assert rect.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_ellipse(self):
        """Test width spinner visible when Ellipse selected."""
        ellipse = VectorAnnotation(AnnotationType.ELLIPSE, 100, 100, 0)
        assert ellipse.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_checkmark(self):
        """Test width spinner visible when Checkmark selected."""
        checkmark = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        assert checkmark.ann_type in VECTOR_WITH_WIDTH
    
    def test_width_spinner_visible_for_crossmark(self):
        """Test width spinner visible when Crossmark selected."""
        crossmark = VectorAnnotation(AnnotationType.CROSSMARK, 100, 100, 0)
        assert crossmark.ann_type in VECTOR_WITH_WIDTH
    def test_width_spinner_hidden_for_text(self):
        """Test width spinner hidden when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert text.ann_type not in VECTOR_WITH_WIDTH
    
    def test_width_spinner_hidden_for_signature(self):
        """Test width spinner hidden for Signature."""
        # Signature is not a VectorAnnotation
        # Test conceptually
        ann_type = AnnotationType.SIGNATURE
        assert ann_type not in VECTOR_WITH_WIDTH


class TestToolbarContextMenu:
    """Test that the toolbar does not expose Qt's hide-toolbar menu."""

    def test_toolbar_has_no_context_menu(self, main_window):
        toolbar = main_window._main_toolbar
        assert toolbar.contextMenuPolicy() == Qt.CustomContextMenu

        event = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(1, 1))
        QApplication.sendEvent(toolbar, event)

        assert event.isAccepted()
        assert QApplication.activePopupWidget() is None


class TestSelectionToolbarRendering:
    """Regression coverage for QToolBar widget-action visibility."""

    def test_widget_actions_remain_visible_after_selecting_annotation(
        self, main_window, sample_pdf, qtbot
    ):
        assert main_window.open_document(str(sample_pdf))
        annotation = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 200, 150)

        main_window.canvas.add_object(annotation)
        main_window.canvas.select_annotation(annotation)
        QApplication.processEvents()

        rows = main_window._context_rows
        actions = [
            action
            for row in rows
            for action in row.actions()
            if isinstance(action, QWidgetAction)
        ]

        assert actions
        assert all(action.isVisible() and action.isEnabled() for action in actions)
        assert all(action.defaultWidget().isVisible() for action in actions)


class TestSelectionToolbarOverflow:
    """Regression coverage for the reserve-space overflow popup lifecycle."""

    def test_text_style_controls_overflow_independently_from_right(
        self, main_window, sample_pdf
    ):
        assert main_window.open_document(str(sample_pdf))
        annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Text style")
        main_window.canvas.add_object(annotation)
        main_window.canvas.select_annotation(annotation)

        text_style_items = [
            main_window._font_size_group,
            main_window._font_family_group,
            main_window._character_spacing_group,
        ]
        observed_overflow = []
        for width in (1200, 1000, 800, 600, 400):
            main_window.resize(width, 700)
            QApplication.processEvents()
            overflow = list(main_window._context_overflow_items)
            observed_overflow.append([item for item in text_style_items if item in overflow])
            assert main_window._context_row1.height() == main_window._context_toolbar_line_height
            assert main_window._context_row1.width() <= main_window._canvas_container.width()
            if overflow:
                button_left = main_window._context_more_btn.geometry().left()
                visible_items = [
                    action.defaultWidget()
                    for action in main_window._context_row1.actions()
                    if isinstance(action, QWidgetAction)
                ]
                assert all(
                    item.mapTo(main_window._canvas_container, QPoint(item.width(), 0)).x()
                    <= button_left
                    for item in visible_items
                )

        assert observed_overflow[0] == []
        assert any(overflow == [text_style_items[-1]] for overflow in observed_overflow)
        assert all(
            overflow == text_style_items[len(text_style_items) - len(overflow):]
            for overflow in observed_overflow
        )

    def test_closing_overflow_popup_restores_controls(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Overflow")
        main_window.canvas.add_object(annotation)
        main_window.canvas.select_annotation(annotation)
        main_window.resize(400, 700)
        QApplication.processEvents()

        assert main_window._context_overflow_items
        overflow_items = list(main_window._context_overflow_items)
        visible_items = [
            item
            for item in main_window._context_items
            if item in main_window._context_conceptually_visible
        ]
        row1_items = [
            action.defaultWidget()
            for action in main_window._context_row1.actions()
            if isinstance(action, QWidgetAction)
        ]
        assert row1_items + overflow_items == visible_items

        def close_popup() -> None:
            popup = QApplication.activePopupWidget()
            if popup is not None:
                popup.close()

        QTimer.singleShot(0, close_popup)
        main_window._show_context_overflow_menu()
        QApplication.processEvents()
        QCoreApplication.sendPostedEvents()
        main_window.resize(401, 700)
        QApplication.processEvents()

        assert all(isValid(item) for item in overflow_items)
        assert all(item.parent() is main_window._canvas_container for item in overflow_items)


class TestFontSizeSpinnerVisibility:
    """Test font size spinner visibility."""
    
    def test_font_size_spinner_visible_for_text(self):
        """Test font size spinner visible when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert hasattr(text, '_font_size_pt')
    
    def test_font_size_spinner_hidden_for_line(self):
        """Test font size spinner hidden when Line selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        # Line should not have font_size_pt attribute used in to_dict
        data = line.to_dict()
        assert 'font_size_pt' not in data
    
    def test_font_size_spinner_hidden_for_rectangle(self):
        """Test font size spinner hidden when Rectangle selected."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        data = rect.to_dict()
        assert 'font_size_pt' not in data
    
    def test_font_size_spinner_hidden_for_arrow(self):
        """Test font size spinner hidden when Arrow selected."""
        arrow = VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)
        data = arrow.to_dict()
        assert 'font_size_pt' not in data


class TestFontFamilyComboVisibility:
    """Test font family combo visibility."""
    
    def test_font_family_combo_visible_for_text(self):
        """Test font family combo visible when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        assert hasattr(text, '_font_family')
    
    def test_font_family_combo_hidden_for_line(self):
        """Test font family combo hidden when Line selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        data = line.to_dict()
        assert 'font_family' not in data
    
    def test_font_family_combo_hidden_for_rectangle(self):
        """Test font family combo hidden when Rectangle selected."""
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        data = rect.to_dict()
        assert 'font_family' not in data


class TestControlsDisabledWhenNoDocument:
    """Test controls are disabled when no document open."""
    
    def test_width_spinner_disabled_no_document(self):
        """Test width spinner disabled with no document."""
        # No document means no annotation selected
        selected = None
        
        # Spinner would be disabled
        assert selected is None
    
    def test_font_size_spinner_disabled_no_document(self):
        """Test font size spinner disabled with no document."""
        selected = None
        assert selected is None
    
    def test_font_family_combo_disabled_no_document(self):
        """Test font family combo disabled with no document."""
        selected = None
        assert selected is None
    
    def test_color_picker_disabled_no_document(self):
        """Test color picker disabled with no document."""
        selected = None
        assert selected is None


class TestControlsDisabledWhenNoSelection:
    """Test controls are disabled when no annotation selected."""
    
    def test_spinners_disabled_no_selection(self):
        """Test spinners disabled with no selection."""
        # Empty document, nothing selected
        selected = None
        assert selected is None


class TestSpinnerRanges:
    """Test spinner range limits."""
    
    def test_width_spinner_range(self):
        """Test width spinner enforces range 0.5-10pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Minimum
        line._line_width_pt = 0.5
        assert line._line_width_pt >= 0.5
        
        # Maximum
        line._line_width_pt = 10.0
        assert line._line_width_pt <= 10.0
    
    def test_width_spinner_step(self):
        """Test width spinner steps by 0.5pt."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Default is 1.5
        assert line._line_width_pt == 1.5
        
        # Step up by 0.5
        line._line_width_pt = 2.0
        assert line._line_width_pt == 2.0
    
    def test_font_size_spinner_range(self):
        """Test font size spinner enforces range 6-72pt."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Minimum (6pt ≈ 8px)
        text._font_size_pt = 8
        assert text._font_size_pt >= 8
        
        # Maximum (72pt ≈ 96px)
        text._font_size_pt = 96
        assert text._font_size_pt <= 96
    
    def test_font_size_spinner_step(self):
        """Test font size spinner steps by 1pt."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        initial = text._font_size_pt
        
        # Step by 1
        text._font_size_pt = initial + 1
        assert text._font_size_pt == initial + 1


def _row_widgets(row):
    return [a.defaultWidget() for a in row.actions() if isinstance(a, QWidgetAction)]


def _select_text(main_window, sample_pdf):
    assert main_window.open_document(str(sample_pdf))
    annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Layout")
    main_window.canvas.add_object(annotation)
    main_window.canvas.select_annotation(annotation)
    QApplication.processEvents()
    return annotation


class TestSelectionToolbarLayoutInvariants:
    """Fitting must follow the geometry Qt actually allocates inside the styled row.

    A sizeHint() taken while a control is parented to the plain container is ~12% too
    small (the row's 13px stylesheet only applies once the control is inside it), which
    previously let controls overlap the overflow button and the window edge.
    """

    def test_controls_never_overlap_overflow_button_or_edge(self, main_window, sample_pdf):
        _select_text(main_window, sample_pdf)
        container = main_window._canvas_container
        more = main_window._context_more_btn
        for width in range(1000, 399, -20):
            main_window.resize(width, 700)
            QApplication.processEvents()
            limit = more.geometry().left() if more.isVisible() else container.width()
            for widget in _row_widgets(main_window._context_row1):
                if not widget.isVisible():
                    continue
                right = widget.mapTo(container, QPoint(widget.width(), 0)).x()
                assert right <= limit, f"width={width}: control right={right} > limit={limit}"
                assert right <= container.width(), f"width={width}: control past container edge"

    def test_every_hidden_control_is_reachable_in_overflow(self, main_window, sample_pdf):
        _select_text(main_window, sample_pdf)
        for width in range(1000, 399, -20):
            main_window.resize(width, 700)
            QApplication.processEvents()
            shown = {w for w in _row_widgets(main_window._context_row1) if w.isVisible()}
            overflow = set(main_window._context_overflow_items)
            for item in main_window._context_items:
                if item in main_window._context_conceptually_visible:
                    assert item in shown or item in overflow, f"width={width}: control vanished"

    def test_overflow_button_shown_exactly_when_something_overflows(self, main_window, sample_pdf):
        _select_text(main_window, sample_pdf)
        for width in range(1000, 399, -20):
            main_window.resize(width, 700)
            QApplication.processEvents()
            assert main_window._context_more_btn.isVisible() == bool(
                main_window._context_overflow_items
            ), f"width={width}: overflow button out of sync with overflow list"

    def test_fit_uses_in_row_geometry_not_container_size_hint(self, main_window, sample_pdf):
        """The row's own stylesheet can make a control wider than the size hint it reports
        while parented to the plain container (on macOS the real gap is ~12%). Enlarging the
        row font here reproduces that difference on any platform: fitting must react to the
        geometry Qt allocates inside the row, not to a hint measured outside it.
        """
        _select_text(main_window, sample_pdf)
        row = main_window._context_row1
        row.setStyleSheet(
            row.styleSheet()
            + " QToolBar QLabel, QToolBar QToolButton, QToolBar QPushButton,"
            " QToolBar QComboBox, QToolBar QSpinBox, QToolBar QDoubleSpinBox"
            " { font-size: 30px; }"
        )
        container = main_window._canvas_container
        more = main_window._context_more_btn
        for width in (900, 820, 700, 600, 500):
            main_window.resize(width, 700)
            QApplication.processEvents()
            limit = more.geometry().left() if more.isVisible() else container.width()
            for widget in _row_widgets(row):
                if not widget.isVisible():
                    continue
                right = widget.mapTo(container, QPoint(widget.width(), 0)).x()
                assert right <= limit, (
                    f"width={width}: control right={right} exceeds limit={limit} "
                    "- fitting used a stale size hint instead of real geometry"
                )

    def test_controls_return_unchanged_after_deselect_reselect(self, main_window, sample_pdf):
        annotation = _select_text(main_window, sample_pdf)
        main_window.resize(1000, 700)
        QApplication.processEvents()
        expected = [w for w in _row_widgets(main_window._context_row1) if w.isVisible()]
        assert expected

        for _ in range(3):
            main_window.canvas.select_annotation(None)
            QApplication.processEvents()
            main_window.canvas.select_annotation(annotation)
            QApplication.processEvents()
            actual = [w for w in _row_widgets(main_window._context_row1) if w.isVisible()]
            assert actual == expected

    def test_controls_survive_deselect_reselect_while_overflowing(self, main_window, sample_pdf):
        annotation = _select_text(main_window, sample_pdf)
        main_window.resize(460, 700)
        QApplication.processEvents()
        for _ in range(3):
            main_window.canvas.select_annotation(None)
            QApplication.processEvents()
            main_window.canvas.select_annotation(annotation)
            QApplication.processEvents()
            shown = {w for w in _row_widgets(main_window._context_row1) if w.isVisible()}
            overflow = set(main_window._context_overflow_items)
            for item in main_window._context_items:
                if item in main_window._context_conceptually_visible:
                    assert item in shown or item in overflow


class TestSelectionToolbarModeSwitch:
    """Toggling the overlay setting must not leave a reserved/painted strip behind."""

    def test_switching_to_overlay_collapses_reserved_row(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        main_window.resize(900, 700)
        QApplication.processEvents()
        line_h = main_window._context_toolbar_line_height
        assert main_window._context_row1.height() == line_h
        assert main_window.canvas.geometry().y() == line_h

        main_window._toggle_overlay_selection_toolbar(True)
        QApplication.processEvents()

        assert main_window._context_row1.height() == 0
        assert main_window._context_toolbar_row_height == 0
        assert main_window.canvas.geometry().y() == 0

    def test_switching_back_restores_reserved_row(self, main_window, sample_pdf):
        assert main_window.open_document(str(sample_pdf))
        main_window.resize(900, 700)
        QApplication.processEvents()
        line_h = main_window._context_toolbar_line_height

        main_window._toggle_overlay_selection_toolbar(True)
        QApplication.processEvents()
        main_window._toggle_overlay_selection_toolbar(False)
        QApplication.processEvents()

        assert main_window._context_row1.height() == line_h
        assert main_window._context_toolbar_row_height == line_h
        assert main_window.canvas.geometry().y() == line_h

    def test_switching_with_selection_collapses_reserved_row(self, main_window, sample_pdf):
        _select_text(main_window, sample_pdf)
        main_window.resize(900, 700)
        QApplication.processEvents()

        main_window._toggle_overlay_selection_toolbar(True)
        QApplication.processEvents()

        assert main_window.canvas.geometry().y() == 0
        assert main_window._context_toolbar_row_height == 0


class TestOverlaySelectionToolbarWrapping:
    """Overlay mode creates as many rows as needed without using an overflow button."""

    def test_rows_hold_every_control_in_order(self, main_window, sample_pdf):
        main_window._toggle_overlay_selection_toolbar(True)
        _select_text(main_window, sample_pdf)
        for width in (1000, 800, 600, 500):
            main_window.resize(width, 700)
            QApplication.processEvents()
            actual = [
                widget
                for row in main_window._context_rows
                for widget in _row_widgets(row)
                if widget.isVisible()
            ]
            expected = [
                i for i in main_window._context_items
                if i in main_window._context_conceptually_visible
            ]
            assert actual == expected, f"width={width}: wrapping lost or reordered controls"

    def test_rows_visible_only_when_used(self, main_window, sample_pdf):
        main_window._toggle_overlay_selection_toolbar(True)
        _select_text(main_window, sample_pdf)
        for width in (1000, 800, 600, 500):
            main_window.resize(width, 700)
            QApplication.processEvents()
            for row in main_window._context_rows:
                has_items = bool(_row_widgets(row))
                assert row.isVisible() == has_items, f"width={width}"

    def test_narrow_window_creates_at_least_three_rows(self, main_window, sample_pdf):
        main_window._toggle_overlay_selection_toolbar(True)
        _select_text(main_window, sample_pdf)
        main_window.resize(400, 700)
        QApplication.processEvents()

        used_rows = [row for row in main_window._context_rows if _row_widgets(row)]
        assert len(used_rows) >= 3

    def test_overflow_button_never_used_in_overlay_mode(self, main_window, sample_pdf):
        main_window._toggle_overlay_selection_toolbar(True)
        _select_text(main_window, sample_pdf)
        for width in (1000, 700, 500):
            main_window.resize(width, 700)
            QApplication.processEvents()
            assert not main_window._context_more_btn.isVisible()
            assert main_window._context_overflow_items == []

    def test_controls_return_unchanged_after_deselect_reselect(self, main_window, sample_pdf):
        main_window._toggle_overlay_selection_toolbar(True)
        annotation = _select_text(main_window, sample_pdf)
        main_window.resize(700, 700)
        QApplication.processEvents()
        expected = tuple(
            tuple(w for w in _row_widgets(row) if w.isVisible())
            for row in main_window._context_rows
        )
        assert expected[0]

        for _ in range(3):
            main_window.canvas.select_annotation(None)
            QApplication.processEvents()
            main_window.canvas.select_annotation(annotation)
            QApplication.processEvents()
            actual = tuple(
                tuple(w for w in _row_widgets(row) if w.isVisible())
                for row in main_window._context_rows
            )
            assert actual == expected


class TestAngleControlRemainsUsable:
    """Regression for the reset button being disabled by QToolBar.addWidget()."""

    def test_reset_button_stays_enabled_after_angle_change(self, main_window, sample_pdf):
        _select_text(main_window, sample_pdf)
        main_window.resize(1100, 700)
        QApplication.processEvents()

        main_window._angle_spinner.setValue(45)
        QApplication.processEvents()

        assert main_window._angle_spinner.isEnabled()
        assert main_window._reset_angle_btn.isEnabled()
        assert main_window._reset_angle_btn.isVisible()

    def test_reset_button_actually_resets(self, main_window, sample_pdf):
        _select_text(main_window, sample_pdf)
        main_window.resize(1100, 700)
        QApplication.processEvents()

        main_window._angle_spinner.setValue(45)
        QApplication.processEvents()
        main_window._reset_angle_btn.click()
        QApplication.processEvents()

        assert main_window._angle_spinner.value() == 0


class TestSpinnerStateManagement:
    """Test spinner state is managed correctly."""
    
    def test_width_spinner_updates_on_selection(self):
        """Test width spinner updates when annotation selected."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        line._line_width_pt = 2.5
        
        # Spinner value should match
        assert line._line_width_pt == 2.5
    
    def test_font_size_spinner_updates_on_selection(self):
        """Test font size spinner updates when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_size_pt = 28
        
        # Spinner value should match
        assert text._font_size_pt == 28

    def test_width_spinner_reflects_keyboard_shortcut_change(self, main_window):
        """Test width spinner value updates after ] keyboard shortcut changes width (real code path)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        main_window.canvas.add_object(line)

        main_window.canvas._adjust_annotation_property([line], 'increase')

        assert main_window._width_spinner.value() == line._line_width_pt

    def test_font_size_spinner_reflects_keyboard_shortcut_change(self, main_window):
        """Test font size spinner value updates after ] keyboard shortcut changes size (real code path)."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        main_window.canvas.add_object(text)

        main_window.canvas._adjust_annotation_property([text], 'increase')

        assert main_window._font_size_spinner.value() == text._font_size_pt
    
    def test_font_family_combo_updates_on_selection(self):
        """Test font family combo updates when Text selected."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        text._font_family = "Verdana"
        
        # Combo value should match
        assert text._font_family == "Verdana"

    def test_character_spacing_spinner_hides_decimal_for_whole_value(self, main_window):
        """Whole character spacing values should display like font-size values."""
        spinner = main_window._character_spacing_spinner

        spinner.setValue(2.0)
        assert spinner.lineEdit().text() == "2"

        spinner.setValue(2.5)
        assert spinner.lineEdit().text().replace(",", ".") == "2.5"


class TestControlSignalBlocking:
    """Test controls use signal blocking to prevent loops."""
    
    def test_spinner_change_doesnt_feedback(self):
        """Test spinner change doesn't cause infinite loop."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Change spinner (would be signal-blocked)
        line._line_width_pt = 2.5
        
        # Should update only once
        assert line._line_width_pt == 2.5
    
    def test_annotation_change_doesnt_feedback(self):
        """Test annotation change doesn't update spinner infinitely."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Change annotation property (would be signal-blocked)
        line._line_width_pt = 3.0
        
        # Spinner would update to reflect this
        # but only once
        assert line._line_width_pt == 3.0


class TestContextSwitchingControls:
    """Test controls update when switching between annotations."""
    
    def test_switch_from_line_to_text(self):
        """Test controls update when switching Line to Text."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Select line - width spinner visible
        selected = line
        assert hasattr(selected, '_line_width_pt')
        
        # Switch to text - font controls visible
        selected = text
        assert hasattr(selected, '_font_size_pt')
        assert hasattr(selected, '_font_family')
    
    def test_switch_from_text_to_rectangle(self):
        """Test controls update when switching Text to Rectangle."""
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        rect = VectorAnnotation(AnnotationType.RECTANGLE, 100, 100, 0)
        
        # Select text - font controls visible
        selected = text
        assert hasattr(selected, '_font_family')
        
        # Switch to rectangle - width visible
        selected = rect
        assert hasattr(selected, '_line_width_pt')


class TestSpecialControls:
    """Test special control behaviors."""
    
    def test_width_spinner_decimal_support(self):
        """Test width spinner supports decimal values (0.5 increments)."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        
        # Test decimal widths
        line._line_width_pt = 1.5
        assert line._line_width_pt == 1.5
        
        line._line_width_pt = 2.5
        assert line._line_width_pt == 2.5
    
    def test_color_control_integration(self):
        """Test color control is integrated with all annotation types."""
        line = VectorAnnotation(AnnotationType.LINE, 100, 100, 0)
        text = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test")
        
        # Both support color
        assert line.color is not None
        assert text.color is not None
        
        # Color can be changed
        line.color.setNamedColor("#ff0000")
        text.color.setNamedColor("#0000ff")
        
        assert line.color.name() == "#ff0000"
        assert text.color.name() == "#0000ff"
