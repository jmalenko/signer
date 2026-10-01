import subprocess

import pytest

from signer.release_version import get_release_version


def _git(repository, *args: str) -> None:
    git_command = ["git", *args]
    subprocess.run(
        git_command, cwd=repository, check=True, capture_output=True
    )


def _commit(repository, message: str) -> None:
    _git(str(repository), "add", "--all")
    _git(str(repository), "commit", "-m", message)


def _initialize_repository(repository) -> None:
    _git(str(repository), "init", "-b", "main")
    _git(str(repository), "config", "user.name", "Release test")
    _git(
        str(repository), "config", "user.email", "release-test@example.invalid"
    )
    (repository / "REQUIREMENTS.md").write_text(
        "## Version 1.2.45 - Previous requirement\n"
        "\n## Version 1.3 - New requirement\n",
        encoding="utf-8",
    )
    (repository / "change.txt").write_text("requirement", encoding="utf-8")
    _commit(repository, "Add 1.3 requirement")


def test_release_version_uses_latest_requirement_and_commit_count(
    tmp_path,
) -> None:
    _initialize_repository(tmp_path)

    assert get_release_version(tmp_path) == "1.3.0"

    (tmp_path / "REQUIREMENTS.md").write_text(
        "## Version 1.2.45 - Previous requirement\n"
        "\n## Version 1.3 - Revised requirement title\n",
        encoding="utf-8",
    )
    _commit(tmp_path, "Clarify requirement title")
    assert get_release_version(tmp_path) == "1.3.1"

    _git(str(tmp_path), "switch", "-c", "feature")
    (tmp_path / "feature-one.txt").write_text("first", encoding="utf-8")
    _commit(tmp_path, "First feature commit")
    (tmp_path / "feature-two.txt").write_text("second", encoding="utf-8")
    _commit(tmp_path, "Second feature commit")

    _git(str(tmp_path), "switch", "main")
    (tmp_path / "main-change.txt").write_text("main", encoding="utf-8")
    _commit(tmp_path, "Main follow-up")
    _git(str(tmp_path), "merge", "--no-ff", "feature", "-m", "Merge feature")

    assert get_release_version(tmp_path) == "1.3.5"


def test_release_version_rejects_downgrade_below_existing_tag(
    tmp_path,
) -> None:
    _initialize_repository(tmp_path)
    _git(str(tmp_path), "tag", "v1.4.0")

    with pytest.raises(ValueError, match="lower than latest released version"):
        get_release_version(tmp_path)
