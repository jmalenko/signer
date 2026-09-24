"""Regression tests for systems where Qt discovers no fonts."""

from PySide6.QtGui import QFontDatabase

from signer.constants import DEFAULT_FONT_FAMILY
from signer.main_window import MainWindow
from signer.objects import AnnotationType, VectorAnnotation


def test_system_font_list_has_defaults_when_qt_finds_no_fonts(monkeypatch):
    monkeypatch.setattr(QFontDatabase, "families", lambda self: [])

    fonts = MainWindow._get_system_fonts()

    assert fonts
    assert DEFAULT_FONT_FAMILY in fonts


def test_font_combo_works_when_qt_finds_no_fonts(
    monkeypatch, qtbot, settings_store, app_settings
):
    monkeypatch.setattr(QFontDatabase, "families", lambda self: [])
    window = MainWindow(settings_store=settings_store, settings=app_settings)
    qtbot.addWidget(window)
    annotation = VectorAnnotation(AnnotationType.TEXT, 0, 0, text="Signer")
    window.canvas.add_object(annotation)

    window._font_family_combo.setCurrentText("Courier New")

    assert window._font_family_combo.count() > 0
    assert annotation._font_family == "Courier New"
