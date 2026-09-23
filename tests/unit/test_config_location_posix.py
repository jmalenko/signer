"""Portable-vs-installed config mode tests for macOS and Linux.

`test_portable_config.py` covers the same behaviour on Windows only (its skipif
is correct — it asserts `%APPDATA%` semantics). These tests cover the other two
platforms so config-location resolution isn't left unverified wherever the suite
actually runs.

See CODE_REVIEW_PLAN.md section D3.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from signer.settings import SettingsStore, get_config_dir


@pytest.fixture
def app_dir_without_config(tmp_path, monkeypatch):
    """Point get_config_dir()'s app-directory probe at an empty temp directory."""
    app_dir = tmp_path / "app"
    (app_dir / "signer").mkdir(parents=True)
    monkeypatch.setattr("signer.settings.__file__", str(app_dir / "signer" / "settings.py"))
    return app_dir


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


class TestInstalledModeLocation:
    def test_macos_uses_application_support(self, app_dir_without_config, fake_home):
        with patch("signer.settings.sys.platform", "darwin"):
            config_dir = get_config_dir("SignerTest")

        assert config_dir == fake_home / "Library" / "Application Support" / "SignerTest"
        assert config_dir.is_dir(), "the directory must be created"

    def test_linux_uses_dot_config(self, app_dir_without_config, fake_home):
        with patch("signer.settings.sys.platform", "linux"):
            config_dir = get_config_dir("SignerTest")

        assert config_dir == fake_home / ".config" / "SignerTest"
        assert config_dir.is_dir(), "the directory must be created"

    def test_unknown_unix_platform_falls_back_to_dot_config(self, app_dir_without_config, fake_home):
        with patch("signer.settings.sys.platform", "freebsd13"):
            config_dir = get_config_dir("SignerTest")

        assert config_dir == fake_home / ".config" / "SignerTest"


class TestPortableModePrecedence:
    @pytest.mark.parametrize("platform", ["darwin", "linux"])
    def test_config_next_to_the_app_wins(self, tmp_path, monkeypatch, fake_home, platform):
        app_dir = tmp_path / "app"
        (app_dir / "signer").mkdir(parents=True)
        (app_dir / "config.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr("signer.settings.__file__", str(app_dir / "signer" / "settings.py"))

        with patch("signer.settings.sys.platform", platform):
            config_dir = get_config_dir("SignerTest")

        assert config_dir == app_dir
        assert not (fake_home / ".config" / "SignerTest").exists()
        assert not (fake_home / "Library").exists()

    @pytest.mark.parametrize("platform", ["darwin", "linux"])
    def test_frozen_app_probes_next_to_the_executable(self, tmp_path, monkeypatch, fake_home, platform):
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "config.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr("signer.settings.sys.executable", str(bundle_dir / "signer"))

        with patch("signer.settings.is_frozen", return_value=True), \
             patch("signer.settings.sys.platform", platform):
            config_dir = get_config_dir("SignerTest")

        assert config_dir == bundle_dir


class TestSettingsRoundTripOnThisPlatform:
    def test_saved_settings_are_read_back(self, tmp_path):
        store = SettingsStore(app_name="SignerTest")
        store._settings_path = tmp_path / "config.json"
        settings = store.load()
        settings.recent_color = "#123456"
        settings.recent_font_size_pt = 23

        store.save(settings)
        reloaded = SettingsStore(app_name="SignerTest")
        reloaded._settings_path = store._settings_path

        assert reloaded.load().recent_color == "#123456"
        assert reloaded.load().recent_font_size_pt == 23

    def test_unreadable_config_falls_back_to_defaults_and_logs(self, tmp_path, caplog):
        store = SettingsStore(app_name="SignerTest")
        store._settings_path = tmp_path / "config.json"
        store._settings_path.write_text("{not json", encoding="utf-8")

        with caplog.at_level("WARNING"):
            settings = store.load()

        assert settings.recent_color
        assert any("falling back to defaults" in r.message for r in caplog.records)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX home-directory layout")
def test_real_platform_config_dir_is_under_home(tmp_path, monkeypatch, app_dir_without_config, fake_home):
    """Sanity check with the real sys.platform of the machine running the suite."""
    config_dir = get_config_dir("SignerTest")

    assert fake_home in config_dir.parents
