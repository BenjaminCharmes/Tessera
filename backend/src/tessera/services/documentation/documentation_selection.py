"""Choisir les tickets à documenter et tenir le marqueur — t.213, extrait par t.692.

Le marqueur ``memory/documentation.json`` dit quels tickets terminés ont déjà
été documentés. Le plafond du lot et le rattrapage initial sont décidés par le
service (``documentation``) ; ce module ne fait que lire et écrire.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

MARQUEUR = "documentation.json"


@dataclass(frozen=True)
class TicketADocumenter:
    id: str
    titre: str
    corps: str


def _tickets_documentes(project_path: Path) -> set[str]:
    """Return the set of ticket IDs that have already been documented.

    Reads the new format ``{"documentes": [...]}`` and falls back to the
    legacy ``{"dernier_ticket": "..."}`` for backward compatibility (ADR-036).
    A missing or unreadable marker returns an empty set.
    """
    marqueur = project_path / "memory" / MARQUEUR
    if not marqueur.is_file():
        return set()
    try:
        data = json.loads(marqueur.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _logger.warning("marqueur_doc_illisible", extra={"path": str(marqueur)})
        return set()

    # New format: {"documentes": ["ticket-001", ...]}
    if "documentes" in data:
        valeur = data["documentes"]
        return set(valeur) if isinstance(valeur, list) else set()

    # Old format: {"dernier_ticket": "ticket-NNN"}  (ADR-036 — lu, jamais réécrit)
    dernier = data.get("dernier_ticket")
    if not dernier:
        return set()
    dossier = project_path / "tickets" / "done"
    if not dossier.is_dir():
        return set()
    documentes: set[str] = set()
    for fichier in dossier.glob("*.md"):
        identifiant = "-".join(fichier.stem.split("-")[:2])
        if identifiant <= str(dernier):
            documentes.add(identifiant)
    return documentes


def tickets_a_documenter(project_path: Path) -> list[TicketADocumenter]:
    """Les tickets terminés qui ne figurent pas encore dans le marqueur.

    Filtre par ensemble d'identifiants documentés plutôt que par comparaison
    de chaînes : un ticket livré avec un identifiant inférieur au dernier
    documenté (livraison hors ordre) est inclus, là où l'ancien filtre
    ``identifiant <= dernier`` l'aurait exclu définitivement.
    """
    dossier = project_path / "tickets" / "done"
    if not dossier.is_dir():
        return []

    documentes = _tickets_documentes(project_path)
    tickets: list[TicketADocumenter] = []
    for fichier in sorted(dossier.glob("*.md")):
        identifiant = "-".join(fichier.stem.split("-")[:2])
        if identifiant in documentes:
            continue
        tickets.append(
            TicketADocumenter(
                id=identifiant,
                titre=_titre(fichier),
                corps=fichier.read_text(encoding="utf-8"),
            )
        )
    return tickets


def _titre(fichier: Path) -> str:
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        if ligne.startswith("title:"):
            return ligne.split(":", 1)[1].strip().strip('"')
    return fichier.stem


def marquer_documente(project_path: Path, ticket_ids: list[str]) -> None:
    """Record which ticket IDs have been documented.

    Merges ``ticket_ids`` with any already-documented IDs and writes the new
    ``{"documentes": [...]}`` format.  The old ``{"dernier_ticket": ...}``
    format is never written back (ADR-036).
    """
    existants = _tickets_documentes(project_path)
    tous = existants | set(ticket_ids)
    memoire = project_path / "memory"
    memoire.mkdir(parents=True, exist_ok=True)
    (memoire / MARQUEUR).write_text(
        json.dumps({"documentes": sorted(tous)}, indent=2) + "\n",
        encoding="utf-8",
    )
