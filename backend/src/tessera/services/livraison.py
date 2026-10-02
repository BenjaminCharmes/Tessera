"""Livrer un run approuvé aussi loin que le projet le déclare — ticket-083.

Les maillons existaient tous séparément : le run commite (ADR-018), le service
de workflow pousse et ouvre la PR, et depuis ADR-029 il sait merger sur une CI
verte. Rien ne les enchaînait : chaque étape demandait un clic.

Ce service est cet enchaînement, et rien d'autre. Il ne décide de rien — il
lit `autonomy` et s'arrête là où le projet le dit. Il ne force rien non plus :
un conflit, une CI rouge ou une CI muette l'arrêtent, et il dit pourquoi.
"""
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from tessera.services.autonomie import NiveauAutonomie, lire_niveau
from tessera.services.git_workspace import GitCommandError
from tessera.services.politique_run import PolitiqueRun
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Intervalle entre deux interrogations de la CI. Assez court pour ne pas
#: laisser traîner un ticket, assez long pour ne pas marteler l'API.
_INTERVALLE_CI_S = 15.0
#: Au-delà, on rend la main. Une attente sans borne bloquerait la file de
#: tickets, et ADR-018 fait reposer le ticket suivant sur un arbre propre.
_ATTENTE_CI_MAX_S = 900.0
#: Délai de grâce avant de lire `none` comme un verdict final. GitHub
#: n'enregistre les checks qu'après l'ouverture de la PR : interroger
#: immédiatement retourne `none` sans qu'aucun check ait pu s'inscrire.
#: Pendant ce délai, `none` est traité comme `pending`. Passé ce délai,
#: `none` redevient un verdict et la livraison s'arrête (ADR-029 : l'absence
#: de signal n'est pas un signal favorable).
_GRACE_CI_S = 120.0


@dataclass(frozen=True)
class Livraison:
    """Ce que la livraison a fait, et pourquoi elle s'est arrêtée."""

    etapes: tuple[str, ...] = ()
    #: Durée en millisecondes de chaque étape, dans le même ordre que `etapes`.
    #: `tuple[float, ...]` est JSON-sérialisable (devient une liste). (ticket-288)
    durees_ms: tuple[float, ...] = ()
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
    async def sync_base_depuis_distant(self, base_branch: str) -> str | None: ...
    async def commit_bookkeeping(self) -> None: ...


