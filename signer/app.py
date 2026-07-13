from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .cli import parse_args
from .main_window import MainWindow
from .settings import SettingsStore


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])

    settings_store = SettingsStore(app_name="Signer")
    settings = settings_store.load()

    win = MainWindow(settings_store=settings_store, settings=settings)
    win.show()
    win.run_startup_load(document=args.document, signature=args.signature)

    return app.exec()
