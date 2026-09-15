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
    
    # Fall back to platform-specific config directory (installed mode)
    if sys.platform == "win32":
        config_dir = Path(os.environ["APPDATA"]) / app_name
    elif sys.platform == "darwin":
        # macOS uses ~/Library/Application Support/
        config_dir = Path.home() / "Library" / "Application Support" / app_name
    else:
        # Linux and other Unix-like systems
        config_dir = Path.home() / ".config" / app_name
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

    # Last save location and export preferences
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
            kwargs = {
                field_name: data[field_name]
                for field_name in AppSettings.__dataclass_fields__
                if field_name in data
            }
            return AppSettings(**kwargs)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")