class _Workflow(Protocol):
    async def open_pull_request(
        self,
        *,
        branch: str | None,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        ticket_type: str = "",
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
        grace_ci_s: float = _GRACE_CI_S,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
        politique: PolitiqueRun | None = None,
        post_pr_callback: Callable[[str, int, str], Awaitable[None]] | None = None,
    ) -> None:
        self._git = git_workspace
        self._workflow = workflow
        self._project_path = project_path
        self._base_branch = base_branch
        self._attente_ci_max_s = attente_ci_max_s
        self._intervalle_ci_s = intervalle_ci_s
        self._grace_ci_s = grace_ci_s
        self._dormir = dormir
        self._resolveur = resolveur
        # Le niveau se fige **avant** le premier agent, jamais au moment de
        # livrer : `agents.json` est sous la racine du projet, et un codeur
        # pouvait y écrire `merge` pendant le run (ticket-119). Sans politique
        # — appel hors pipeline — on lit le fichier, comme avant.
        self._politique = politique
        # Appelé après `open_pull_request` mais avant tout merge : écrit le
        # pr_number dans le ticket, commite et pousse, de sorte qu'aucun
        # commit ne soit laissé sur la branche après le merge (ticket-270).
        self._post_pr_callback = post_pr_callback

    async def livrer(
        self,
        *,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        ticket_type: str = "",
        branch: str | None,
        approuve: bool,
    ) -> Livraison:
        """Porte le travail du ticket jusqu'où le projet le permet."""
        etapes: list[str] = []
        durees_ms: list[float] = []

        if not approuve:
            return Livraison(
                arret=(
                    "Run non approuvé : son commit porte du travail que le "
                    "reviewer a refusé, il ne se livre pas."
                )
            )
        if branch is None:
            return Livraison(arret="Aucune branche : rien à livrer.")

        niveau = (
            self._politique.autonomy
            if self._politique is not None
            else lire_niveau(self._project_path)
        )
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

        # Align local base_branch with remote before rebase (ticket-285).
        # Non-blocking: a failed sync falls back to the current local branch.
        await self._git.sync_base_depuis_distant(self._base_branch)

        # Commite les artefacts de tenue de livres en attente (pipeline-log,
        # statuts de tickets) avant le rebase : `git rebase` exige un arbre
        # entièrement propre, sans exception, alors qu'`is_clean` tolère ces
        # chemins pour ne pas bloquer le ticket suivant (ticket-303).
        await self._git.commit_bookkeeping()

        t0 = time.monotonic()
        try:
            conflits = await self._git.rejouer_sur(
                self._base_branch,
                resolveur=resoudre if self._resolveur is not None else None,
            )
        except GitCommandError as exc:
            # Le rebase a refusé de démarrer — arbre sale (fichier de code
            # modifié non commité), base inconnue ou autre erreur git.
            # `commit_bookkeeping` a déjà commité les artefacts Tessera : ce
            # qui reste est du code que le pipeline n'a pas produit.
            raison = exc.stderr.strip() or str(exc)
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                arret=f"Rebase refusé : {raison}",
            )
        rebase_ms = (time.monotonic() - t0) * 1000

        if conflits:
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                conflits=conflits,
                arret=(
                    f"Conflit avec {self._base_branch} sur : "
                    + ", ".join(conflits)
                    + ". La branche est restée intacte, à toi de trancher."
                ),
            )
        etapes.append(f"rebase sur {self._base_branch}")
        durees_ms.append(rebase_ms)
        if resolus:
            # La résolution est incluse dans la durée du rebase ci-dessus.
            etapes.append("conflit résolu : " + ", ".join(resolus))
            durees_ms.append(0.0)

        t0 = time.monotonic()
        resultat = await self._workflow.open_pull_request(
            branch=branch,
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            ticket_body=ticket_body,
            ticket_type=ticket_type,
        )
        pr_ms = (time.monotonic() - t0) * 1000
        pr_number = int(resultat.pr_number)
        etapes.append(f"PR #{pr_number} ouverte")
        durees_ms.append(pr_ms)

        # Enregistre le pr_number dans le ticket, commite et pousse **avant**
        # tout merge : garantit qu'aucun commit n'est laissé sur la branche
        # locale après que la PR a été mergée (ticket-270).
        if self._post_pr_callback is not None:
            try:
                await self._post_pr_callback(ticket_id, pr_number, branch)
            except Exception as exc:  # noqa: BLE001 — non-critique, le merge continue
                _logger.warning("post_pr_callback_failed", extra={"error": str(exc)})

        if resolus:
            # Un conflit est l'endroit où deux intentions divergent : le pire
            # endroit pour deviner. Le projet a beau déclarer `merge`, il n'a
            # pas déclaré ça — et personne n'a relu la résolution.
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
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
                etapes=tuple(etapes), durees_ms=tuple(durees_ms),
                pr_number=pr_number, arret=None,
            )

        # Attendre une CI que le projet déclare absente, c'est payer le délai
        # complet pour un verdict qui ne viendra pas (ADR-045). Le refus sur
        # une CI rouge, lui, reste dans `niveau_peut_merger` : la déclaration
        # dit « pas de CI », pas « ignore la CI ».
        if self._politique is not None and self._politique.merge_without_ci:
            etapes.append("CI : non attendue, déclarée absente")
            durees_ms.append(0.0)
            return await self._merger(pr_number, etapes, durees_ms, ticket_id)

        t0 = time.monotonic()
        ci = await self._attendre_la_ci(pr_number)
        ci_ms = (time.monotonic() - t0) * 1000
        etapes.append(f"CI : {ci}")
        durees_ms.append(ci_ms)

        if ci == "pending":
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
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
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=f"CI {ci} : la PR #{pr_number} reste ouverte.",
            )

        return await self._merger(pr_number, etapes, durees_ms, ticket_id)

    async def _merger(
        self,
        pr_number: int,
        etapes: list[str],
        durees_ms: list[float],
        ticket_id: str,
    ) -> Livraison:
        """Le dernier maillon, commun aux deux chemins de décision."""
        t0 = time.monotonic()
        merged = await self._workflow.merge_si_la_ci_est_verte(pr_number)
        merge_ms = (time.monotonic() - t0) * 1000
        if not merged:
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=f"GitHub a refusé le merge de la PR #{pr_number}.",
            )
        etapes.append(f"PR #{pr_number} mergée")
        durees_ms.append(merge_ms)
        _logger.info("livraison_complete", extra={"ticket": ticket_id, "pr": pr_number})
        return Livraison(
            etapes=tuple(etapes), durees_ms=tuple(durees_ms),
            pr_number=pr_number, merged=True,
        )

    async def _attendre_la_ci(self, pr_number: int) -> str:
        """Poll CI until a verdict, or until the wait bound.

        `none` is treated as `pending` during the grace period: GitHub
        registers checks only after the PR is opened, so an immediate poll
        returns `none` without any check having had time to appear.  Once the
        grace period has elapsed, `none` becomes a final verdict (ADR-029).
        `failing` always stops the wait immediately, even during grace.
        """
        ecoule = 0.0
        while True:
            etat = await self._workflow.etat_ci(pr_number)
            if etat == "none" and ecoule < self._grace_ci_s:
                # Dans le délai de grâce, on continue d'attendre comme si
                # la CI était en cours.
                pass
            elif etat not in ("pending", "none"):
                # Verdict définitif (passing, failing, …).
                return etat
            elif etat == "none":
                # Délai de grâce écoulé : none devient un verdict final.
                return etat
            # etat vaut "pending", ou "none" dans le délai de grâce.
            if ecoule >= self._attente_ci_max_s:
                return "pending"
            await self._dormir(self._intervalle_ci_s)
            ecoule += self._intervalle_ci_s
