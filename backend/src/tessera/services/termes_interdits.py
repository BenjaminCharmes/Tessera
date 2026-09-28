"""Contrôle des termes interdits avant publication — ADR-048.

Un push ne sort jamais si une ligne ajoutée, un message de commit ou un auteur
contient un terme de la liste. La liste vit dans FORBIDDEN_TERMS (.env local,
jamais versionné) ; vide ou absente, le service est inactif.

Le service ne nomme jamais le terme dans sa sortie : un log se partage, un nom
interdit aussi.

Intégration : `GitHubWorkflowService.open_pull_request()` appelle `verifier()`
avant le push. `PolitiqueRun.confidentialite == "professional"` court-circuite
le contrôle pour les dépôts professionnels (ADR-048).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ViolationTerme:
    """Localisation d'un terme interdit.

    `source` identifie l'endroit où le terme a été trouvé — jamais le terme
    lui-même. Formes attendues : ``"commit:<sha7>"``, ``"file:<chemin>"``,
    ``"auteur:<sha7>"``.
    """

    source: str


class TermesInterditsChecker(Protocol):
    """Contrat que doit satisfaire l'implémentation concrète."""

    @property
    def actif(self) -> bool:
        """False quand FORBIDDEN_TERMS est vide ou absent : aucun appel réseau."""
        ...

    def verifier(
        self,
        *,
        lignes_ajoutees: list[str],
        messages_commit: list[str],
        auteurs: list[str],
    ) -> list[ViolationTerme]:
        """Rend les violations trouvées. Liste vide signifie « rien à signaler »."""
        ...
