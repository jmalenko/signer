"""On-screen selection-toolbar regressions.

These run for real in the default `pytest` run. They cannot share the main suite's
QApplication: the Qt platform plugin is process-wide and fixed at QApplication creation,
and the rest of the suite needs `offscreen`. Each test therefore drives a real window in a
subprocess started with the host's native platform plugin.

That matters because the offscreen platform does not reproduce these bugs at all: offscreen,
a control's sizeHint() happens to equal the width Qt later allocates inside the styled row,
and Qt honours a shrink below a stale minimum. Both differ on a real window server, which is
why TOOLBAR_ISSUES.md items were repeatedly marked fixed while still reproducing for users.

No user interaction is required: windows are driven programmatically, the unsaved-changes
dialog is bypassed via the existing test-mode flag, and the overflow popup is closed from a
timer.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve()
REPO_ROOT = MODULE.parents[2]
SWEEP_WIDTHS = range(1100, 399, -10)


def _native_platform():
    """The platform plugin that gives us a real window server, if one is available."""
    if sys.platform == "darwin":
        return "cocoa"
    if sys.platform.startswith("win"):
        return "windows"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "xcb"
    return None


NATIVE_PLATFORM = _native_platform()

needs_window_server = pytest.mark.skipif(
    NATIVE_PLATFORM is None,
    reason="headless host: no window server (set DISPLAY/WAYLAND_DISPLAY to enable)",
)


def _run_onscreen(scenario):
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = NATIVE_PLATFORM
    env["PYTHONPATH"] = str(REPO_ROOT)
    completed = subprocess.run(
        [sys.executable, str(MODULE), scenario],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if completed.returncode != 0:
        pytest.fail(
            f"on-screen scenario {scenario!r} failed\n"
            f"--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}"
        )


@needs_window_server
def test_controls_never_overlap_and_are_never_lost_while_resizing():
    """Issues 1, 9: no control may overlap the overflow button or the window edge, none may
    vanish without staying reachable, and the button tracks the overflow list exactly."""
    _run_onscreen("sweep")


@needs_window_server
def test_mode_switch_renders_identically_to_a_native_window():
    """Issues 5, 7: switching modes must leave no reserved space or painted strip behind."""
    _run_onscreen("mode-switch")


@needs_window_server
def test_overflow_popup_lists_hidden_controls_and_restores_them():
    """Issues 8, 9: the custom popup holds exactly the controls that left the row."""
    _run_onscreen("popup")


# --------------------------------------------------------------------------------------
# Subprocess side: everything below runs with a real platform plugin.
# --------------------------------------------------------------------------------------


def _build(overlay, tmp_path, select=True):
    from PySide6.QtWidgets import QApplication

    from signer.main_window import MainWindow
    from signer.objects import AnnotationType, VectorAnnotation
    from signer.settings import AppSettings, SettingsStore

    store = SettingsStore(app_name="SignerOnScreenTest")
    store._settings_path = tmp_path / "never-written.json"
    settings = AppSettings()
    settings.overlay_selection_toolbar = overlay

    window = MainWindow(settings_store=store, settings=settings)
    window._in_test_mode = True  # bypass the unsaved-changes dialog on close
    assert window.open_document(str(REPO_ROOT / "examples" / "document.pdf"))
    window.show()
    QApplication.processEvents()
    if select:
        annotation = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Onscreen")
        window.canvas.add_object(annotation)
        window.canvas.select_annotation(annotation)
        QApplication.processEvents()
    return window


def _row_widgets(row):
    from PySide6.QtWidgets import QWidgetAction

    return [a.defaultWidget() for a in row.actions() if isinstance(a, QWidgetAction)]


def _scenario_sweep(tmp_path):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication

    failures = []
    for overlay in (False, True):
        window = _build(overlay, tmp_path)
        container = window._canvas_container
        more = window._context_more_btn
        mode = "overlay" if overlay else "reserve"
        for width in SWEEP_WIDTHS:
            window.resize(width, 700)
            QApplication.processEvents()
            limit = more.geometry().left() if more.isVisible() else container.width()

            shown = set()
            for row in window._context_rows:
                if not row.isVisible():
                    continue
                for widget in _row_widgets(row):
                    if not widget.isVisible():
                        continue
                    shown.add(widget)
                    right = widget.mapTo(container, QPoint(widget.width(), 0)).x()
                    if right > limit or right > container.width():
                        failures.append(
                            f"{mode} w={width}: control right={right} exceeds "
                            f"limit={limit} container={container.width()}"
                        )

            overflow = set(window._context_overflow_items)
            for item in window._context_items:
                if item in window._context_conceptually_visible:
                    if item not in shown and item not in overflow:
                        failures.append(f"{mode} w={width}: a control vanished entirely")

            if more.isVisible() != bool(window._context_overflow_items):
                failures.append(
                    f"{mode} w={width}: overflow button visible={more.isVisible()} "
                    f"but overflow list holds {len(window._context_overflow_items)}"
                )
            if overlay and (more.isVisible() or window._context_overflow_items):
                failures.append(f"{mode} w={width}: overlay mode must not use the popup")
        window.close()
    return failures


def _scenario_mode_switch(tmp_path):
    from PySide6.QtWidgets import QApplication

    failures = []
    for target_overlay in (True, False):
        for select in (False, True):
            native = _build(target_overlay, tmp_path, select)
            native.resize(900, 700)
            QApplication.processEvents()
            expected_image = native.grab().toImage()
            expected_canvas = native.canvas.geometry()
            native.close()

            switched = _build(not target_overlay, tmp_path, select)
            switched.resize(900, 700)
            QApplication.processEvents()
            switched._toggle_overlay_selection_toolbar(target_overlay)
            QApplication.processEvents()
            actual_image = switched.grab().toImage()
            actual_canvas = switched.canvas.geometry()
            switched.close()

            label = f"to={'overlay' if target_overlay else 'reserve'} selected={select}"
            if actual_canvas != expected_canvas:
                failures.append(
                    f"{label}: canvas {actual_canvas.getRect()} != {expected_canvas.getRect()}"
                )
            if actual_image != expected_image:
                failures.append(f"{label}: stale toolbar strip after switching modes")
    return failures


def _scenario_popup(tmp_path):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QWidgetAction

    failures = []
    window = _build(False, tmp_path)
    window.resize(430, 700)
    QApplication.processEvents()

    expected = list(window._context_overflow_items)
    if not expected:
        window.close()
        return ["no controls overflowed at 430px, cannot exercise the popup"]

    seen = []

    def inspect():
        popup = QApplication.activePopupWidget()
        if popup is None:
            failures.append("overflow popup did not open")
            return
        seen.extend(
            a.defaultWidget() for a in popup.actions() if isinstance(a, QWidgetAction)
        )
        popup.close()

    QTimer.singleShot(0, inspect)
    window._show_context_overflow_menu()
    QApplication.processEvents()

    if seen != expected:
        failures.append(f"popup listed {len(seen)} controls, expected {len(expected)}")

    window.resize(431, 700)
    QApplication.processEvents()
    shown = {w for w in _row_widgets(window._context_row1) if w.isVisible()}
    overflow = set(window._context_overflow_items)
    for item in window._context_items:
        if item in window._context_conceptually_visible:
            if item not in shown and item not in overflow:
                failures.append("a control was lost after closing the popup")
    window.close()
    return failures


SCENARIOS = {
    "sweep": _scenario_sweep,
    "mode-switch": _scenario_mode_switch,
    "popup": _scenario_popup,
}


def _main():
    import tempfile

    from PySide6.QtWidgets import QApplication

    scenario = sys.argv[1]
    app = QApplication(sys.argv[:1])
    platform = app.platformName()
    if platform == "offscreen":
        print("refusing to run: offscreen cannot reproduce these bugs")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        failures = SCENARIOS[scenario](Path(tmp))
    print(f"scenario={scenario} platform={platform} failures={len(failures)}")
    for failure in failures[:20]:
        print(f"  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
