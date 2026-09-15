"""Agent de workflow GitHub — ticket-064."""
from pathlib import Path

import pytest

from vibe_ide.services.github_workflow import (
    GitHubWorkflowService,
    WorkflowError,
    build_pr_body,
)


class _FakeGit:
    def __init__(self, branch: str | None = "ticket-042-slug") -> None:
        self.branch = branch
        self.pushed: list[str] = []
        self.rebased: list[str] = []
        self.conflicts: list[str] = []

    async def push_branch(self, branch_name: str) -> None:
        self.pushed.append(branch_name)

    async def current_diff(self) -> str:
        return "diff --git a/x.py b/x.py\n+x = 1\n"


class _FakeGitHub:
    def __init__(self, pr: tuple[int, str] = (7, "https://github.com/o/r/pull/7")) -> None:
        self.pr = pr
        self.created: list[dict[str, object]] = []

    async def create_pull_request(self, **kwargs: object) -> tuple[int, str]:
        self.created.append(kwargs)
        return self.pr


def _ticket_body() -> str:
    return (
        "# ticket-042 — Endpoint de santé\n\n"
        "## Objectif\n\nExposer /health.\n\n"
        "## Critères d'acceptation\n\n- [ ] 200 sur /health\n"
    )


# ------------------------------------------------------------------
# Corps de la PR
# ------------------------------------------------------------------


def test_le_corps_de_pr_reprend_l_objectif_du_ticket() -> None:
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())

    assert "Exposer /health" in body
    assert "ticket-042" in body


def test_le_corps_de_pr_ne_porte_aucune_trace_d_ia() -> None:
    # ticket-060 : ce texte part dans le dépôt de l'utilisateur.
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())

    lowered = body.lower()
    for trace in ("co-authored-by", "claude", "generated with", "ia ", " ai "):
        assert trace not in lowered, trace


def test_le_corps_de_pr_reprend_les_criteres_d_acceptation() -> None:
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())
    assert "200 sur /health" in body


# ------------------------------------------------------------------
# Ouvrir une PR
# ------------------------------------------------------------------


async def test_pousse_la_branche_avant_d_ouvrir_la_pr(tmp_path: Path) -> None:
    # L'ordre est le correctif : GitHub refuse une `head` qu'il ne connaît pas.
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(git_workspace=git, github=github, base_branch="develop")

    result = await svc.open_pull_request(
        branch="ticket-042-slug",
        ticket_id="ticket-042",
        ticket_title="Endpoint de santé",
        ticket_body=_ticket_body(),
    )

    assert git.pushed == ["ticket-042-slug"]
    assert result.pr_number == 7
    assert github.created[0]["head"] == "ticket-042-slug"
    assert github.created[0]["base"] == "develop"


async def test_sans_branche_l_ouverture_est_refusee(tmp_path: Path) -> None:
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(), github=_FakeGitHub(), base_branch="develop"
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch=None, ticket_id="ticket-042", ticket_title="T", ticket_body=""
        )

    assert "branche" in str(exc.value).lower()


async def test_sans_github_configure_l_ouverture_est_refusee() -> None:
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(), github=None, base_branch="develop"
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="b", ticket_id="ticket-042", ticket_title="T", ticket_body=""
        )

    assert "github" in str(exc.value).lower()


# ------------------------------------------------------------------
# Ce que l'agent ne fait jamais
# ------------------------------------------------------------------


def test_le_service_n_expose_aucun_merge() -> None:
    # Merger, c'est décider qu'un travail est bon. C'est le seul point où un
    # humain tranche, et c'est ce qui rend le reste de l'automatisation
    # acceptable.
    public = [n for n in dir(GitHubWorkflowService) if not n.startswith("_")]

    assert not any("merge" in n.lower() for n in public), public


def test_aucun_appel_de_merge_dans_le_code() -> None:
    import inspect

    from vibe_ide.services import github_workflow

    source = inspect.getsource(github_workflow).lower()
    # Les mentions en commentaire sont attendues ; les appels ne le sont pas.
    code_lines = [
        line for line in source.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    for line in code_lines:
        assert "merge(" not in line, line
        assert '"merge"' not in line, line
