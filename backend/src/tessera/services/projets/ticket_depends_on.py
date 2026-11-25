"""Normalisation du champ `depends_on` d'un ticket, extraite de `ticket_service`."""
import re

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_TICKET_ID_RE = re.compile(r"^ticket-\d+$")


def normalize_depends_on(raw: object) -> list[str]:
    """Coerce any YAML representation of depends_on into a list of ticket ids.

    YAML scalars like ``depends_on: ticket-001`` reach Python as a plain string.
    Iterating over a string yields characters, not ticket ids — the root cause
    of ticket-275.  This function handles all three forms:

    * ``None`` / empty string / empty list → ``[]``
    * ``str`` → split on commas, strip whitespace, discard empty pieces
    * ``list`` → kept as-is after coercion to str

    Items that do not look like ``ticket-NNN`` are discarded and logged.
    """
    if not raw:
        return []

    if isinstance(raw, str):
        pieces = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, (list, tuple)):
        pieces = [str(item) for item in raw]
    else:
        pieces = [str(raw)]

    result: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if _TICKET_ID_RE.match(piece):
            result.append(piece)
        else:
            _logger.warning("depends_on_invalid_id", extra={"value": piece})
    return result
