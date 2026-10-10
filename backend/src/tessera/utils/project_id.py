"""Project-id validation shared by models and routes — ticket-370.

Kept in its own module: `models/project.py` and `services/project_loader.py`
both need it, and the loader already imports the models.
"""
import re

_PROJECT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def validate_project_id(project_id: str) -> bool:
    """Return True when project_id is safe to use as a directory name.

    Accepts identifiers matching ``[A-Za-z0-9][A-Za-z0-9._-]*`` over the
    **whole** string. Rejects empty strings, path separators (/ and \\),
    traversal sequences (., .., ../x, ..\\x) and a trailing newline, which
    ``re.match`` with ``$`` would let through.
    """
    return _PROJECT_ID_RE.fullmatch(project_id) is not None
