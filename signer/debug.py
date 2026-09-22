"""Small helpers for debug-only diagnostics."""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True when running as a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def debug_print(message: str, tag: str | os.PathLike[str] | None = None) -> None:
    """Print a tagged debug message when ``DEBUG=1``.

    If ``tag`` is omitted, it is derived from the calling module's filename
    without its extension.
    """
    if os.environ.get("DEBUG") != "1":
        return
    if tag is None:
        caller = inspect.currentframe()
        caller = caller.f_back if caller is not None else None
        tag = caller.f_globals.get("__file__", "debug") if caller else "debug"
    tag = Path(tag).stem
    print(f"[{tag}] {message}", flush=True)