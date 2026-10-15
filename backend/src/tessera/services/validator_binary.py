# -*- coding: utf-8 -*-
"""Binary file detection for the cited-files section (ticket-462).

Split out of ``validator_cited_files.py`` to keep that module small.
"""
from pathlib import Path

# Bytes inspected at the start of a file when looking for a NUL byte.
_SNIFF_BYTES = 8192
# Extensions that always denote a binary file, whatever their content.
_BINARY_EXTENSIONS = frozenset(
    {
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".avif",
        ".tif", ".tiff", ".heic",
        # Fonts
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
        # Archives and packages
        ".zip", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".tar", ".whl",
        ".jar",
        # Documents, media, compiled
        ".pdf", ".mp3", ".mp4", ".wav", ".mov", ".webm", ".ogg",
        ".exe", ".dll", ".so", ".dylib", ".pyc", ".class", ".sqlite", ".db",
    }
)


def is_binary_file(path: Path) -> bool:
    """Whether ``path`` is binary: known extension, or a NUL byte in its first 8 KB."""
    if path.suffix.lower() in _BINARY_EXTENSIONS:
        return True
    with path.open("rb") as handle:
        return b"\x00" in handle.read(_SNIFF_BYTES)
