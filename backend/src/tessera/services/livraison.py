"""Livrer un run approuvé aussi loin que le projet le déclare — ticket-083.

Les maillons existaient tous séparément : le run commite (ADR-018), le service
de workflow pousse et ouvre la PR, et depuis ADR-029 il sait merger sur une CI
verte. Rien ne les enchaînait : chaque étape demandait un clic.

Ce service est cet enchaînement, et rien d'autre. Il ne décide de rien — il
lit `autonomy` et s'arrête là où le projet le dit. Il ne force rien non plus :
un conflit, une CI rouge ou une CI muette l'arrêtent, et il dit pourquoi.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from tessera.services.autonomie import NiveauAutonomie, lire_niveau
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Intervalle entre deux interrogations de la CI. Assez court pour ne pas
#: laisser traîner un ticket, assez long pour ne pas marteler l'API.
_INTERVALLE_CI_S = 15.0
#: Au-delà, on rend la main. Une attente sans borne bloquerait la file de
#: tickets, et ADR-018 fait reposer le ticket suivant sur un arbre propre.
_ATTENTE_CI_MAX_S = 900.0


@dataclass(frozen=True)
class Livraison:
    """Ce que la livraison a fait, et pourquoi elle s'est arrêtée."""

    etapes: tuple[str, ...] = ()
    #: `None` quand la livraison est allée aussi loin que le projet l'autorise.
    arret: str | None = None
    conflits: tuple[str, ...] = ()
    pr_number: int | None = None
    merged: bool = False


class _Git(Protocol):
    async def rejouer_sur(
        self,
        base: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> tuple[str, ...]: ...


class _Workflow(Protocol):
    async def open_pull_request(
        self,
        *,
        branch: str | None,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
    ) -> Any: ...
    async def etat_ci(self, pr_number: int) -> str: ...
    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool: ...


class LivraisonService:
    def __init__(
        self,
        git_workspace: _Git,
        workflow: _Workflow,
        project_path: Path,
        base_branch: str,
        attente_ci_max_s: float = _ATTENTE_CI_MAX_S,
        intervalle_ci_s: float = _INTERVALLE_CI_S,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> None:
        self._git = git_workspace
        self._workflow = workflow
        self._project_path = project_path
        self._base_branch = base_branch
        self._attente_ci_max_s = attente_ci_max_s
        self._intervalle_ci_s = intervalle_ci_s
        self._dormir = dormir
        self._resolveur = resolveur

    async def livrer(
        self,
        *,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        branch: str | None,
        approuve: bool,
    ) -> Livraison:
        """Porte le travail du ticket jusqu'où le projet le permet."""
        etapes: list[str] = []

        if not approuve:
            return Livraison(
                arret=(
                    "Run non approuvé : son commit porte du travail que le "
                    "reviewer a refusé, il ne se livre pas."
                )
            )
        if branch is None:
            return Livraison(arret="Aucune branche : rien à livrer.")

        niveau = lire_niveau(self._project_path)
        if niveau is NiveauAutonomie.commit:
            return Livraison(
                arret=(
                    f"Le travail est commité sur {branch}. Ce projet ne laisse "
                    "pas l'IDE aller plus loin ; pour changer cela, déclare "
                    '`"autonomy": "pr"` dans son agents.json.'
                )
            )

        resolus: list[str] = []

        async def resoudre(fichiers: tuple[str, ...]) -> None:
            # Le résolveur ne dit pas s'il a réussi : c'est `rejouer_sur` qui
            # tranche, en vérifiant l'arbre. On note seulement qu'il a tourné.
            resolus.extend(fichiers)
            if self._resolveur is not None:
                await self._resolveur(fichiers)

        conflits = await self._git.rejouer_sur(
            self._base_branch,
            resolveur=resoudre if self._resolveur is not None else None,
        )
        if conflits:
            return Livraison(
                etapes=tuple(etapes),
                conflits=conflits,
                arret=(
                    f"Conflit avec {self._base_branch} sur : "
                    + ", ".join(conflits)
                    + ". La branche est restée intacte, à toi de trancher."
                ),
            )
        etapes.append(f"rebase sur {self._base_branch}")
        if resolus:
            etapes.append("conflit résolu : " + ", ".join(resolus))

        resultat = await self._workflow.open_pull_request(
            branch=branch,
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            ticket_body=ticket_body,
        )
        pr_number = int(resultat.pr_number)
        etapes.append(f"PR #{pr_number} ouverte")

        if resolus:
            # Un conflit est l'endroit où deux intentions divergent : le pire
            # endroit pour deviner. Le projet a beau déclarer `merge`, il n'a
            # pas déclaré ça — et personne n'a relu la résolution.
            return Livraison(
                etapes=tuple(etapes),
                pr_number=pr_number,
                conflits=tuple(resolus),
                arret=(
                    f"Conflit résolu sur {', '.join(resolus)} : la PR "
                    f"#{pr_number} est ouverte, à relire. Une résolution de "
                    "conflit ne se merge jamais toute seule."
                ),
            )

        if niveau is not NiveauAutonomie.merge:
            return Livraison(
                etapes=tuple(etapes), pr_number=pr_number, arret=None
            )

        ci = await self._attendre_la_ci(pr_number)
        etapes.append(f"CI : {ci}")
        if ci == "pending":
            return Livraison(
                etapes=tuple(etapes),
                pr_number=pr_number,
                arret=(
                    "Fin de l'attente : la CI de la PR "
                    f"#{pr_number} n'a pas rendu de verdict. La PR reste "
                    "ouverte."
                ),
            )
        if ci != "passing":
            return Livraison(
                etapes=tuple(etapes),
                pr_number=pr_number,
                arret=f"CI {ci} : la PR #{pr_number} reste ouverte.",
            )

        merged = await self._workflow.merge_si_la_ci_est_verte(pr_number)
        if not merged:
            return Livraison(
                etapes=tuple(etapes),
                pr_number=pr_number,
                arret=f"GitHub a refusé le merge de la PR #{pr_number}.",
            )
        etapes.append(f"PR #{pr_number} mergée")
        _logger.info("livraison_complete", extra={"ticket": ticket_id, "pr": pr_number})
        return Livraison(etapes=tuple(etapes), pr_number=pr_number, merged=True)

    async def _attendre_la_ci(self, pr_number: int) -> str:
        """Interroge la CI jusqu'à un verdict, ou jusqu'à la borne d'attente."""
        ecoule = 0.0
        while True:
            etat = await self._workflow.etat_ci(pr_number)
            if etat != "pending":
                return etat
            if ecoule >= self._attente_ci_max_s:
                return "pending"
            await self._dormir(self._intervalle_ci_s)
            ecoule += self._intervalle_ci_s
