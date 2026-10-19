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

import httpx

from tessera.config import settings
from tessera.services.autonomie import NiveauAutonomie, lire_niveau
from tessera.services.git_workspace import GitCommandError, GitWorkspaceError
from tessera.services.politique_run import PolitiqueRun
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
    #: Durée en millisecondes de chaque étape, dans le même ordre que `etapes`.
    #: `tuple[float, ...]` est JSON-sérialisable (devient une liste). (ticket-288)
    durees_ms: tuple[float, ...] = ()
    #: `None` quand la livraison est allée aussi loin que le projet l'autorise.
    arret: str | None = None
    conflits: tuple[str, ...] = ()
    pr_number: int | None = None
    merged: bool = False
    #: Vrai quand la phase 1 a levé **après** l'ouverture de la PR : `arret`
    #: porte alors une cause, mais la PR est bien ouverte et doit passer à la
    #: phase 2. Les autres arrêts avec PR (conflit résolu, ADR-033) restent
    #: sans surveillance. (ticket-415)
    pr_orpheline: bool = False
    #: Tête de la branche telle qu'elle est partie sur le distant : c'est elle
    #: que le watcher compare à la tête de la PR avant de merger (ticket-492).
    pushed_sha: str | None = None
    #: Vrai quand la branche ne porte plus le commit que le reviewer a lu :
    #: rien n'est poussé, le ticket est bloqué (ticket-492).
    branche_modifiee: bool = False


class LivraisonInterrompue(Exception):
    """Phase 1 failed after the PR was opened; carries its number and cause."""

    def __init__(self, pr_number: int, cause: Exception) -> None:
        super().__init__(f"PR #{pr_number} ouverte, puis {type(cause).__name__}")
        self.pr_number = pr_number
        self.cause = cause


