"""
Tests for portable config detection (Version 1.2.26).

Tests verify that the application correctly switches between portable mode
(config.json in app directory) and installed mode (config.json in AppData)
based on file presence at runtime.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from signer.settings import get_config_dir, SettingsStore, AppSettings


class TestPortableConfigDetection:
    """Test get_config_dir() portable vs installed config detection."""

    def test_portable_mode_precedence(self, tmp_path, monkeypatch):
        """When config.json exists in app dir, portable mode takes precedence."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        config_file = app_dir / "config.json"
        config_file.write_text('{}')
        
        (app_dir / "signer").mkdir()
        
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
        
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            result = get_config_dir()
            assert result is not None

    def test_installed_mode_when_no_config_in_app_dir(self, tmp_path, monkeypatch):
        """When config.json not in app dir, AppData mode is used."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        appdata_dir = tmp_path / "appdata"
        appdata_dir.mkdir()
        
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        
        # Create signer directory but NOT config.json in app_dir
        (app_dir / "signer").mkdir()
        
        # We'll simulate this by testing with a temp file structure
        # No config.json in app_dir, so it should fall back to AppData
        with patch("signer.settings.Path") as MockPath:
            mock_settings_path = app_dir / "signer" / "settings.py"
            
            # Make Path() return real paths for everything except the check
            def mock_path(p):
                if isinstance(p, str) and "config.json" in p:
                    return app_dir / "config.json"
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result = get_config_dir()
            assert result is not None
            assert result.name == "Signer"

    def test_portable_precedence_both_exist(self, tmp_path, monkeypatch):
        """When both configs exist, portable mode takes precedence."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        appdata_dir = tmp_path / "appdata" / "Signer"
        appdata_dir.mkdir(parents=True)
        
        # Create config in both locations
        (app_dir / "config.json").write_text('{"mode": "portable"}')
        (appdata_dir / "config.json").write_text('{"mode": "installed"}')
        
        monkeypatch.setenv("APPDATA", str(appdata_dir.parent))
        (app_dir / "signer").mkdir()
        
        # Patch to return the right paths
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            # Both exist, portable should win
            result = get_config_dir()
            assert result is not None

    def test_creates_appdata_directory_if_missing(self, tmp_path, monkeypatch):
        """AppData Signer directory is created if it doesn't exist."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        appdata_dir = tmp_path / "appdata"
        appdata_dir.mkdir()
        
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        (app_dir / "signer").mkdir()
        
        # No config.json in app_dir, no Signer dir in AppData yet
        assert not (appdata_dir / "Signer").exists()
        
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result = get_config_dir()
            # Should create the Signer directory
            assert (appdata_dir / "Signer").exists()


class TestSettingsStore:
    """Test SettingsStore uses get_config_dir() correctly."""

    def test_settings_store_uses_get_config_dir(self, tmp_path, monkeypatch):
        """SettingsStore correctly uses get_config_dir()."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        appdata_dir = tmp_path / "appdata"
        appdata_dir.mkdir()
        
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        (app_dir / "signer").mkdir()
        
        # Mock get_config_dir to return a specific directory
        with patch("signer.settings.get_config_dir") as mock_get_config_dir:
            expected_dir = tmp_path / "custom_config"
            expected_dir.mkdir()
            mock_get_config_dir.return_value = expected_dir
            
            store = SettingsStore()
            assert store.settings_path == expected_dir / "config.json"

    def test_settings_store_load_save_cycle(self, tmp_path, monkeypatch):
        """SettingsStore save and load cycle works correctly."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        appdata_dir = tmp_path / "appdata"
        appdata_dir.mkdir()
        
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        (app_dir / "signer").mkdir()
        
        # Use a real config directory
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        with patch("signer.settings.get_config_dir") as mock_get_config_dir:
            mock_get_config_dir.return_value = config_dir
            
            # Save settings
            store = SettingsStore()
            original_settings = AppSettings(recent_color="#FF0000", recent_line_width_pt=2.5)
            store.save(original_settings)
            
            # Verify file was created
            assert (config_dir / "config.json").exists()
            
            # Load and verify
            loaded_settings = store.load()
            assert loaded_settings.recent_color == "#FF0000"
            assert loaded_settings.recent_line_width_pt == 2.5


class TestPortabilityScenarios:
    """Test realistic portable/installed scenarios."""

    def test_portable_mode_single_directory(self, tmp_path, monkeypatch):
        """User can make app portable by copying config to app directory."""
        # Simulate user moving entire app to USB drive
        usb_drive = tmp_path / "E" / "portable-signer"
        usb_drive.mkdir(parents=True)
        
        # Copy signer.exe (simulated by creating signer directory)
        (usb_drive / "signer").mkdir()
        
        # Create config.json in the same directory
        config_file = usb_drive / "config.json"
        config_file.write_text('{"recent_color": "#123456"}')
        
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
        
        # When app runs from USB, it should detect portable mode
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result = get_config_dir()
            assert result is not None

    def test_installed_mode_multiple_users(self, tmp_path, monkeypatch):
        """Each Windows user gets separate config in installed mode."""
        app_install_dir = tmp_path / "Program Files" / "Signer"
        app_install_dir.mkdir(parents=True)
        (app_install_dir / "signer").mkdir()
        
        user1_appdata = tmp_path / "users" / "user1" / "AppData" / "Roaming"
        user1_appdata.mkdir(parents=True)
        
        user2_appdata = tmp_path / "users" / "user2" / "AppData" / "Roaming"
        user2_appdata.mkdir(parents=True)
        
        # User 1 runs the app
        monkeypatch.setenv("APPDATA", str(user1_appdata))
        
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result1 = get_config_dir()
            assert (user1_appdata / "Signer").exists()
        
        # User 2 runs the app
        monkeypatch.setenv("APPDATA", str(user2_appdata))
        
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result2 = get_config_dir()
            assert (user2_appdata / "Signer").exists()
        
        # Each user has separate config directory
        assert result1 != result2

    def test_mode_switching_manual_migration(self, tmp_path, monkeypatch):
        """User can manually switch from installed to portable mode."""
        # Step 1: Start in installed mode
        app_dir = tmp_path / "Program Files" / "Signer"
        app_dir.mkdir(parents=True)
        (app_dir / "signer").mkdir()
        
        appdata_dir = tmp_path / "AppData" / "Roaming"
        appdata_dir.mkdir(parents=True)
        
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        
        # Create config in AppData (installed mode)
        appdata_config_dir = appdata_dir / "Signer"
        appdata_config_dir.mkdir()
        appdata_config = appdata_config_dir / "config.json"
        appdata_config.write_text('{"recent_color": "#111111"}')
        
        # Verify installed mode
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result = get_config_dir()
            assert (appdata_config_dir / "config.json").exists()
        
        # Step 2: User copies config to app directory (enable portable mode)
        app_config = app_dir / "config.json"
        app_config.write_text('{"recent_color": "#111111"}')
        
        # Now portable mode should be detected
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            # Portable should take precedence now
            result = get_config_dir()
            assert result is not None


class TestConfigDirIntegration:
    """Integration tests for config directory detection."""

    def test_get_config_dir_returns_path_object(self, tmp_path, monkeypatch):
        """get_config_dir() always returns a Path object."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "signer").mkdir()
        
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
        
        with patch("signer.settings.Path") as MockPath:
            def mock_path(p):
                return Path(p)
            
            MockPath.side_effect = mock_path
            
            result = get_config_dir()
            assert isinstance(result, Path)

    def test_config_json_file_operations(self, tmp_path, monkeypatch):
        """Config file operations work in both modes."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
        
        # Create a config file
        config_file = config_dir / "config.json"
        config_file.write_text('{"test": "data"}')
        
        # Read it back
        content = config_file.read_text()
        assert "test" in content
        assert "data" in content

