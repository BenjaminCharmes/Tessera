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
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol

from tessera.config import settings
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.git_workspace import GitCommandError
from tessera.services.livraison.livraison_apres import branche_modifiee, ouvrir_avec_recours, pr_a_relire, sha_pousse
from tessera.services.livraison.livraison_arrets import ARRET_NON_APPROUVE, arret_ci_illisible, arret_conflit, arret_niveau_commit, arret_pr_en_conflit
from tessera.services.livraison.livraison_conflit import annoncer_fin_de_conflit, resolveur_suivi, signal_courant
from tessera.services.livraison.livraison_merge import arret_de_merge, tenter_le_merge, tete_a_change
from tessera.services.livraison.livraison_rebase import noter_ce_que_le_rebase_a_fait, retester_apres_rebase, tete_avant_rebase
from tessera.services.livraison.livraison_resultat import Livraison as Livraison
from tessera.services.livraison.renumeroter import etape_de_numerotation
from tessera.services.livraison.retest_apres_rebase import RetestApresRebase
from tessera.services.projets.autonomie import NiveauAutonomie, lire_niveau
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Intervalle entre deux interrogations de la CI. Assez court pour ne pas
#: laisser traîner un ticket, assez long pour ne pas marteler l'API.
_INTERVALLE_CI_S = 15.0
#: Au-delà, on rend la main : avec le job E2E, la CI prend une vingtaine de
#: minutes ; une attente sans borne bloquerait la file de tickets (ADR-018).
_ATTENTE_CI_MAX_S = 2100.0


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
    async def head_sha(self) -> str: ...
    async def remettre_sur(self, sha: str) -> None: ...


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
        retest: RetestApresRebase | None = None,
        renumeroter: Callable[[], Awaitable[tuple[str, ...]]] | None = None,
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
        # Rejoue les tests quand le rebase ramène des commits (ticket-568).
        self._retest = retest
        # Renumérote ce que le diff ajoute et que la base porte déjà (ticket-659).
        self._renumeroter = renumeroter

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
        if not approuve:
            return Livraison(arret=ARRET_NON_APPROUVE)
        if branch is None:
            return Livraison(arret="Aucune branche : rien à livrer.")
        arret_niveau = self._arret_de_niveau(branch)
        if arret_niveau is not None:
            return arret_niveau

        etapes: list[str] = []
        durees_ms: list[float] = []
        resolus: list[str] = []
        arret_base = await self._preparer_la_base(approved_sha, etapes, durees_ms)
        if arret_base is not None:
            return arret_base

        # Avant le rebase : après lui, la base est toujours ancêtre de HEAD.
        retest = self._retest
        avancee = retest is not None and await retest.base_a_avance(self._base_branch)
        sha_avant = await tete_avant_rebase(self._git) if avancee else None  # ticket-740
        arret_rebase = await self._rebaser(etapes, durees_ms, resolus)
        if arret_rebase is not None:
            return arret_rebase
        arret_retest = await retester_apres_rebase(
            self._git, retest if avancee else None, self._base_branch,
            sha_avant, resolus, etapes, durees_ms,
        )
        if arret_retest is not None:
            return Livraison(
                etapes=tuple(etapes), durees_ms=tuple(durees_ms), arret=arret_retest
            )

        pr_number = await self._ouvrir_la_pr(
            branch, ticket_id, ticket_title, ticket_body, ticket_type, etapes, durees_ms
        )
        # La PR existe : toute exception à partir d'ici porte son numéro, pour
        # que la phase 2 puisse quand même la reprendre (ticket-415).
        try:
            return await self._apres_ouverture(
                ticket_id, pr_number, branch, tuple(etapes), tuple(durees_ms), resolus
            )
        except Exception as exc:  # noqa: BLE001 — relevée avec le numéro de PR
            raise LivraisonInterrompue(pr_number, exc) from exc

    def _arret_de_niveau(self, branch: str) -> Livraison | None:
        """The stop when the project declares the commit level, else None."""
        niveau = (
            self._politique.autonomy
            if self._politique is not None
            else lire_niveau(self._project_path)
        )
        if niveau is NiveauAutonomie.commit:
            return Livraison(arret=arret_niveau_commit(branch), arret_voulu=True)
        return None

    async def _preparer_la_base(
        self, approved_sha: str | None, etapes: list[str], durees_ms: list[float]
    ) -> Livraison | None:
        """Sync the base, tidy the bookkeeping, check the approval and the numbering."""
        # Align local base_branch with remote before rebase (ticket-285).
        # Non-blocking: a failed sync falls back to the current local branch.
        await self._git.sync_base_depuis_distant(self._base_branch)

        # Commite les artefacts de tenue de livres en attente (pipeline-log,
        # statuts de tickets) avant le rebase : `git rebase` exige un arbre
        # entièrement propre, sans exception, alors qu'`is_clean` tolère ces
        # chemins pour ne pas bloquer le ticket suivant (ticket-303).
        await self._git.commit_bookkeeping()

        if approved_sha is not None:
            changee = await branche_modifiee(self._git, approved_sha)
            if changee is not None:
                return changee

        # Après le contrôle de l'approbation, qui refuserait ce commit de code,
        # et avant le rebase, qui n'a pas à rejouer des numéros déjà pris.
        arret = await etape_de_numerotation(self._renumeroter, etapes, durees_ms)
        if arret is None:
            return None
        return Livraison(etapes=tuple(etapes), durees_ms=tuple(durees_ms), arret=arret)

    async def _rebaser(
        self, etapes: list[str], durees_ms: list[float], resolus: list[str]
    ) -> Livraison | None:
        """Replay the branch on the base; the stop on refusal or conflict, else None."""
        # Le résolveur ne dit pas s'il a réussi : c'est `rejouer_sur` qui
        # tranche, en vérifiant l'arbre. On note seulement qu'il a tourné.
        signal = signal_courant()
        resoudre = resolveur_suivi(resolus, self._resolveur, signal)
        t0 = time.monotonic()
        try:
            conflits = await self._git.rejouer_sur(self._base_branch, resolveur=resoudre)
        except GitCommandError as exc:
            # Le rebase a refusé de démarrer — arbre sale (fichier de code
            # modifié non commité), base inconnue ou autre erreur git.
            # `commit_bookkeeping` a déjà commité les artefacts Tessera : ce
            # qui reste est du code que le pipeline n'a pas produit.
            await annoncer_fin_de_conflit(signal, resolus, annule=True)
            raison = exc.stderr.strip() or str(exc)
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                arret=f"Rebase refusé : {raison}",
            )
        rebase_ms = (time.monotonic() - t0) * 1000
        await annoncer_fin_de_conflit(signal, resolus, annule=bool(conflits))
        if conflits:
            return self._arret_de_conflit(conflits, resolus, rebase_ms, etapes, durees_ms)
        etapes.append(f"rebase sur {self._base_branch}")
        durees_ms.append(rebase_ms)
        noter_ce_que_le_rebase_a_fait(self._git, etapes, durees_ms, resolus)
        if resolus:
            # La résolution est incluse dans la durée du rebase ci-dessus.
            etapes.append("conflit résolu : " + ", ".join(resolus))
            durees_ms.append(0.0)
        return None

    def _arret_de_conflit(
        self,
        conflits: tuple[str, ...],
        resolus: list[str],
        rebase_ms: float,
        etapes: list[str],
        durees_ms: list[float],
    ) -> Livraison:
        """The stop on a rebase that left conflicts."""
        if resolus:
            # La tentative figure au journal même quand elle échoue.
            etapes.append("résolveur tenté : " + ", ".join(resolus))
            durees_ms.append(rebase_ms)
        return Livraison(
            etapes=tuple(etapes),
            durees_ms=tuple(durees_ms),
            conflits=conflits,
            arret=arret_conflit(
                self._base_branch, conflits, resolus, self._resolveur is not None,
                getattr(self._git, "raison_resolveur", None),
            ),
        )

    async def _ouvrir_la_pr(
        self,
        branch: str,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        ticket_type: str,
        etapes: list[str],
        durees_ms: list[float],
    ) -> int:
        """Open the PR and note it; a lost response or a 5xx is survived (ticket-455, 781)."""
        t0 = time.monotonic()

        async def ouvrir() -> Any:
            return await self._workflow.open_pull_request(
                branch=branch,
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                ticket_body=ticket_body,
                ticket_type=ticket_type,
            )

        pr_number, perdue = await ouvrir_avec_recours(
            ouvrir, self._workflow, branch, etapes, self._dormir
        )
        if perdue is not None:
            raise LivraisonInterrompue(pr_number, perdue) from perdue
        etapes.append(f"PR #{pr_number} ouverte")
        durees_ms.append((time.monotonic() - t0) * 1000)
        return pr_number

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
            return pr_a_relire(pr_number, etapes, durees_ms, resolus)
        return Livraison(
            etapes=etapes,
            durees_ms=durees_ms,
            pr_number=pr_number,
            arret=None,
            pushed_sha=await sha_pousse(self._git, branch),
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
                arret=arret_ci_illisible(
                    getattr(self._workflow, "code_http_ci", None), pr_number
                ),
            )
        if ci == "conflicting":
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=arret_pr_en_conflit(pr_number, self._base_branch),
                a_mettre_a_jour=True,
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
            arret_tete = await tete_a_change(self._workflow, pr_number, sha_attendu)
            if arret_tete is not None:
                return Livraison(
                    etapes=tuple(etapes),
                    durees_ms=tuple(durees_ms),
                    pr_number=pr_number,
                    arret=arret_tete,
                )
        t0 = time.monotonic()
        issue = await tenter_le_merge(self._workflow, pr_number, sha_attendu)
        merge_ms = (time.monotonic() - t0) * 1000
        if not issue.merged:
            return Livraison(
                etapes=tuple(etapes),
                durees_ms=tuple(durees_ms),
                pr_number=pr_number,
                arret=arret_de_merge(pr_number, issue),
            )
        etapes.append(
            f"PR #{pr_number} mergée — confirmée après une erreur réseau"
            if issue.confirme_apres_reseau
            else f"PR #{pr_number} mergée"
        )
        durees_ms.append(merge_ms)
        _logger.info("livraison_complete", extra={"ticket": ticket_id, "pr": pr_number})
        return Livraison(
            etapes=tuple(etapes), durees_ms=tuple(durees_ms),
            pr_number=pr_number, merged=True,
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
