"""Which « À toi » cases are still open once their target is settled — ticket-1059.

A filter on read: nothing is written to `memory/supervision.md`. A case whose
ticket is done or cancelled, or whose rule or lesson left `## Proposées`, no
longer waits for the user.
"""
import re
from pathlib import Path

from tessera.services.supervision.superviseur_decision_blocs import Genre, blocs_proposes
from tessera.services.supervision.superviseur_journal import LigneJournal, cas_a_toi_ouverts, lire_journal

DOSSIERS_REGLES = ("done", "cancelled")
_TICKET = re.compile(r"^(ticket-\d+)(?:-|\.md$|$)")
_FICHIERS: dict[str, tuple[Genre, str]] = {
    "regle": ("regle", "contraintes.md"),
    "lecon": ("lecon", "lecons.md"),
}


def ids_tickets_regles(projet: Path) -> frozenset[str]:
    """Ids (`ticket-XXX`) of the tickets under `tickets/done` and `tickets/cancelled`."""
    ids: set[str] = set()
    for dossier in DOSSIERS_REGLES:
        try:
            noms = [p.name for p in (projet / "tickets" / dossier).iterdir()]
        except OSError:
            continue
        ids.update(m.group(1) for nom in noms if (m := _TICKET.match(nom)))
    return frozenset(ids)


def _est_regle(cas: LigneJournal, tickets: frozenset[str], proposes: dict[Genre, set[str]]) -> bool:
    ticket = _TICKET.match(cas.cible)
    if ticket:
        return ticket.group(1) in tickets
    genre = cas.cible.split("-", 1)[0]
    if genre in _FICHIERS and cas.cible.count("-") == 1:
        return cas.cible not in proposes[_FICHIERS[genre][0]]
    return False


def cas_encore_ouverts(
    cas: list[LigneJournal],
    tickets_regles: frozenset[str],
    contraintes: str,
    lecons: str,
) -> list[LigneJournal]:
    """The cases whose target is not settled; an unknown target form stays open."""
    proposes: dict[Genre, set[str]] = {
        "regle": {b.cible for b in blocs_proposes(contraintes, "regle")},
        "lecon": {b.cible for b in blocs_proposes(lecons, "lecon")},
    }
    return [c for c in cas if not _est_regle(c, tickets_regles, proposes)]


def _lire(chemin: Path) -> str:
    try:
        return chemin.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def cas_a_toi_a_relire(memory_dir: Path, journal: list[LigneJournal] | None = None) -> list[LigneJournal]:
    """Open `a_toi` cases of a project, minus those already settled; simple reads only."""
    lignes = lire_journal(memory_dir) if journal is None else journal
    return cas_encore_ouverts(
        cas_a_toi_ouverts(lignes),
        ids_tickets_regles(memory_dir.parent),
        _lire(memory_dir / "contraintes.md"),
        _lire(memory_dir / "lecons.md"),
    )
