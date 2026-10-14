"""Check a project's ticket files the way the loader reads them.

One broken frontmatter value makes `TicketService` drop the file from the
project; this module names the file and the field before the tickets are
committed (ticket-433).

Command line: ``python -m tessera.services.ticket_check <project_id>`` exits
with 1 when at least one problem is reported.
"""
import sys
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any

import frontmatter
from pydantic import BaseModel

from tessera.models.ticket import TicketPriority, TicketStatus, TicketType
from tessera.services.ticket_service import _STATUS_DIRS, TicketService

_REQUIRED_FIELDS = ("id", "title", "type", "priority", "agent")
_ENUM_FIELDS: dict[str, type[Enum]] = {
    "type": TicketType,
    "priority": TicketPriority,
    "status": TicketStatus,
}
_STATUS_BY_DIR = {directory: status for status, directory in _STATUS_DIRS.items()}


class Probleme(BaseModel):
    """One defect found in a ticket file."""

    #: Path of the file, relative to the project root, with forward slashes.
    chemin: str
    champ: str
    valeur: str | None = None
    message: str


def _enum_error(champ: str, valeur: object, enum: type[Enum]) -> Probleme | None:
    """Return a problem when `valeur` is not a member of `enum`."""
    try:
        enum(valeur)
    except ValueError:
        accepted = ", ".join(str(member.value) for member in enum)
        return Probleme(
            chemin="",
            champ=champ,
            valeur=str(valeur),
            message=f"valeur hors enum, acceptées : {accepted}",
        )
    return None


def _field_problems(meta: dict[str, Any], folder_status: TicketStatus | None) -> list[Probleme]:
    """Missing fields, out-of-enum values and a folder that contradicts `status`."""
    found: list[Probleme] = []
    for champ in _REQUIRED_FIELDS:
        if meta.get(champ) in (None, ""):
            found.append(Probleme(chemin="", champ=champ, message="champ obligatoire absent"))
    for champ, enum in _ENUM_FIELDS.items():
        if meta.get(champ) is not None and (problem := _enum_error(champ, meta[champ], enum)):
            found.append(problem)
    declared = meta.get("status")
    if declared is None and folder_status is None:
        found.append(Probleme(chemin="", champ="status", message="champ obligatoire absent"))
    elif folder_status is not None and declared is not None:
        if not _enum_error("status", declared, TicketStatus) and TicketStatus(declared) != folder_status:
            found.append(
                Probleme(
                    chemin="",
                    champ="status",
                    valeur=str(declared),
                    message=f"le fichier est rangé dans {_STATUS_DIRS[folder_status]}/",
                )
            )
    return found


def _check_file(service: TicketService, path: Path) -> tuple[str | None, list[Probleme]]:
    """Return the file's declared id (when readable) and its problems."""
    try:
        meta = dict(frontmatter.load(str(path)).metadata)
    except Exception as exc:  # noqa: BLE001 — un YAML illisible est justement le cas cherché
        return None, [Probleme(chemin="", champ="frontmatter", message=str(exc))]
    problems = _field_problems(meta, _STATUS_BY_DIR.get(path.parent.name))
    if not problems:
        # Dernier filet : ce que le chargeur refuserait sans que les contrôles
        # ci-dessus l'aient vu.
        try:
            service._parse(path)
        except Exception as exc:  # noqa: BLE001
            problems.append(Probleme(chemin="", champ="fichier", message=str(exc)))
    ticket_id = str(meta["id"]) if meta.get("id") not in (None, "") else None
    return ticket_id, problems


def _duplicate_problems(paths_by_id: dict[str, list[str]]) -> list[Probleme]:
    """One problem per file sharing its `id` with another file."""
    found: list[Probleme] = []
    for ticket_id, chemins in sorted(paths_by_id.items()):
        if len(chemins) < 2:
            continue
        for chemin in chemins:
            others = ", ".join(c for c in chemins if c != chemin)
            found.append(
                Probleme(
                    chemin=chemin,
                    champ="id",
                    valeur=ticket_id,
                    message=f"id déjà porté par {others}",
                )
            )
    return found


def verifier_tickets(racine_projet: Path) -> list[Probleme]:
    """List every defect in `tickets/*/ticket-*.md`, empty when the project is sound.

    Files are enumerated and parsed by `TicketService`, so a file reported here
    is exactly a file the loader would drop. `tickets/archive/` is skipped, as
    the loader skips it.
    """
    service = TicketService(racine_projet, racine_projet.name)
    problems: list[Probleme] = []
    paths_by_id: dict[str, list[str]] = defaultdict(list)
    for path in service._iter_active_files():
        chemin = path.relative_to(racine_projet).as_posix()
        ticket_id, file_problems = _check_file(service, path)
        problems.extend(p.model_copy(update={"chemin": chemin}) for p in file_problems)
        if ticket_id is not None:
            paths_by_id[ticket_id].append(chemin)
    return problems + _duplicate_problems(paths_by_id)


def main(argv: list[str]) -> int:
    """Print the problems of project `argv[0]` and return the exit code."""
    from tessera.config import settings
    from tessera.utils.project_id import validate_project_id

    if len(argv) != 1 or not validate_project_id(argv[0]):
        sys.stderr.write("usage : python -m tessera.services.ticket_check <project_id>\n")
        return 2
    racine = settings.ide_workspace_dir / argv[0]
    if not racine.is_dir():
        sys.stderr.write(f"projet introuvable : {racine}\n")
        return 2
    problems = verifier_tickets(racine)
    for p in problems:
        valeur = f" = {p.valeur!r}" if p.valeur is not None else ""
        sys.stdout.write(f"{p.chemin} : {p.champ}{valeur} — {p.message}\n")
    sys.stdout.write(f"{len(problems)} problème(s)\n")
    return 1 if problems else 0


if __name__ == "__main__":  # pragma: no cover — point d'entrée
    sys.exit(main(sys.argv[1:]))
