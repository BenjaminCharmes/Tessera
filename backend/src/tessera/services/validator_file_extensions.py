# -*- coding: utf-8 -*-
"""Which backtick-quoted token of a criterion names a file (ticket-475)."""
import re

# Trailing extension (letters or digits, as in ``woff2``), captured without its
# dot. Its length is not bounded: a path stays a path whatever it ends with.
_FILE_EXTENSION = re.compile(r"\.([a-zA-Z0-9]+)$")

# Extensions of files a criterion may cite: code, config, documents, images.
# ``BRAND.name`` or ``settings.github_token`` end like a file but are
# identifiers: only a known extension, or a ``/`` in the token, makes a file.
KNOWN_FILE_EXTENSIONS = frozenset(
    {
        # Code
        "py", "pyi", "ts", "tsx", "js", "jsx", "mjs", "cjs", "rs", "go",
        "java", "kt", "rb", "php", "c", "h", "cpp", "hpp", "cs", "swift",
        "sh", "bash", "ps1", "bat", "sql", "prisma", "graphql", "gql",
        "vue", "svelte", "lua",
        # Config and data
        "json", "jsonc", "yml", "yaml", "toml", "ini", "cfg", "conf", "env",
        "lock", "xml", "csv", "tsv", "ndjson", "jsonl", "mdx", "tf",
        "gitignore", "dockerfile",
        # Documents and web
        "md", "txt", "rst", "pdf", "html", "htm", "css", "scss", "sass",
        "less", "log", "ipynb",
        # Images, fonts, media
        "png", "jpg", "jpeg", "gif", "svg", "webp", "avif", "ico", "bmp",
        "woff", "woff2", "ttf", "otf", "mp3", "mp4", "webm", "wav",
    }
)


def looks_like_file(candidate: str) -> bool:
    """Whether ``candidate`` reads as a file name rather than an identifier.

    A token with a ``/`` and an extension is a path whatever that extension;
    otherwise the extension must belong to ``KNOWN_FILE_EXTENSIONS``
    (case-insensitive). A token without any extension is never a file.
    """
    match = _FILE_EXTENSION.search(candidate)
    if match is None:
        return False
    if "/" in candidate:
        return True
    return match.group(1).lower() in KNOWN_FILE_EXTENSIONS
