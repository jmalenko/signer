"""Calculate the release version from REQUIREMENTS.md and Git history."""

import re
import subprocess
from pathlib import Path

REQUIREMENT_VERSION = re.compile(
    r"^## Version (\d+)\.(\d+)(?:\.\d+)? - .+$",
    re.MULTILINE,
)
RELEASE_TAG_VERSION = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def get_release_version(repository_root: Path = REPOSITORY_ROOT) -> str:
    requirements_path = repository_root / "REQUIREMENTS.md"
    requirements = requirements_path.read_text(encoding="utf-8")
    matches = list(REQUIREMENT_VERSION.finditer(requirements))
    if not matches:
        raise ValueError("REQUIREMENTS.md has no version heading")

    latest = matches[-1]
    major, minor = latest.group(1, 2)
    version_marker = f"## Version {major}.{minor} -"
    relative_requirements_path = requirements_path.relative_to(repository_root)
    introducing_commits = subprocess.run(
        [
            "git",
            "log",
            "--reverse",
            "--format=%H",
            f"-S{version_marker}",
            "--",
            str(relative_requirements_path),
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if not introducing_commits:
        error_message = (
            f"Could not find the commit that introduced {version_marker!r}"
        )
        raise RuntimeError(error_message)

    commits_since_requirement = subprocess.run(
        [
            "git",
            "rev-list",
            "--ancestry-path",
            "--count",
            f"{introducing_commits[0]}..HEAD",
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    version_parts = (int(major), int(minor), int(commits_since_requirement))
    version = ".".join(str(part) for part in version_parts)

    existing_tags = subprocess.run(
        ["git", "tag", "--list"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    released_versions = [
        tuple(map(int, match.groups()))
        for tag in existing_tags
        if (match := RELEASE_TAG_VERSION.fullmatch(tag))
    ]
    if released_versions:
        latest_released_version = max(released_versions)
        if version_parts < latest_released_version:
            latest_released = ".".join(
                str(part) for part in latest_released_version
            )
            raise ValueError(
                f"Release version {version} is lower than latest released "
                f"version {latest_released}"
            )

    return version


if __name__ == "__main__":
    print(get_release_version())
