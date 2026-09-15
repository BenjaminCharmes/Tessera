"""Workflow GitHub d'un ticket : pousser, ouvrir la PR, suivre la CI — ticket-064.

Ce service couvre la mécanique qui entoure une PR, et **jamais le merge**.

Merger, c'est décider qu'un travail est bon. C'est le seul point du pipeline
où un humain tranche, et c'est précisément ce qui rend acceptable tout le
reste de l'automatisation. Un agent qui mergerait rendrait la relecture
facultative.

Le maillon que ce module ajoute est le push. `create-pr` demandait à GitHub une
branche `head` que rien n'avait jamais poussée : la fonctionnalité n'avait
jamais pu aboutir.
"""
import re
from dataclasses import dataclass
from typing import Optional, Protocol

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)


class WorkflowError(Exception):
    """Une opération de workflow a été refusée."""


@dataclass(frozen=True)
class PullRequestResult:
    pr_number: int
    pr_url: str
    branch: str


class _GitWorkspace(Protocol):
    async def push_branch(self, branch_name: str) -> None: ...
    async def current_diff(self) -> str: ...


class _GitHub(Protocol):
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str | None = None,
    ) -> tuple[int, str]: ...


def _section(ticket_body: str, heading: str) -> str:
    """Extrait une section `## <heading>` du corps d'un ticket."""
    pattern = re.compile(
        rf"^##\s*{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(ticket_body or "")
    return match.group(1).strip() if match else ""


def build_pr_body(ticket_id: str, ticket_title: str, ticket_body: str) -> str:
    """Rédige le corps de la PR depuis le ticket.

    Aucune mention d'outil d'IA (ticket-060) : ce texte part dans le dépôt de
    l'utilisateur, parfois celui d'un client.
    """
    parts = [f"Ticket **{ticket_id}** — {ticket_title}"]

    objectif = _section(ticket_body, "Objectif")
    if objectif:
        parts.append(f"## Objectif\n\n{objectif}")

    criteres = _section(ticket_body, "Critères d'acceptation")
    if criteres:
        parts.append(f"## Critères d'acceptation\n\n{criteres}")

    return "\n\n".join(parts) + "\n"


class GitHubWorkflowService:
    """Pousse une branche et ouvre sa PR. N'expose aucune action de merge."""

    def __init__(
        self,
        git_workspace: Optional[_GitWorkspace],
        github: Optional[_GitHub],
        base_branch: str,
    ) -> None:
        self._git = git_workspace
        self._github = github
        self._base_branch = base_branch

    async def open_pull_request(
        self,
        *,
        branch: str | None,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
    ) -> PullRequestResult:
        """Pousse la branche **puis** ouvre la PR.

        L'ordre est le correctif : GitHub refuse une `head` qu'il ne connaît
        pas, et rien ne poussait jusqu'ici.
        """
        if self._git is None:
            raise WorkflowError("Ce projet n'a pas de dépôt git utilisable.")
        if branch is None:
            raise WorkflowError(
                "Aucune branche à pousser : lance d'abord le pipeline sur ce ticket."
            )
        if self._github is None:
            raise WorkflowError(
                "GitHub n'est pas configuré pour ce projet : il faut un "
                "GITHUB_TOKEN et un dépôt distant lié."
            )

        await self._git.push_branch(branch)

        pr_number, pr_url = await self._github.create_pull_request(
            title=f"{ticket_id} — {ticket_title}",
            body=build_pr_body(ticket_id, ticket_title, ticket_body),
            head=branch,
            base=self._base_branch,
        )
        _logger.info(
            "pull_request_opened",
            extra={"ticket_id": ticket_id, "pr_number": pr_number, "branch": branch},
        )
        return PullRequestResult(pr_number=pr_number, pr_url=pr_url, branch=branch)
