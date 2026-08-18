from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .cli import parse_args
from .main_window import MainWindow
from .settings import SettingsStore

# Import recording setup (only used when SIGNER_RECORD_ACTIONS=1)
try:
    from tests.recording.action_recorder import setup_recording_if_enabled
except ImportError:
    setup_recording_if_enabled = None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    
    # Set application icon (prefer transparent PNG for UI consistency)
    resources_dir = Path(__file__).parent / "resources"
    icon_path = resources_dir / "signer-transparent.png"
    if not icon_path.exists():
        icon_path = resources_dir / "signer.png"
    if not icon_path.exists():
        icon_path = resources_dir / "signer.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    settings_store = SettingsStore(app_name="Signer")
    settings = settings_store.load()

    win = MainWindow(settings_store=settings_store, settings=settings)
    
    # Set up action recording if enabled via environment variable
    if setup_recording_if_enabled:
        setup_recording_if_enabled(win)
    
    win.show()
    win.run_startup_load(document=args.document, signature=args.signature)

    return app.exec()