class _Git(Protocol):
    async def rejouer_sur(
        self,
        base: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> tuple[str, ...]: ...
    async def sync_base_depuis_distant(self, base_branch: str) -> str | None: ...
    async def commit_bookkeeping(self) -> None: ...
    async def commits_hors_rangement(self, depuis: str) -> list[str]: ...
    async def sha_distant(self, branch: str) -> str | None: ...


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
    async def has_workflows(self) -> bool: ...
    async def pr_ouverte_de(self, branch: str) -> int | None: ...
    async def pr_state(self, pr_number: int) -> str: ...
    async def tete_pr(self, pr_number: int) -> str | None: ...
    async def merge_si_la_ci_est_verte(
        self, pr_number: int, sha_attendu: str | None = None
    ) -> bool: ...


class LivraisonService:
    def __init__(
        self,
        git_workspace: _Git,
        workflow: _Workflow,
        project_path: Path,
        base_branch: str,
        attente_ci_max_s: float = _ATTENTE_CI_MAX_S,
        intervalle_ci_s: float = _INTERVALLE_CI_S,
        grace_ci_s: float | None = None,
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
        # Sans valeur explicite, le réglage `CI_GRACE_S` (ticket-405).
        self._grace_ci_s = settings.ci_grace_s if grace_ci_s is None else grace_ci_s
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

    async def livrer_phase_1(
        self,
        *,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        ticket_type: str = "",
        branch: str | None,
        approuve: bool,
        approved_sha: str | None = None,
    ) -> Livraison:
        """Rebase, push, and open the PR.

        Returns a Livraison with pr_number set on success, or arret set if
        anything prevents opening the PR (unapproved, commit level, conflict).
        The CI wait and merge are handled by livrer_phase_2.

        With an `approved_sha`, every commit added since the approval must be
        the pipeline's own bookkeeping; otherwise nothing is pushed
        (ticket-492). The check runs before the rebase, which rewrites the
        commits the approval was given on.
        """
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

        if approved_sha is not None:
            changee = await self._branche_modifiee(approved_sha)
            if changee is not None:
                return changee

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
            if resolus:
                # La tentative figure au journal même quand elle échoue.
                etapes.append("résolveur tenté : " + ", ".join(resolus))
                durees_ms.append(rebase_ms)
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                conflits=conflits,
                arret=self._arret_conflit(conflits, resolus),
            )
        etapes.append(f"rebase sur {self._base_branch}")
        durees_ms.append(rebase_ms)
        if resolus:
            # La résolution est incluse dans la durée du rebase ci-dessus.
            etapes.append("conflit résolu : " + ", ".join(resolus))
            durees_ms.append(0.0)

        t0 = time.monotonic()
        try:
            resultat = await self._workflow.open_pull_request(
                branch=branch,
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                ticket_body=ticket_body,
                ticket_type=ticket_type,
            )
        except httpx.TransportError as exc:
            # La réponse a pu se perdre alors que la PR s'ouvrait (ticket-455).
            pr_perdue = await self._pr_ouverte_malgre(branch)
            if pr_perdue is None:
                raise
            raise LivraisonInterrompue(pr_perdue, exc) from exc
        pr_ms = (time.monotonic() - t0) * 1000
        pr_number = int(resultat.pr_number)
        etapes.append(f"PR #{pr_number} ouverte")
        durees_ms.append(pr_ms)

        # La PR existe : toute exception à partir d'ici porte son numéro, pour
        # que la phase 2 puisse quand même la reprendre (ticket-415).
        try:
            return await self._apres_ouverture(
                ticket_id, pr_number, branch, tuple(etapes), tuple(durees_ms), resolus
            )
        except Exception as exc:  # noqa: BLE001 — relevée avec le numéro de PR
            raise LivraisonInterrompue(pr_number, exc) from exc

    async def _branche_modifiee(self, approved_sha: str) -> Livraison | None:
        """The stop when the branch moved since the approval, else None.

        Fails closed (ADR-039): a branch that cannot be compared is a branch
        that changed.
        """
        try:
            intrus = await self._git.commits_hors_rangement(approved_sha)
        except GitWorkspaceError as exc:
            _logger.warning("comparaison_approbation_echouee", extra={"erreur": str(exc)})
            return Livraison(
                branche_modifiee=True,
                arret=(
                    "la branche n'a pas pu être comparée au commit approuvé "
                    f"{approved_sha[:7]} : {type(exc).__name__}"
                ),
            )
        if not intrus:
            return None
        return Livraison(
            branche_modifiee=True,
            arret=f"la branche a changé depuis l'approbation : {intrus[0][:7]}",
        )

    async def _sha_pousse(self, branch: str) -> str | None:
        """The head of `branch` on the remote; None when it cannot be read."""
        try:
            sha = await self._git.sha_distant(branch)
        except Exception as exc:  # noqa: BLE001 — sans lui, le watcher refuse de merger
            _logger.warning("sha_pousse_illisible", extra={"erreur": str(exc)})
            return None
        return sha if isinstance(sha, str) else None

    async def _pr_ouverte_malgre(self, branch: str) -> int | None:
        """Look for a PR already open on `branch` after a transport error.

        Never raises: a failing search keeps the original stop (ticket-455).
        """
        try:
            return await self._workflow.pr_ouverte_de(branch)
        except Exception as exc:  # noqa: BLE001 — la recherche ne masque pas l'erreur d'origine
            _logger.warning("recherche_pr_perdue_echouee", extra={"erreur": str(exc)})
            return None

    async def _apres_ouverture(
        self,
        ticket_id: str,
        pr_number: int,
        branch: str,
        etapes: tuple[str, ...],
        durees_ms: tuple[float, ...],
        resolus: list[str],
    ) -> Livraison:
        """What follows the PR opening: ticket note, then the verdict of phase 1."""
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

        return Livraison(
            etapes=tuple(etapes),
            durees_ms=tuple(durees_ms),
            pr_number=pr_number,
            arret=None,
            pushed_sha=await self._sha_pousse(branch),
        )

    async def livrer_phase_2(
        self,
        pr_number: int,
        *,
        ticket_id: str = "",
        sha_attendu: str | None = None,
    ) -> Livraison:
        """CI wait and merge.

        Called after livrer_phase_1 has opened the PR. Returns a Livraison
        with merged=True on success, or arret set if the CI fails or the
        project does not declare merge autonomy.

        With a `sha_attendu` (the pushed head), the head of the PR is read
        again after the CI verdict and the merge is bound to that commit: a
        push made during the CI wait never reaches the base (ticket-492).
        """
        etapes: list[str] = []
        durees_ms: list[float] = []

        niveau = (
            self._politique.autonomy
            if self._politique is not None
            else lire_niveau(self._project_path)
        )
        if niveau is not NiveauAutonomie.merge:
            # Nothing to do beyond the PR — project declared pr or commit.
            return Livraison(etapes=(), durees_ms=())

        # Attendre une CI que le projet déclare absente, c'est payer le délai
        # complet pour un verdict qui ne viendra pas (ADR-045). Le refus sur
        # une CI rouge, lui, reste dans `niveau_peut_merger` : la déclaration
        # dit « pas de CI », pas « ignore la CI ».
        if self._politique is not None and self._politique.merge_without_ci:
            etapes.append("CI : non attendue, déclarée absente")
            durees_ms.append(0.0)
            return await self._merger(
                pr_number, etapes, durees_ms, ticket_id, sha_attendu
            )

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
        if ci == "unreadable":
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=self._arret_ci_illisible(pr_number),
            )
        if ci == "conflicting":
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=(
                    f"PR #{pr_number} en conflit avec {self._base_branch} : "
                    "à rebaser. La PR reste ouverte."
                ),
            )
        if ci != "passing":
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=f"CI {ci} : la PR #{pr_number} reste ouverte.",
            )

        return await self._merger(
            pr_number, etapes, durees_ms, ticket_id, sha_attendu
        )

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
        """Porte le travail du ticket jusqu'où le projet le permet.

        Chains livrer_phase_1 (rebase, push, PR) and livrer_phase_2 (CI, merge).
        Existing callers use this method unchanged.
        """
        phase1 = await self.livrer_phase_1(
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            ticket_body=ticket_body,
            ticket_type=ticket_type,
            branch=branch,
            approuve=approuve,
        )
        # Stop here if phase 1 did not open a PR, or if it stopped on a conflict.
        if phase1.pr_number is None or phase1.arret is not None:
            return phase1

        phase2 = await self.livrer_phase_2(phase1.pr_number, ticket_id=ticket_id)

        # Merge the two phases: etapes and durees from both, other fields from phase2.
        return Livraison(
            etapes=phase1.etapes + phase2.etapes,
            durees_ms=phase1.durees_ms + phase2.durees_ms,
            pr_number=phase1.pr_number,
            merged=phase2.merged,
            conflits=phase1.conflits,
            arret=phase2.arret,
        )

    async def _merger(
        self,
        pr_number: int,
        etapes: list[str],
        durees_ms: list[float],
        ticket_id: str,
        sha_attendu: str | None = None,
    ) -> Livraison:
        """Le dernier maillon, commun aux deux chemins de décision.

        Avec `sha_attendu`, la tête de la PR se relit **ici**, après l'attente
        de la CI, et le merge y est lié (ticket-492).
        """
        if sha_attendu is not None:
            arret_tete = await self._tete_a_change(pr_number, sha_attendu)
            if arret_tete is not None:
                return Livraison(
                    etapes=tuple(etapes),
                    durees_ms=tuple(durees_ms),
                    pr_number=pr_number,
                    arret=arret_tete,
                )
        t0 = time.monotonic()
        if sha_attendu is None:
            merged = await self._workflow.merge_si_la_ci_est_verte(pr_number)
        else:
            merged = await self._workflow.merge_si_la_ci_est_verte(
                pr_number, sha_attendu=sha_attendu
            )
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

    async def _tete_a_change(self, pr_number: int, sha_attendu: str) -> str | None:
        """The stop line when the PR head is not `sha_attendu`, else None.

        Fails closed (ADR-039): an unreadable head refuses the merge.
        """
        try:
            tete = await self._workflow.tete_pr(pr_number)
        except Exception as exc:  # noqa: BLE001 — une tête illisible refuse le merge
            _logger.warning("tete_pr_illisible", extra={"erreur": str(exc)})
            tete = None
        if tete == sha_attendu:
            return None
        lue = tete[:7] if tete else "inconnue"
        return (
            f"la tête de la PR #{pr_number} n'est plus le commit poussé : "
            f"{lue} au lieu de {sha_attendu[:7]}. La PR reste ouverte."
        )

    def _arret_conflit(self, conflits: tuple[str, ...], resolus: list[str]) -> str:
        """The stop line of an unresolved conflict, saying what the resolver did.

        Sans cela, un résolveur jamais appelé et un résolveur tenté en échec
        donnent la même ligne (ticket-453).
        """
        message = f"Conflit avec {self._base_branch} sur : " + ", ".join(conflits)
        if self._resolveur is None:
            message += " — résolveur non tenté : aucun résolveur câblé sur cette livraison"
        elif resolus:
            raison = getattr(self._git, "raison_resolveur", None)
            message += (
                f" — résolveur tenté sur {', '.join(resolus)}, sans succès"
                + (f" : {raison}" if isinstance(raison, str) and raison else "")
            )
        else:
            message += " — résolveur non tenté : le rebase ne l'a pas appelé"
        return message + ". La branche est restée intacte, à toi de trancher."

    def _arret_ci_illisible(self, pr_number: int) -> str:
        """Le message d'arrêt quand le jeton ne peut pas lire la CI (ticket-449)."""
        code = getattr(self._workflow, "code_http_ci", None)
        precision = f" (HTTP {code})" if isinstance(code, int) else ""
        return (
            "Le jeton GitHub de Tessera ne peut pas lire la CI de ce dépôt"
            f"{precision} : il lui faut les permissions Actions et Commit "
            f"statuses en lecture. La PR #{pr_number} reste "
            "ouverte, rien n'est mergé."
        )

    async def _attendre_la_ci(self, pr_number: int) -> str:
        """Poll CI until a verdict, or until the wait bound.

        `unreadable` (the token cannot read the CI) is a final verdict like
        `failing`: waiting would never make it readable (ticket-449).

        `none` is treated as `pending` during the grace period: GitHub
        registers checks only after the PR is opened, so an immediate poll
        returns `none` without any check having had time to appear.  Once the
        grace period has elapsed, `none` becomes a final verdict (ADR-029)
        only if the repository declares no workflow at all; when workflows
        exist their checks are merely late, and `none` stays `pending` until
        the wait bound (ticket-405).
        `failing` always stops the wait immediately, even during grace.
        `conflicting` (the PR conflicts with its base) is final too: no CI
        verdict makes a conflicting PR mergeable (ticket-452).
        """
        ecoule = 0.0
        workflows_declares = False
        while True:
            etat = await self._workflow.etat_ci(pr_number)
            if etat not in ("pending", "none"):
                # Verdict définitif (passing, failing, …).
                return etat
            if etat == "none" and ecoule >= self._grace_ci_s:
                # Un workflow déclaré ne disparaît pas : on ne le redemande
                # plus une fois qu'on l'a vu.
                workflows_declares = (
                    workflows_declares or await self._workflow.has_workflows()
                )
                if not workflows_declares:
                    return etat
            # etat vaut "pending", ou "none" en attente de checks inscrits tard.
            if ecoule >= self._attente_ci_max_s:
                return "pending"
            await self._dormir(self._intervalle_ci_s)
            ecoule += self._intervalle_ci_s

    async def pr_state(self, pr_number: int) -> str:
        """The state of a PR (open, closed, merged, unknown) — ticket-405."""
        return await self._workflow.pr_state(pr_number)

    async def tete_pr(self, pr_number: int) -> str | None:
        """The head SHA of a PR, None when it cannot be known — ticket-492."""
        return await self._workflow.tete_pr(pr_number)
