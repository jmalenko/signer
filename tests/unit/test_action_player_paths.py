from pathlib import Path

from tests.recording.action_player import normalize_recorded_path


def test_normalize_recorded_path_accepts_windows_separators():
    assert normalize_recorded_path(r"examples\document1.pdf") == "examples/document1.pdf"


def test_normalize_recorded_path_preserves_posix_paths():
    path = "/tmp/examples/document1.pdf"
    assert normalize_recorded_path(path) == path


def test_normalize_recorded_path_accepts_path_objects():
    assert normalize_recorded_path(Path("examples/document1.pdf")) == "examples/document1.pdf"