"""Moves the old months of a project's pipeline log into monthly archives.

Nothing is deleted: every line leaves the log only to be appended to
`memory/journal/pipeline-log-YYYY-MM.md`. Meant to run by hand, outside any
run: the in-memory `RunLock` is not visible from here.
"""

import re
from collections import defaultdict
from datetime import date
from pathlib import Path

JOURNAL = Path("memory/pipeline-log.md")
ARCHIVE_DIR = Path("memory/journal")

_LIGNE_DATEE = re.compile(r"^- (\d{4})-(\d{2})-\d{2} ")


def _mois_conserves(aujourd_hui: date, garder_mois: int) -> set[str]:
    """The `garder_mois` latest months, current one included, as `YYYY-MM`."""
    conserves: set[str] = set()
    annee, mois = aujourd_hui.year, aujourd_hui.month
    for _ in range(garder_mois):
        conserves.add(f"{annee:04d}-{mois:02d}")
        mois -= 1
        if mois == 0:
            annee, mois = annee - 1, 12
    return conserves


def _repartir(lignes: list[str]) -> list[tuple[str | None, str]]:
    """Pairs each line with its month; an undated line takes the previous one's."""
    resultat: list[tuple[str | None, str]] = []
    courant: str | None = None
    for ligne in lignes:
        trouve = _LIGNE_DATEE.match(ligne)
        if trouve:
            courant = f"{trouve.group(1)}-{trouve.group(2)}"
        resultat.append((courant, ligne))
    return resultat


def archiver_journal(
    projet: Path, garder_mois: int = 2, aujourd_hui: date | None = None
) -> dict[str, int]:
    """Archives the log lines older than `garder_mois` months; returns lines moved per month.

    Archives are written before the log is rewritten, so a failure midway
    never loses a line (at worst a line is present twice).
    """
    if garder_mois < 1:
        raise ValueError("garder_mois must be at least 1")
    journal = projet / JOURNAL
    if not journal.is_file():
        return {}
    conserves = _mois_conserves(aujourd_hui or date.today(), garder_mois)
    with journal.open(encoding="utf-8", newline="") as f:
        lignes = f.read().splitlines(keepends=True)
    gardees: list[str] = []
    a_ranger: dict[str, list[str]] = defaultdict(list)
    for mois, ligne in _repartir(lignes):
        if mois is None or mois in conserves:
            gardees.append(ligne)
        else:
            a_ranger[mois].append(ligne)
    if not a_ranger:
        return {}
    dossier = projet / ARCHIVE_DIR
    dossier.mkdir(parents=True, exist_ok=True)
    for mois, bloc in a_ranger.items():
        with (dossier / f"pipeline-log-{mois}.md").open("a", encoding="utf-8", newline="") as f:
            f.write("".join(bloc))
    with journal.open("w", encoding="utf-8", newline="") as f:
        f.write("".join(gardees))
    return {mois: len(bloc) for mois, bloc in sorted(a_ranger.items())}
