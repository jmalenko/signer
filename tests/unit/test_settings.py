"""Unit tests for settings persistence."""

import json

import pytest

from signer.settings import AppSettings, SettingsStore


class TestAppSettings:
    """Tests for AppSettings dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        settings = AppSettings()
        
        assert settings.recent_color == "#cc0000"
        assert settings.recent_line_width_pt == 1.5
        assert settings.recent_font_family == "Arial"
        assert settings.recent_font_size_pt == 11
        assert settings.last_save_directory is None
        assert settings.recent_signature_paths == []
        assert settings.recent_text_strings == []
        assert settings.recent_document_paths == []
    
    def test_custom_values(self):
        """Test custom values."""
        settings = AppSettings(
            recent_color="#ff0000",
            recent_line_width_pt=2.0,
            recent_font_family="Times",
            recent_font_size_pt=36,
            last_save_directory="/output",
            recent_signature_paths=["/path/sig1.png", "/path/sig2.png"],
            recent_text_strings=["Text 1", "Text 2"],
            recent_document_paths=["/path/doc1.pdf"]
        )
        
        assert settings.recent_color == "#ff0000"
        assert settings.recent_line_width_pt == 2.0
        assert settings.recent_font_family == "Times"
        assert settings.recent_font_size_pt == 36
        assert settings.last_save_directory == "/output"
        assert settings.recent_signature_paths == ["/path/sig1.png", "/path/sig2.png"]
        assert settings.recent_text_strings == ["Text 1", "Text 2"]
        assert settings.recent_document_paths == ["/path/doc1.pdf"]
    
    def test_asdict(self):
        """Test conversion to dictionary."""
        settings = AppSettings(recent_color="#ff0000")
        data = settings.__dict__
        
        assert data["recent_color"] == "#ff0000"
        assert "recent_line_width_pt" in data
        assert "recent_signature_paths" in data

    def test_asdict_does_not_include_duplicate_image_paths(self):
        """Recent image paths use the unified signature paths setting."""
        data = AppSettings().__dict__

        assert "recent_image_paths" not in data


class TestSettingsStore:
    """Tests for SettingsStore."""
    
    def test_load_no_file(self, temp_dir):
        """Test loading when config file doesn't exist."""
        config_path = temp_dir / "nonexistent.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        assert isinstance(settings, AppSettings)
        assert settings.recent_color == "#cc0000"
    
    def test_save_creates_directory(self, temp_dir):
        """Test save creates parent directories."""
        config_path = temp_dir / "subdir" / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = AppSettings(recent_color="#ff0000")
        store.save(settings)
        
        assert config_path.exists()
        assert config_path.parent.exists()
    
    def test_save_load_roundtrip(self, temp_dir):
        """Test save and load roundtrip."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        original = AppSettings(
            recent_color="#ff0000",
            recent_line_width_pt=2.0,
            recent_font_family="Times",
            recent_font_size_pt=11,
            last_save_directory="/output",
            recent_signature_paths=["/path/sig1.png", "/path/sig2.png"],
            recent_text_strings=["Text 1", "Text 2"],
            recent_document_paths=["/path/doc1.pdf"]
        )
        
        store.save(original)
        loaded = store.load()
        
        assert loaded.recent_color == original.recent_color
        assert loaded.recent_line_width_pt == original.recent_line_width_pt
        assert loaded.recent_font_family == original.recent_font_family
        assert loaded.recent_font_size_pt == original.recent_font_size_pt
        assert loaded.last_save_directory == original.last_save_directory
        assert loaded.recent_signature_paths == original.recent_signature_paths
        assert loaded.recent_text_strings == original.recent_text_strings
        assert loaded.recent_document_paths == original.recent_document_paths
    
    def test_load_corrupted_json(self, temp_dir):
        """Test loading corrupted JSON returns defaults."""
        config_path = temp_dir / "config.json"
        config_path.write_text("not valid json")
        
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        assert isinstance(settings, AppSettings)
        assert settings.recent_color == "#cc0000"
    
    def test_load_partial_json(self, temp_dir):
        """Test loading partial JSON uses defaults for missing keys."""
        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps({"recent_color": "#ff0000"}))
        
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        assert settings.recent_color == "#ff0000"
        assert settings.recent_line_width_pt == 1.5  # default
        assert settings.recent_font_family == "Arial"  # default
    
    def test_load_extra_keys_ignored(self, temp_dir):
        """Test loading JSON with extra keys ignores them."""
        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps({
            "recent_color": "#ff0000",
            "unknown_key": "should be ignored"
        }))
        
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        assert settings.recent_color == "#ff0000"
        assert not hasattr(settings, "unknown_key")

    def test_config_json_uses_snake_case_keys(self, temp_dir):
        """config.json is a user-facing/hand-editable file and uses snake_case keys
        per REQUIREMENTS.md, matching the AppSettings field names."""
        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps({
            "libreoffice_path": "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
            "last_export_format": "png",
            "last_export_folder": "/exports",
            "last_jpeg_quality": 80,
            "last_pdf_image_quality": 70,
            "recent_document_paths": ["/path/doc1.pdf"],
        }))

        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path

        settings = store.load()

        assert settings.libreoffice_path == "C:\\Program Files\\LibreOffice\\program\\soffice.exe"
        assert settings.last_export_format == "png"
        assert settings.last_export_folder == "/exports"
        assert settings.last_jpeg_quality == 80
        assert settings.last_pdf_image_quality == 70
        assert settings.recent_document_paths == ["/path/doc1.pdf"]

    def test_save_writes_snake_case_keys(self, temp_dir):
        """Saving writes snake_case JSON keys, matching what load() reads back."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path

        store.save(AppSettings(libreoffice_path="/opt/libreoffice/soffice"))

        data = json.loads(config_path.read_text())
        assert data["libreoffice_path"] == "/opt/libreoffice/soffice"

    def test_settings_path_property(self, temp_dir):
        """Test settings_path property."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        assert store.settings_path == config_path
    
    def test_multiple_save_load_cycles(self, temp_dir):
        """Test multiple save/load cycles."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = AppSettings(recent_color="#ff0000")
        
        for i in range(5):
            store.save(settings)
            loaded = store.load()
            assert loaded.recent_color == "#ff0000"
            settings = loaded  # Use loaded for next iteration
    
    def test_unicode_paths(self, temp_dir):
        """Test handling of unicode paths."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = AppSettings(
            recent_document_paths=["/path/文档.pdf", "/path/документ.pdf"]
        )
        
        store.save(settings)
        loaded = store.load()
        
        assert loaded.recent_document_paths == ["/path/文档.pdf", "/path/документ.pdf"]


class TestRecentListsManagement:
    """Tests for recent lists LRU management."""
    
    def test_recent_signature_paths_lru(self):
        """Test recent signature paths LRU behavior."""
        settings = AppSettings()
        
        # Add paths
        paths = [f"/path/sig{i}.png" for i in range(15)]
        for path in paths:
            if path in settings.recent_signature_paths:
                settings.recent_signature_paths.remove(path)
            settings.recent_signature_paths.insert(0, path)
            settings.recent_signature_paths = settings.recent_signature_paths[:10]
        
        assert len(settings.recent_signature_paths) == 10
        # Most recent first
        assert settings.recent_signature_paths[0] == "/path/sig14.png"
        assert settings.recent_signature_paths[-1] == "/path/sig5.png"
        # Oldest dropped
        assert "/path/sig0.png" not in settings.recent_signature_paths
        assert "/path/sig4.png" not in settings.recent_signature_paths
    
    def test_recent_text_strings_lru(self):
        """Test recent text strings LRU behavior."""
        settings = AppSettings()
        
        texts = [f"Text {i}" for i in range(15)]
        for text in texts:
            if text in settings.recent_text_strings:
                settings.recent_text_strings.remove(text)
            settings.recent_text_strings.insert(0, text)
            settings.recent_text_strings = settings.recent_text_strings[:10]
        
        assert len(settings.recent_text_strings) == 10
        assert settings.recent_text_strings[0] == "Text 14"
        assert settings.recent_text_strings[-1] == "Text 5"
    
    def test_recent_document_paths_lru(self):
        """Test recent document paths LRU behavior."""
        settings = AppSettings()
        
        paths = [f"/path/doc{i}.pdf" for i in range(15)]
        for path in paths:
            if path in settings.recent_document_paths:
                settings.recent_document_paths.remove(path)
            settings.recent_document_paths.insert(0, path)
            settings.recent_document_paths = settings.recent_document_paths[:10]
        
        assert len(settings.recent_document_paths) == 10
        assert settings.recent_document_paths[0] == "/path/doc14.pdf"
        assert settings.recent_document_paths[-1] == "/path/doc5.pdf"
    
    def test_duplicate_removal_in_recent(self):
        """Test that adding duplicate moves to front."""
        settings = AppSettings()
        
        settings.recent_signature_paths = ["/path/a.png", "/path/b.png", "/path/c.png"]
        
        # Add b again - should move to front
        path = "/path/b.png"
        if path in settings.recent_signature_paths:
            settings.recent_signature_paths.remove(path)
        settings.recent_signature_paths.insert(0, path)
        
        assert settings.recent_signature_paths == ["/path/b.png", "/path/a.png", "/path/c.png"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])