from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AppSettings:
    last_signature_path: str | None = None
    last_open_document_path: str | None = None
    last_save_directory: str | None = None
    recent_signature_paths: list[str] = field(default_factory=list)


class SettingsStore:
    def __init__(self, app_name: str = "Signer") -> None:
        appdata = os.environ.get("APPDATA")
        if appdata:
            self._settings_path = Path(appdata) / app_name / "config.json"
        else:
            self._settings_path = Path.home() / ".signer" / "config.json"

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load(self) -> AppSettings:
        try:
            if not self._settings_path.exists():
                return AppSettings()
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return AppSettings(
                last_signature_path=data.get("last_signature_path"),
                last_open_document_path=data.get("last_open_document_path"),
                last_save_directory=data.get("last_save_directory"),
                recent_signature_paths=data.get("recent_signature_paths", []),
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
