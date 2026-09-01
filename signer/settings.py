from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# Default settings constants - single source of truth
DEFAULT_COLOR: str = "#cc0000"
DEFAULT_LINE_WIDTH_PT: float = 1.5
DEFAULT_FONT_FAMILY: str = "Arial"
DEFAULT_FONT_SIZE_PT: int = 11


def get_config_dir(app_name: str = "Signer") -> Path:
    """
    Determine config directory based on deployment mode.
    
    - Portable mode: config.json exists in application directory
    - Installed mode: config.json in %APPDATA%/Signer/ (default)
    
    Returns the directory where config.json should be stored.
    """
    # Get the application directory (where signer.exe/main.py lives)
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable: sys.executable is signer.exe
        app_dir = Path(sys.executable).parent
    else:
        # Running from source: __file__ is signer/settings.py, parent.parent gets project root
        app_dir = Path(__file__).parent.parent
    
    # Check if config.json exists in app directory (portable mode)
    if (app_dir / "config.json").exists():
        return app_dir
    
    # Fall back to AppData (installed mode)
    appdata = os.environ.get("APPDATA")
    if appdata:
        config_dir = Path(appdata) / app_name
    else:
        # Fallback if APPDATA not available (shouldn't happen on Windows)
        config_dir = Path.home() / f".{app_name.lower()}"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

@dataclass
class AppSettings:
    # Recent color (hex format: #rrggbb)
    recent_color: str = DEFAULT_COLOR
    
    # Recent line width for vector annotations (points) - default 1.5pt per requirements
    recent_line_width_pt: float = DEFAULT_LINE_WIDTH_PT

    # Recent font family (font name string)
    recent_font_family: str = DEFAULT_FONT_FAMILY
    # Recent font size (points) - default 11pt per requirements
    recent_font_size_pt: int = DEFAULT_FONT_SIZE_PT
    
    # LibreOffice path (for Word/ODT support)
    libreoffice_path: str | None = None

    # Signature/document paths (file paths or None if not set)
    last_signature_path: str | None = None
    last_open_document_path: str | None = None
    last_save_directory: str | None = None
    last_export_format: str = "jpg"  # Default export format
    last_export_folder: str | None = None  # Last used export folder
    
    # Export quality settings (for lossy formats only)
    last_jpeg_quality: int = 95  # JPG quality 1-100
    last_pdf_image_quality: int = 95  # PDF image quality 1-100
    
    # Recent lists (LRU, max 10 items each)
    recent_signature_paths: list[str] = field(default_factory=list)
    recent_text_strings: list[str] = field(default_factory=list)
    recent_document_paths: list[str] = field(default_factory=list)
    recent_image_paths: list[str] = field(default_factory=list)  # v1.2.22: Recent images (max 10)


class SettingsStore:
    def __init__(self, app_name: str = "Signer") -> None:
        config_dir = get_config_dir(app_name)
        self._settings_path = config_dir / "config.json"

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load(self) -> AppSettings:
        try:
            if not self._settings_path.exists():
                return AppSettings()
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return AppSettings(
                # Recent color (hex: #rrggbb)
                recent_color=data.get("recent_color", DEFAULT_COLOR),
                # Recent line width (points)
                recent_line_width_pt=data.get("recent_line_width_pt", DEFAULT_LINE_WIDTH_PT),
                # Recent font (name string)
                recent_font_family=data.get("recent_font_family", DEFAULT_FONT_FAMILY),
                # Recent font size (points)
                recent_font_size_pt=data.get("recent_font_size_pt", DEFAULT_FONT_SIZE_PT),
                # LibreOffice path
                libreoffice_path=data.get("libreoffice_path"),
                # File paths (str or None)
                last_signature_path=data.get("last_signature_path"),
                last_open_document_path=data.get("last_open_document_path"),
                last_save_directory=data.get("last_save_directory"),
                last_export_format=data.get("last_export_format", "jpg"),
                last_export_folder=data.get("last_export_folder"),
                # Export quality settings
                last_jpeg_quality=data.get("last_jpeg_quality", 95),
                last_pdf_image_quality=data.get("last_pdf_image_quality", 95),
                # Recent lists (LRU, max 10 items)
                recent_signature_paths=data.get("recent_signature_paths", []),
                recent_text_strings=data.get("recent_text_strings", []),
                recent_document_paths=data.get("recent_document_paths", []),
                recent_image_paths=data.get("recent_image_paths", []),  # v1.2.22
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")