"""Pure text helpers: unions, conflict markers, ticket paths."""

import json
import re
from pathlib import Path


def _union_lines(base: str, theirs: str) -> str:
    """Union of two append-only text files, base lines first, no duplicates."""
    base_lines = base.splitlines(keepends=True)
    theirs_lines = theirs.splitlines(keepends=True)
    base_set = set(base_lines)
    extra = [line for line in theirs_lines if line not in base_set]
    return "".join(base_lines + extra)


def _liste_documentes(valeur: object) -> list[object] | None:
    """The id list of a ``documentation.json`` version, None if unrecognised.

    Accepts a bare JSON array, or the real marker format
    ``{"documentes": [...]}`` written by ``marquer_documente`` (ticket-418).
    """
    if isinstance(valeur, list):
        return valeur
    if isinstance(valeur, dict) and set(valeur) == {"documentes"}:
        interne = valeur["documentes"]
        return interne if isinstance(interne, list) else None
    return None


def _union_json_lists(base_text: str, theirs_text: str) -> str | None:
    """Union of two ``documentation.json`` versions, no duplicates.

    Base items come first. A bare array stays an array; the
    ``{"documentes": [...]}`` marker stays a marker, ids sorted as
    ``marquer_documente`` writes them. Returns None when either side is
    neither (invalid JSON, legacy ``dernier_ticket``, extra keys).
    """
    try:
        base_value = json.loads(base_text)
        theirs_value = json.loads(theirs_text)
    except (json.JSONDecodeError, ValueError):
        return None
    base_list = _liste_documentes(base_value)
    theirs_list = _liste_documentes(theirs_value)
    if base_list is None or theirs_list is None:
        return None
    seen: set[str] = set()
    result: list[object] = []
    for item in (*base_list, *theirs_list):
        key = json.dumps(item, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(item)
    if isinstance(base_value, dict) or isinstance(theirs_value, dict):
        envelope = {"documentes": sorted(result, key=str)}
        return json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    return json.dumps(result, ensure_ascii=False, indent=2)


def _extraire_fichiers_bloques(stderr: str) -> list[str]:
    """Extract untracked file paths that blocked a ``git rebase --abort``.

    Git emits, in this order:
        error: The following untracked working tree files would be overwritten by reset:
            path/to/file.md
        fatal: could not move back to <sha>

    Returns the list of file paths found between the header line and the
    ``fatal:`` line. Paths are returned as git reports them (relative to the
    repository root, with forward slashes on all platforms).
    """
    fichiers: list[str] = []
    en_section = False
    for ligne in stderr.splitlines():
        if "untracked working tree files" in ligne and "overwritten" in ligne:
            en_section = True
            continue
        if en_section:
            stripped = ligne.strip()
            if stripped and not any(
                stripped.startswith(p)
                for p in ("fatal:", "error:", "hint:", "Please")
            ):
                fichiers.append(stripped)
            else:
                en_section = False
    return fichiers


#: Le marqueur que git laisse dans un fichier non résolu.
_MARQUEUR_CONFLIT = "<" * 7


def _chemin_du_ticket(listing: str, ticket_id: str) -> str | None:
    """The first path of ``listing`` named ``<ticket_id>[-slug].md``, or None.

    Motif strict : ``ticket-50`` ne doit pas retrouver ``ticket-503-...md``.
    """
    motif = re.compile(rf"^{re.escape(ticket_id)}(?:-[\w-]+)?\.md$")
    for ligne in listing.splitlines():
        chemin = ligne.strip()
        if chemin and motif.match(Path(chemin).name):
            return chemin
    return None
