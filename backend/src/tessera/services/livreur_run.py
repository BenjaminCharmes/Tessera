"""Phase 1 of a run's delivery — rebase, push, PR — built from the project's declarations."""

from collections.abc import Awaitable, Callable
from dataclasses import replace

from tessera.config import settings
from tessera.services.agent_runner import AgentRunner
from tessera.services.attente_des_merges import apres_les_merges
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.livraison import Livraison, LivraisonInterrompue, LivraisonService
from tessera.services.orchestrator import PipelineResult
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import load_project
from tessera.services.renumeroter import Renumeroteur
from tessera.services.resolveur_conflit import ResolveurConflitService
from tessera.services.retest_apres_rebase import RetestApresRebase
from tessera.services.run_worktree import RunWorktree
from tessera.services.sha_approbation import noter_poussee
from tessera.services.ticket_service import TicketService
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def livraison_interrompue(exc: Exception) -> Livraison:
    """Turn an exception of phase 1 into a Livraison that names its cause.

    Si la PR était déjà ouverte (`LivraisonInterrompue`), son numéro est gardé
    et la livraison est marquée pour la phase 2 : la PR ne reste pas orpheline.
    """
    cause = exc.cause if isinstance(exc, LivraisonInterrompue) else exc
    motif = decrire_exception(cause)
    _logger.warning(
        "livraison_echouee",
        exc_info=cause,
        extra={"erreur": motif, "pr": getattr(exc, "pr_number", None)},
    )
    arret = f"Livraison interrompue : {motif}"
    if not isinstance(exc, LivraisonInterrompue):
        return Livraison(arret=arret)
    return Livraison(
        etapes=(f"PR #{exc.pr_number} ouverte",),
        durees_ms=(0.0,),
        arret=arret,
        pr_number=exc.pr_number,
        pr_orpheline=True,
    )


async def sync_apres_livraison(
    livraison: Livraison,
    espace: GitWorkspaceService | None,
    politique: PolitiqueRun | None,
    base_branch: str,
) -> Livraison:
    """Sync the base ref with the remote after a delivery attempt.

    Toujours appelé après la phase 1 (succès ou exception), pour que le
    ticket suivant forke depuis `origin/<base>` et non depuis la pointe du
    ticket précédent (ADR-051).

    Cas couverts :
    - PR ouverte : `advance_base_ref()` a été appelé dans `_noter_et_pousser`
      → le sync remet `_base_ref` sur la base distante.
    - Phase 1 échouée sans PR (exception, rebase refusé) : `advance_base_ref()`
      n'a pas été appelé, mais la base distante est la bonne référence.
    - Merge (squash) : `_base_ref` pointe sur la pointe du ticket, pas sur le
      squash commit → le sync corrige le décalage (ticket-264).

    Sur un projet `commit` (pas de push), la sync est sans effet : il n'y a
    pas de distante à rejoindre.
    """
    if espace is None:
        return livraison
    # Projets commit-only : pas de distante, la sync est sans effet
    # et ne doit pas être appelée (ticket-307).
    if politique is not None and politique.autonomy is NiveauAutonomie.commit:
        return livraison
    needs_sync = (
        livraison.merged
        or livraison.pr_number is not None
        or livraison.arret is not None
    )
    if not needs_sync:
        return livraison
    raison = await espace.sync_base_depuis_distant(base_branch)
    if raison is None:
        return livraison
    # Une PR orpheline garde la cause de son interruption : la raison de la
    # sync s'y ajoute au lieu de l'effacer (ticket-415).
    arret = f"{livraison.arret} ; {raison}" if livraison.pr_orpheline else raison
    return replace(livraison, arret=arret)


async def noter_sha_pousse(result: PipelineResult, livraison: Livraison) -> None:
    """Record the pushed head on the run's row, for the watcher (ticket-492).

    Un échec d'écriture est journalisé : le watcher, sans SHA poussé, refusera
    de merger — la PR reste ouverte, rien ne part sous une approbation périmée.
    """
    if livraison.pushed_sha is None or result.run_id is None:
        return
    try:
        await noter_poussee(settings.ide_db_path, result.run_id, livraison.pushed_sha)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("pushed_sha_non_note", extra={"erreur": str(exc)})


