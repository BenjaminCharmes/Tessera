"""Petits outils de la reprise de surveillance — ticket-510, ticket-516.

Le journal du projet, et la lecture des PR ouvertes sur GitHub : une PR du
pipeline se reconnaît à sa branche de tête `ticket-NNN-…` et à sa base.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from tessera.services.github_service import PrOuverte
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_BRANCHE_TICKET = re.compile(r"^(ticket-\d+)-")


def ecrire_log(projet: Path, texte: str) -> None:
    """Append one timestamped line to the project's pipeline log; never raises."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    chemin = projet / "memory" / "pipeline-log.md"
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with chemin.open("a", encoding="utf-8") as f:
            f.write(f"- {ts} — {texte}\n")
    except OSError as exc:
        _logger.warning("reprise_ci_log_echec", extra={"erreur": str(exc)})


def ticket_de_branche(branche: str) -> str | None:
    """The ticket id a pipeline branch belongs to (`ticket-034-x` -> `ticket-034`)."""
    trouve = _BRANCHE_TICKET.match(branche)
    return trouve.group(1) if trouve else None


def prs_a_reprendre(
    prs: list[PrOuverte], base: str | None
) -> list[tuple[str, int]]:
    """The (ticket id, PR number) pairs worth handing back to the watcher.

    Keeps the PR whose head branch follows `ticket-NNN-` and whose base is the
    project's. Without a known base nothing is kept: a PR is never merged
    toward a branch the project did not declare.
    """
    if base is None:
        return []
    retenues: list[tuple[str, int]] = []
    for pr in prs:
        ticket_id = ticket_de_branche(pr.branche)
        if ticket_id is not None and pr.base == base:
            retenues.append((ticket_id, pr.number))
    return retenues
