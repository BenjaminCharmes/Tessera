"""La matière de code que lit la documentation par lot — ticket-540, ADR-057.

Un ticket dit l'intention ; il ne dit ni le numéro d'une migration, ni un
seuil, ni le libellé d'un onglet. Ce module produit ce que l'agent lira en plus
des tickets : le diff livré de chaque ticket, puis le contenu des fichiers que
ces diffs touchent. Tout est borné, et tout ce qui est coupé se nomme : un
agent qui ne sait pas ce qu'il n'a pas vu en déduit des faits.

Le brief (`documentation._brief`) l'assemble avec les tickets (ticket-541).
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.diff_sections import Section, borner, decouper, marqueur
from tessera.services.ticket_diff import diff_du_ticket

#: Bornes en caractères : par ticket et pour le lot (diffs), par fichier et
#: pour le lot (contenus). Des constantes, à ajuster après les premiers lots.
_BORNE_DIFF_TICKET = 12_000
_BORNE_DIFF_LOT = 60_000
_BORNE_FICHIER = 8_000
_BORNE_FICHIERS = 40_000


@dataclass(frozen=True)
class DiffDeTicket:
    """Le diff filtré d'un ticket, borné ; `non_montres` nomme ce qui a été coupé."""

    ticket_id: str
    diff: str
    fichiers: list[str]
    non_montres: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FichierLivre:
    chemin: str
    contenu: str


@dataclass(frozen=True)
class MatiereCode:
    diffs: list[DiffDeTicket] = field(default_factory=list)
    fichiers: list[FichierLivre] = field(default_factory=list)
    #: Fichiers touchés dont le contenu n'est pas fourni (trop longs, ou le lot
    #: est plein) : l'agent ne les a que par leurs hunks.
    fichiers_non_montres: list[str] = field(default_factory=list)
    #: Tickets sans diff retrouvable, ou dont le diff filtré est vide.
    sans_diff: list[str] = field(default_factory=list)


def _diff_borne(
    ticket_id: str, fichiers: list[str], sections: list[Section], reste_du_lot: int
) -> tuple[DiffDeTicket, int]:
    """Le diff d'un ticket dans sa borne et celle du lot, et ce qu'il en consomme."""
    montre, non_montres = borner(sections, min(_BORNE_DIFF_TICKET, reste_du_lot))
    texte = montre + marqueur(non_montres) if non_montres else montre
    return DiffDeTicket(ticket_id, texte, fichiers, non_montres), len(montre)


def _cumuler(changes: dict[str, int], sections: list[Section]) -> None:
    """Ajoute les lignes changées des fichiers dont le contenu est lisible."""
    for section in sections:
        if section.lisible:
            changes[section.chemin] = changes.get(section.chemin, 0) + section.lignes


def _lire_fichier(racine: Path, chemin: str) -> str | None:
    """Le texte d'un fichier du dépôt, ou None : absent, hors dépôt, binaire, énorme."""
    cible = (racine / chemin).resolve()
    try:
        cible.relative_to(racine.resolve())
    except ValueError:
        return None
    if not cible.is_file() or cible.stat().st_size > 4 * _BORNE_FICHIER:
        return None
    try:
        return cible.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _contenus(
    racine: Path, changes: dict[str, int]
) -> tuple[list[FichierLivre], list[str]]:
    """Les fichiers, du plus modifié au moins modifié, dans la borne du lot."""
    livres: list[FichierLivre] = []
    non_montres: list[str] = []
    total = 0
    for chemin in sorted(changes, key=lambda c: (-changes[c], c)):
        if not (racine / chemin).is_file():
            continue
        contenu = _lire_fichier(racine, chemin)
        if (
            contenu is None
            or len(contenu) > _BORNE_FICHIER
            or total + len(contenu) > _BORNE_FICHIERS
        ):
            non_montres.append(chemin)
        else:
            livres.append(FichierLivre(chemin, contenu))
            total += len(contenu)
    return livres, non_montres


async def matiere_du_lot(
    racine_depot: Path,
    project_path: Path,
    tickets: list[str],
    base: str | None = None,
) -> MatiereCode:
    """Le diff livré de chaque ticket, les fichiers qu'il touche, et les tickets sans diff.

    `racine_depot` est la racine du dépôt (`racine_doc`) : le diff s'y prend,
    et les exclusions portent le chemin du projet. `base` est la base déclarée
    du projet, pour un ticket encore sur sa branche.
    """
    diffs: list[DiffDeTicket] = []
    sans_diff: list[str] = []
    changes: dict[str, int] = {}
    reste = _BORNE_DIFF_LOT
    for ticket_id in tickets:
        trouve = await diff_du_ticket(
            project_path, ticket_id, base=base, depot=racine_depot,
            hors_documentation=True,
        )
        sections = decouper(trouve.diff)
        if not sections:
            sans_diff.append(ticket_id)
            continue
        diff, consomme = _diff_borne(ticket_id, trouve.files, sections, reste)
        reste -= consomme
        diffs.append(diff)
        _cumuler(changes, sections)
    fichiers, fichiers_non_montres = _contenus(racine_depot, changes)
    return MatiereCode(diffs, fichiers, fichiers_non_montres, sans_diff)


#: Ce que le service appelle pour obtenir la matière : `matiere_du_lot`, ou un
#: substitut quand le dépôt n'est pas celui d'un vrai run.
FournisseurMatiere = Callable[[Path, Path, list[str], str | None], Awaitable[MatiereCode]]


def bloc_diffs(matiere: MatiereCode) -> str:
    """The delivered diff of each ticket, one titled block per ticket (ticket-541)."""
    if not matiere.diffs:
        return ""
    morceaux = ["\n---\nDiff livré de chaque ticket (hors documentation) :\n"]
    for diff in matiere.diffs:
        morceaux.append(f"\n### {diff.ticket_id}\n\n```diff\n{diff.diff.rstrip()}\n```\n")
    return "".join(morceaux)


def bloc_fichiers(matiere: MatiereCode) -> str:
    """The current content of the touched files, and the names of those left out."""
    if not matiere.fichiers and not matiere.fichiers_non_montres:
        return ""
    morceaux = ["\n---\nFichiers touchés par ces diffs (contenu actuel) :\n"]
    for fichier in matiere.fichiers:
        morceaux.append(f"\n### {fichier.chemin}\n\n```\n{fichier.contenu.rstrip()}\n```\n")
    if matiere.fichiers_non_montres:
        noms = ", ".join(matiere.fichiers_non_montres)
        morceaux.append(
            f"\n[contenu non fourni — lisible dans les diffs seulement : {noms}]\n"
        )
    return "".join(morceaux)