def livreur(
    project_id: str,
    runner: AgentRunner | None = None,
    politique: PolitiqueRun | None = None,
    espace: GitWorkspaceService | None = None,
    wt: RunWorktree | None = None,
    retest: RetestApresRebase | None = None,
) -> Callable[[PipelineResult], Awaitable[Livraison]]:
    """Fabrique la livraison de phase 1 d'un projet (ADR-051).

    Phase 1 seulement : rebase, push, PR, une fois mergées les PR déjà confiées
    au watcher (ticket-533). La phase 2 (CI, merge) est celle de `CIWatcher`.
    `espace` est l'espace git de l'orchestrateur : celui dont la base sert
    de départ au ticket suivant de la file.

    Une livraison qui échoue ne fait **pas** échouer le run : le travail est
    commité, et perdre la réponse du pipeline parce que GitHub est injoignable
    ferait croire que c'est le pipeline qui a échoué. Le motif remonte dans
    `livraison.arret`, là où l'utilisateur le lira.
    """
    dossier_reel = settings.ide_workspace_dir / project_id
    project = load_project(dossier_reel)
    # Dans un worktree (ADR-056), tout ce que la livraison lit ou écrit est le
    # pendant du projet dans ce worktree.
    project_path = wt.projet if wt is not None else dossier_reel
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    # La branche de base dépend du dépôt, pas de la machine — même raison
    # qu'ADR-029 pour l'autonomie. Le réglage global reste le repli des
    # projets qui ne déclarent rien (ticket-166).
    base_branch = (
        politique.base_branch if politique else None
    ) or settings.github_base_branch

    ticket_svc = TicketService(project_path, project_id)

    async def _noter_et_pousser(ticket_id: str, pr_number: int, branch: str) -> None:
        """Write pr_number, commit and push before any merge (ticket-270).

        Called after opening the PR but before any merge, so the bookkeeping
        commit for the PR number is on the remote and no commit is stranded on
        the ticket branch after a merged PR.  Without this number the ticket
        card would keep offering to open a PR on already-merged work (ticket-205).
        A write failure never undoes an already-opened PR: it is logged instead.
        """
        try:
            await ticket_svc.set_pr_number(ticket_id, pr_number)
            git_espace = espace or GitWorkspaceService(project_path, politique=politique, worktree=wt)
            await git_espace.commit_bookkeeping()
            await git_espace.push_branch(branch)
        except Exception as exc:  # noqa: BLE001 — même raison que la livraison
            _logger.warning("pr_non_notee", extra={"erreur": str(exc)})

    service = LivraisonService(
        git_workspace=GitWorkspaceService(project_path, politique=politique, worktree=wt),
        workflow=GitHubWorkflowService(
            git_workspace=GitWorkspaceService(project_path, politique=politique, worktree=wt),
            github=github,
            base_branch=base_branch,
            project_path=project_path,
            politique=politique,
        ),
        project_path=project_path,
        base_branch=base_branch,
        politique=politique,
        # Sans runner — appel programmatique, test — pas de résolveur : le
        # conflit annule le rebase et remonte, comme avant ticket-090.
        resolveur=(
            ResolveurConflitService(runner, project_path).resoudre
            if runner is not None
            else None
        ),
        post_pr_callback=_noter_et_pousser,
        retest=retest,
        renumeroter=Renumeroteur(GitWorkspaceService(project_path, politique=politique, worktree=wt), project_path, base_branch),
    )

    async def livrer(result: PipelineResult) -> Livraison:
        """Phase 1 seulement : rebase, push, PR. Syncing remote base after."""
        ticket = await ticket_svc.get_ticket(result.ticket_id)
        livraison: Livraison
        try:
            livraison = await service.livrer_phase_1(
                ticket_id=result.ticket_id,
                ticket_title=ticket.title if ticket else result.ticket_id,
                ticket_body=ticket.body if ticket else "",
                ticket_type=ticket.type.value if ticket else "",
                branch=result.branch,
                approuve=result.approved,
                approved_sha=result.approved_sha,
            )
        except Exception as exc:  # noqa: BLE001 — voir la docstring
            livraison = livraison_interrompue(exc)
        await noter_sha_pousse(result, livraison)
        # Syncing is always attempted so the next ticket forks from origin/<base>
        # regardless of whether this phase 1 succeeded or failed (ADR-051).
        livraison = await sync_apres_livraison(livraison, espace, politique, base_branch)
        return livraison

    return apres_les_merges(livrer, project_id)
