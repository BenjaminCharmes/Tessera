"""Propose tickets to a project while a run holds its working tree — ticket-479.

The files are written in a temporary worktree cut from the remote base,
committed, pushed and put in a pull request. The main working tree of the
project is never the cwd of a command that writes: a run may be on its own
branch there, with a tree that must stay as the run left it (ADR-018).

The PR is merged only for a project declaring `autonomy: merge`, and then by
the CI watcher in the background (ADR-051): an HTTP request does not wait up
to fifteen minutes for a CI.
"""
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tessera.models.ticket import Ticket
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.ci_watcher import CI_WATCHER
from tessera.services.event_hub import EVENT_HUB
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService, PullRequestResult
from tessera.services.livraison import LivraisonService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.proposal_workspace import ProposalWorkspace
from tessera.services.racine_depot import GIT_ROOT_ANCESTOR
from tessera.services.temporary_worktree import detached_worktree, run_git
from tessera.services.ticket_service import validate_ticket


class ProposalRefused(Exception):
    """The proposal cannot be made; nothing was pushed."""


@dataclass(frozen=True)
class ProposalRequest:
    project_id: str
    project_path: Path
    #: (file name, file content), written as is under `tickets/todo/`.
    files: tuple[tuple[str, str], ...]
    policy: PolitiqueRun
    github: GitHubService
    base_branch: str


@dataclass(frozen=True)
class Proposal:
    branch: str
    pr_number: int
    pr_url: str
    ticket_ids: tuple[str, ...]
    merge_watched: bool


def validate_batch(files: tuple[tuple[str, str], ...]) -> list[Ticket]:
    """Validate every file with the loading rule; refuse duplicates in the batch."""
    if not files:
        raise ProposalRefused("Aucun ticket proposé.")
    tickets: list[Ticket] = []
    for name, content in files:
        try:
            tickets.append(validate_ticket(name, content))
        except ValueError as exc:
            raise ProposalRefused(str(exc)) from exc
    for label, series in (
        ("nom de fichier", [name for name, _ in files]),
        ("id", [ticket.id for ticket in tickets]),
    ):
        repeated = next((v for v in series if series.count(v) > 1), None)
        if repeated is not None:
            raise ProposalRefused(f"{label} en double dans le lot : {repeated}")
    return tickets


def _branch_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"tickets-propose-{stamp}-{secrets.token_hex(2)}"


def _check_free(project_dir: Path, tickets: list[Ticket]) -> None:
    """Refuse an id already used on the base, in any status folder, archive included."""
    root = project_dir / "tickets"
    for ticket in tickets:
        found = [*root.rglob(f"{ticket.id}.md"), *root.rglob(f"{ticket.id}-*.md")]
        if found:
            raise ProposalRefused(
                f"{ticket.id} existe déjà sur la base : {found[0].relative_to(project_dir)}"
            )


def _write(project_dir: Path, files: tuple[tuple[str, str], ...]) -> list[str]:
    """Write the files as received (no newline translation); return their paths."""
    folder = project_dir / "tickets" / "todo"
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in files:
        (folder / name).write_bytes(content.encode("utf-8"))
    return [f"tickets/todo/{name}" for name, _ in files]


def _workflow(request: ProposalRequest, git: ProposalWorkspace | None) -> GitHubWorkflowService:
    return GitHubWorkflowService(
        git_workspace=git,
        github=request.github,
        base_branch=request.base_branch,
        project_path=request.project_path,
        politique=request.policy,
    )


async def _deposit(
    request: ProposalRequest, root: Path, prefix: str, branch: str, tickets: list[Ticket]
) -> PullRequestResult:
    """Write, commit, push and open the PR, all inside the worktree."""
    project_dir = root / prefix if prefix else root
    _check_free(project_dir, tickets)
    paths = _write(project_dir, request.files)
    ids = ", ".join(t.id for t in tickets)
    await run_git(project_dir, "add", "--", *paths)
    await run_git(project_dir, "commit", "-m", f"chore: propose {ids}")
    workflow = _workflow(request, ProposalWorkspace(project_dir, request.policy))
    return await workflow.open_pull_request(
        branch=branch,
        ticket_id="tickets",
        ticket_title=f"propose {ids}",
        ticket_body="## Objectif\n\n" + "\n".join(f"- {t.id} — {t.title}" for t in tickets),
        ticket_type="chore",
        # Un geste demandé explicitement, comme `open-pr` : le niveau
        # d'autonomie borne ce que l'IDE fait seul, pas ce qu'on lui demande.
        autonome=False,
    )


async def _watch_merge(request: ProposalRequest, branch: str, pr_number: int) -> bool:
    """Hand the merge to the CI watcher, for `autonomy: merge` only."""
    if request.policy.autonomy is not NiveauAutonomie.merge:
        return False
    service = LivraisonService(
        git_workspace=GitWorkspaceService(request.project_path, politique=request.policy),
        workflow=_workflow(request, None),
        project_path=request.project_path,
        base_branch=request.base_branch,
        politique=request.policy,
    )
    # La branche sert d'identifiant : elle ne peut pas heurter celui d'un vrai
    # ticket. Aucun réalignement de la base locale : l'arbre principal reste
    # tel qu'il est, c'est tout l'objet de cette fonction.
    await CI_WATCHER.surveiller(
        request.project_id,
        branch,
        pr_number,
        service.livrer_phase_2,
        EVENT_HUB.publish,
        etat_pr=service.pr_state,
    )
    return True


async def propose_tickets(request: ProposalRequest) -> Proposal:
    """Open a PR adding the tickets to the remote base; see the module docstring."""
    tickets = validate_batch(request.files)
    if request.policy.artifacts != "tracked":
        raise ProposalRefused(
            "Les tickets de ce projet sont des artefacts locaux : ils ne se "
            'versionnent pas. Déclare `"artifacts": "tracked"` dans son agents.json.'
        )
    prefix = (await run_git(request.project_path, "rev-parse", "--show-prefix")).strip()
    if prefix and not request.policy.dans_le_depot_parent:
        raise ProposalRefused(
            "Ce projet n'est pas la racine de son dépôt git (ADR-024) : "
            f'déclare `"git_root": "{GIT_ROOT_ANCESTOR}"` pour y proposer des tickets.'
        )
    branch = _branch_name()
    await run_git(request.project_path, "fetch", "origin", request.base_branch)
    async with detached_worktree(
        request.project_path, f"origin/{request.base_branch}"
    ) as root:
        pr = await _deposit(request, root, prefix, branch, tickets)
    watched = await _watch_merge(request, branch, pr.pr_number)
    return Proposal(
        branch=branch,
        pr_number=pr.pr_number,
        pr_url=pr.pr_url,
        ticket_ids=tuple(t.id for t in tickets),
        merge_watched=watched,
    )
