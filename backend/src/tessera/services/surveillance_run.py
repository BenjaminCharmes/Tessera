"""Phase 2 of a run's delivery and the GitHub reads the orchestrator relies on."""

from collections.abc import Awaitable, Callable

from tessera.config import settings
from tessera.services.agent_runner import AgentRunner
from tessera.services.ci_watcher import ControleTete, EstAncetre, TetePr
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.livraison import Livraison, LivraisonService
from tessera.services.pipeline_events import EventCallback
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import load_project
from tessera.services.realignement_base import Realignement
from tessera.services.reprise_surveillance import SurveillanceProjet
from tessera.services.resolveur_conflit import ResolveurConflitService
from tessera.services.run_worktree import RunWorktree
from tessera.services.sha_approbation import sha_pousse_du_ticket
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def controle_tete_de(
    project_id: str,
    ticket_id: str,
    lire_tete: TetePr,
    est_ancetre: EstAncetre | None = None,
) -> ControleTete:
    """The check the watcher makes before merging a PR (ticket-492, 527)."""
    try:
        pushed = await sha_pousse_du_ticket(settings.ide_db_path, project_id, ticket_id)
    except Exception as exc:  # noqa: BLE001 — sans SHA, le watcher refuse de merger
        _logger.warning("pushed_sha_illisible", extra={"erreur": str(exc)})
        pushed = None
    return ControleTete(pushed_sha=pushed, lire_tete=lire_tete, est_ancetre=est_ancetre)


def surveillance_pour(
    project_id: str,
    runner: AgentRunner | None = None,
    politique: PolitiqueRun | None = None,
    espace: GitWorkspaceService | None = None,
    wt: RunWorktree | None = None,
) -> Callable[[str, str, int, EventCallback], Awaitable[None]]:
    """Fabrique le callback `surveiller` pour l'orchestrateur (ADR-051).

    Retourne une coroutine qui démarre la phase 2 (attente CI + merge) en
    tâche de fond via `CI_WATCHER.surveiller`. Retourne immédiatement, sans
    attendre la fin de la CI.

    Avec un worktree (ADR-056), la phase 2 ne lit ni n'écrit aucun arbre : le
    worktree est supprimé avant qu'elle ne finisse, et le checkout n'appartient
    pas au run. Ni réalignement de la base locale, ni ligne de journal sur disque.
    """
    from tessera.services.ci_watcher import CI_WATCHER

    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    base_branch = (
        politique.base_branch if politique else None
    ) or settings.github_base_branch

    service = LivraisonService(
        git_workspace=GitWorkspaceService(project_path, politique=politique),
        workflow=GitHubWorkflowService(
            git_workspace=GitWorkspaceService(project_path, politique=politique),
            github=github,
            base_branch=base_branch,
            project_path=project_path,
            politique=politique,
        ),
        project_path=project_path,
        base_branch=base_branch,
        politique=politique,
        resolveur=(
            ResolveurConflitService(runner, project_path).resoudre
            if runner is not None
            else None
        ),
    )

    pipeline_log_path_ci = None if wt is not None else project_path / "memory" / "pipeline-log.md"
    realignement = None if wt is not None else Realignement(project_path, base_branch)

    async def surveiller(
        p_id: str,
        ticket_id: str,
        pr_number: int,
        on_event: EventCallback,
    ) -> None:
        """Start CI watching for pr_number in a background task."""
        controle = await controle_tete_de(
            p_id, ticket_id, service.tete_pr,
            GitWorkspaceService(project_path, politique=politique).est_ancetre,
        )

        async def phase_2(pr: int) -> Livraison:
            # Le merge est lié au commit poussé : une tête qui bouge pendant
            # l'attente de la CI ne part jamais sur la base (ticket-492).
            return await service.livrer_phase_2(pr, sha_attendu=controle.pushed_sha)

        await CI_WATCHER.surveiller(
            p_id,
            ticket_id,
            pr_number,
            phase_2,
            on_event,
            pipeline_log_path=pipeline_log_path_ci,
            etat_pr=service.pr_state,
            realignement=realignement,
            controle_tete=controle,
        )

    return surveiller


def lecteur_etat_pr(
    project_id: str, politique: PolitiqueRun | None = None
) -> Callable[[int], Awaitable[str]]:
    """Fabrique la relecture de l'état d'une PR, donnée à la file.

    La file s'en sert quand le watcher n'a pas inscrit le ticket dont dépend
    le suivant : elle relit la PR au lieu de la supposer mergée. Sans dépôt
    GitHub déclaré, la relecture rend `unknown`, donc « pas mergé ».
    """
    return workflow_de_lecture(project_id, politique).pr_state


def surveillance_de_reprise(
    project_id: str, politique: PolitiqueRun
) -> SurveillanceProjet:
    """Ce que la reprise au démarrage utilise pour un projet (ticket-510).

    La même fabrique que la livraison : une PR reprise passe par `surveiller`
    avec ses règles — CI verte, `merge_without_ci`, tête inchangée.
    """
    lecture = workflow_de_lecture(project_id, politique)
    return SurveillanceProjet(
        etat_pr=lecture.pr_state,
        surveiller=surveillance_pour(project_id, politique=politique),
        prs_ouvertes=lecture.prs_ouvertes,
        base_branch=lecture.base_branch,
    )


def chercheur_pr_mergee(
    project_id: str, politique: PolitiqueRun | None = None
) -> Callable[[str], Awaitable[int | None]]:
    """Fabrique la recherche d'une PR mergée par préfixe de branche (ticket-482).

    Sans dépôt GitHub déclaré, la recherche ne trouve rien : le ticket reste
    bloqué.
    """
    return workflow_de_lecture(project_id, politique).pr_mergee_de_branche


def workflow_de_lecture(
    project_id: str, politique: PolitiqueRun | None
) -> GitHubWorkflowService:
    """Le service GitHub dont l'orchestrateur ne se sert qu'en lecture."""
    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)
    base_branch = (
        politique.base_branch if politique else None
    ) or settings.github_base_branch
    return GitHubWorkflowService(
        git_workspace=GitWorkspaceService(project_path, politique=politique),
        github=github,
        base_branch=base_branch,
        project_path=project_path,
        politique=politique,
    )
