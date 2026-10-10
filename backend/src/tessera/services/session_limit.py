"""Detect CLI session limit errors and extract the reset time — ticket-388."""
import re

_SESSION_LIMIT_RE = re.compile(r"hit your session limit", re.IGNORECASE)
# Le CLI suffixe « (exit code: 1) » : l'heure s'arrête avant.
_RESET_TIME_RE = re.compile(r"\bresets\s+(.+?)(?:\s*·|\s*\(exit code|\s*$)", re.IGNORECASE)
_ARRET_RESET_RE = re.compile(r"\(reprise\s*:\s*(.+)\)$")


def is_session_limit(message: str) -> bool:
    """Return True if message indicates a subscription session limit.

    Reconnaît la réponse du CLI : « You've hit your session limit · resets … »
    """
    return bool(_SESSION_LIMIT_RE.search(message))


def extract_reset_time(message: str) -> str | None:
    """Extract the reset time from a session limit error message.

    Format attendu : « You've hit your session limit · resets 5pm (Europe/Paris) »
    Renvoie « 5pm (Europe/Paris) » ou None si absent.
    """
    match = _RESET_TIME_RE.search(message)
    if match:
        return match.group(1).strip()
    return None


def extract_reset_time_from_arret(arret: str | None) -> str | None:
    """Extract the reset time from a session-limit arret string.

    Format attendu : « session_limit (reprise : 5pm (Europe/Paris)) »
    Renvoie « 5pm (Europe/Paris) » ou None si absent ou format différent.
    """
    if arret is None:
        return None
    match = _ARRET_RESET_RE.search(arret)
    if match:
        return match.group(1).strip()
    return None
