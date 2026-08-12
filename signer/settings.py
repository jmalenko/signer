from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AppSettings:
    # Recent color
    recent_color: str = "#cc0000"
    
    # Recent line width (for vector annotations)
    recent_line_width: float = 1.5
    
    # Recent font family and size
    recent_font_family: str = "Arial"
    recent_font_size_px: int = 48
    
    # LibreOffice path (for Word/ODT support)
    libreoffice_path: str | None = None
    
    # Signature/document paths
    last_signature_path: str | None = None
    last_open_document_path: str | None = None
    last_save_directory: str | None = None
    recent_signature_paths: list[str] = field(default_factory=list)
    recent_text_strings: list[str] = field(default_factory=list)
    recent_document_paths: list[str] = field(default_factory=list)


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
                # Recent color
                recent_color=data.get("recent_color", "#cc0000"),
                # Recent line width
                recent_line_width=data.get("recent_line_width", 1.5),
                # Recent font
                recent_font_family=data.get("recent_font_family", "Arial"),
                recent_font_size_px=data.get("recent_font_size_px", 48),
                # LibreOffice path
                libreoffice_path=data.get("libreoffice_path"),
                # Signature/document paths
                last_signature_path=data.get("last_signature_path"),
                last_open_document_path=data.get("last_open_document_path"),
                last_save_directory=data.get("last_save_directory"),
                recent_signature_paths=data.get("recent_signature_paths", []),
                recent_text_strings=data.get("recent_text_strings", []),
                recent_document_paths=data.get("recent_document_paths", []),
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")