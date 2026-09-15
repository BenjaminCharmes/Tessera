"""Shared pytest fixtures and environment probes."""
import os
import tempfile
from pathlib import Path

import pytest


def _symlinks_available() -> bool:
    """True when this process may actually create a directory symlink.

    On Windows, `os.symlink` needs either Developer Mode or elevation and
    otherwise fails with WinError 1314 — an environment limitation, not a
    defect in the code under test.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "target"
        target.mkdir()
        try:
            (root / "link").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
        return True


SYMLINKS_AVAILABLE = _symlinks_available()

requires_symlinks = pytest.mark.skipif(
    not SYMLINKS_AVAILABLE,
    reason=(
        "this process cannot create symlinks "
        f"(on {os.name}, enable Developer Mode or run elevated)"
    ),
)
