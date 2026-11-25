"""L'issue de chaque rôle de documentation, et le tour de correction — ticket-1037."""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.services.documentation.documentation_base import EditionRefusee
from tessera.services.documentation.documentation_code import MatiereCode
from tessera.services.documentation.documentation_editions import appliquer_editions
from tessera.services.documentation.documentation_reponse import editions_depuis, lire_json, refuser
from tessera.services.documentation.documentation_titres import brief_correction, titres_fichiers_vises
from tessera.services.providers.base import LLMProvider
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

APPLIQUEES = "éditions appliquées"
AUCUNE = "aucune édition proposée"
ILLISIBLE = "réponse illisible"
REFUSE = "refusé"
#: Les issues où le rôle n'a rien écrit : le journal les nomme.
SANS_ECRITURE = (AUCUNE, ILLISIBLE, REFUSE)


def noter_illisible(role: str, issues: dict[str, str], refus: list[str]) -> None:
    """Record an unreadable answer as a refusal, so the batch counts it."""
    _logger.warning("reponse_doc_illisible", extra={"role": role})
    issues[role] = ILLISIBLE
    refus.append(f"{role} : {ILLISIBLE}")


@dataclass(frozen=True)
class ContexteEdition:
    """What an edit is applied against, gathered to keep signatures short."""

    racine: Path
    fichiers: list[str]
    claude_md: Path | None
    matiere: MatiereCode
    intentions: str
    agents_md: Path | None


async def tour_de_correction(
    provider: LLMProvider,
    modele: str,
    max_tokens: int,
    cwd: Path,
    systeme: str,
    user: Callable[[], str],
    role: str,
    premiere: str,
    exc: EditionRefusee,
    editions: list[dict[str, object]],
    contexte: ContexteEdition,
    issues: dict[str, str],
    refus: list[str],
) -> list[str]:
    """Call the role once more with the refusal; return the files written."""
    motif = str(exc)
    reponse = await provider.complete(
        system=systeme,
        user=brief_correction(
            user(), premiere, motif,
            titres_fichiers_vises(contexte.racine, editions), contexte.fichiers, exc.extrait,
        ),
        model=modele,
        max_tokens=max_tokens,
        cwd=cwd,
    )
    donnees = lire_json(str(reponse.content))
    if donnees is None:
        noter_illisible(role, issues, refus)
        refuser(role, [motif], refus)
        return []
    editions2 = editions_depuis(donnees)
    if not editions2:
        # Le refus qui a coûté deux appels ne se perd pas.
        issues[role] = REFUSE
        refuser(role, [motif], refus)
        return []
    ecartees: list[str] = []
    try:
        ecrits = appliquer_editions(
            contexte.racine, editions2, contexte.claude_md, contexte.matiere,
            contexte.intentions, contexte.agents_md, ecartees,
        )
    except EditionRefusee as exc2:
        issues[role] = REFUSE
        refuser(role, [str(exc2)], refus)
        return []
    refuser(role, ecartees, refus)
    return ecrits
