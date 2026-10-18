"""Proposer des tickets sans toucher l'arbre d'un run — ticket-479.

Vrais dépôts git : un origin nu, un clone qui joue le projet, et une fausse API
GitHub. Rien ne passe par le réseau.
"""
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.ci_watcher import CI_WATCHER
from tessera.services.git_workspace import GitCommandError
from tessera.services.github_service import GitHubService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.ticket_proposal import (
    ProposalRefused,
    ProposalRequest,
    propose_tickets,
)


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return done.stdout


@dataclass
class Env:
    origin: Path
    repo: Path
    project: Path


class FakeGitHub:
    def __init__(self, on_create: Callable[[], None] | None = None) -> None:
        self.calls: list[tuple[str, str, str | None]] = []
        self._on_create = on_create

    async def create_pull_request(
        self, title: str, body: str, head: str, base: str | None = None
    ) -> tuple[int, str]:
        self.calls.append((title, head, base))
        if self._on_create is not None:
            self._on_create()
        return 7, "https://example.test/pull/7"


def _ticket(n: int, type_: str = "chore") -> tuple[str, str]:
    return f"ticket-{n:03d}-demo.md", (
        f'---\nid: ticket-{n:03d}\ntitle: "Demo {n}"\ntype: {type_}\n'
        "status: todo\npriority: medium\nagent: codeur\n---\n\n# Demo\n"
    )


@pytest.fixture(autouse=True)
def _git_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
    # Un fichier vide, pas `os.devnull` : git sous Windows lit « NUL » comme un fichier.
    vide = tmp_path / "gitconfig-vide"
    vide.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(vide))


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    return ws


def _build(ws: Path, *, autonomy: str = "commit", ancestor: bool = False,
           artifacts: str = "tracked") -> Env:
    origin = ws.parent / "origin.git"
    _git(ws.parent, "init", "--bare", "--initial-branch=develop", str(origin))
    repo = ws if ancestor else ws / "mon-projet"
    project = ws / "mon-projet"
    (project / "tickets" / "todo").mkdir(parents=True)
    agents = {"github_remote": "o/r", "artifacts": artifacts,
              "base_branch": "develop", "autonomy": autonomy}
    if ancestor:
        agents["git_root"] = "ancestor"
    (project / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    name, content = _ticket(1)
    (project / "tickets" / "todo" / name).write_text(content, encoding="utf-8")
    _git(repo, "init", "--initial-branch=develop")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "chore: initial")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "origin", "develop")
    return Env(origin, repo, project)


def _simulate_run(env: Env) -> None:
    """A run on its own branch, with work in the tree that is not committed."""
    _git(env.repo, "checkout", "-b", "ticket-099-en-cours")
    todo = env.project / "tickets" / "todo" / _ticket(1)[0]
    todo.write_text(todo.read_text(encoding="utf-8") + "modif du run\n", encoding="utf-8")
    (env.project / "scratch.txt").write_text("travail en cours\n", encoding="utf-8")


def _snapshot(env: Env) -> tuple[str, str, str]:
    return (
        _git(env.repo, "status", "--porcelain"),
        _git(env.repo, "rev-parse", "HEAD"),
        _git(env.repo, "branch", "--show-current"),
    )


def _worktrees(env: Env) -> int:
    listing = _git(env.repo, "worktree", "list", "--porcelain")
    return sum(1 for line in listing.splitlines() if line.startswith("worktree "))


def _request(env: Env, files: tuple[tuple[str, str], ...], github: FakeGitHub) -> ProposalRequest:
    return ProposalRequest(
        project_id="mon-projet", project_path=env.project, files=files,
        policy=PolitiqueRun.lire(env.project),
        github=github,  # type: ignore[arg-type]
        base_branch="develop",
    )


def test_invalid_frontmatter_is_refused_with_422_and_nothing_pushed(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build(workspace)
    calls: list[str] = []

    async def _spy(self: GitHubService, **kwargs: object) -> tuple[int, str]:
        calls.append("create_pull_request")
        return 1, "x"

    monkeypatch.setattr(GitHubService, "create_pull_request", _spy)
    name, content = _ticket(10, type_="inconnu")
    response = TestClient(app).post(
        "/api/v1/projects/mon-projet/tickets/propose",
        json={"tickets": [{"name": name, "content": content}]},
    )
    assert response.status_code == 422
    assert "ticket-010-demo.md" in response.json()["detail"]
    assert _git(env.origin, "for-each-ref", "--format=%(refname)").split() == [
        "refs/heads/develop"
    ]
    assert _worktrees(env) == 1
    assert calls == []


def test_valid_proposal_through_the_api_opens_the_pr(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build(workspace)

    async def _fake(self: GitHubService, **kwargs: object) -> tuple[int, str]:
        return 7, "https://example.test/pull/7"

    monkeypatch.setattr(GitHubService, "create_pull_request", _fake)
    name, content = _ticket(10)
    response = TestClient(app).post(
        "/api/v1/projects/mon-projet/tickets/propose",
        json={"tickets": [{"name": name, "content": content}]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["pr_number"] == 7 and body["ticket_ids"] == ["ticket-010"]
    assert body["merge_watched"] is False
    assert _git(env.origin, "show", f"{body['branch']}:tickets/todo/{name}") == content


async def test_main_tree_is_intact_during_and_after(workspace: Path) -> None:
    env = _build(workspace)
    _simulate_run(env)
    before = _snapshot(env)
    during: list[tuple[str, str, str]] = []
    github = FakeGitHub(on_create=lambda: during.append(_snapshot(env)))
    files = (_ticket(10), _ticket(11))

    proposal = await propose_tickets(_request(env, files, github))

    assert during == [before]
    assert _snapshot(env) == before
    assert not (env.project / "tickets" / "todo" / files[0][0]).exists()
    on_origin = _git(env.origin, "ls-tree", "--name-only", f"{proposal.branch}:tickets/todo")
    assert set(on_origin.split()) == {_ticket(1)[0], files[0][0], files[1][0]}
    assert github.calls[0][2] == "develop"
    assert _git(env.origin, "rev-list", "--count", f"develop..{proposal.branch}").strip() == "1"


async def test_worktree_is_removed_even_when_the_push_fails(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build(workspace)
    hook = env.origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    created: list[str] = []
    real_mkdtemp = tempfile.mkdtemp
    monkeypatch.setattr(
        tempfile, "mkdtemp", lambda **kw: created.append(real_mkdtemp(**kw)) or created[-1]
    )
    github = FakeGitHub()

    with pytest.raises(GitCommandError):
        await propose_tickets(_request(env, (_ticket(10),), github))

    assert len(created) == 1 and not Path(created[0]).exists()
    assert _worktrees(env) == 1
    assert github.calls == []
    assert "tickets-propose" not in _git(env.repo, "branch", "--list")


@pytest.mark.parametrize(("autonomy", "watched"), [("commit", False), ("pr", False), ("merge", True)])
async def test_merge_is_watched_only_for_autonomy_merge(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, autonomy: str, watched: bool
) -> None:
    env = _build(workspace, autonomy=autonomy)
    calls: list[tuple[str, str, int]] = []

    async def _surveiller(project_id: str, ticket_id: str, pr_number: int, *a: object, **k: object) -> None:
        calls.append((project_id, ticket_id, pr_number))

    monkeypatch.setattr(CI_WATCHER, "surveiller", _surveiller)
    proposal = await propose_tickets(_request(env, (_ticket(10),), FakeGitHub()))

    assert proposal.merge_watched is watched
    assert calls == ([("mon-projet", proposal.branch, 7)] if watched else [])


async def test_project_inside_an_ancestor_repository(workspace: Path) -> None:
    env = _build(workspace, ancestor=True)
    _simulate_run(env)
    before = _snapshot(env)
    proposal = await propose_tickets(_request(env, (_ticket(10),), FakeGitHub()))
    path = f"{proposal.branch}:mon-projet/tickets/todo/{_ticket(10)[0]}"
    assert _git(env.origin, "show", path) == _ticket(10)[1]
    assert _snapshot(env) == before and _worktrees(env) == 1


@pytest.mark.parametrize("case", ["duplicate_id", "existing_id", "bad_name", "empty", "local"])
async def test_refused_proposals_push_nothing(workspace: Path, case: str) -> None:
    env = _build(workspace, artifacts="local" if case == "local" else "tracked")
    files = {
        "duplicate_id": (_ticket(10), ("ticket-010-autre.md", _ticket(10)[1])),
        "existing_id": (_ticket(1),),
        "bad_name": (("../ticket-010-demo.md", _ticket(10)[1]),),
        "empty": (),
        "local": (_ticket(10),),
    }[case]
    with pytest.raises(ProposalRefused):
        await propose_tickets(_request(env, files, FakeGitHub()))
    assert _git(env.origin, "for-each-ref", "--format=%(refname)").split() == [
        "refs/heads/develop"
    ]
    assert _worktrees(env) == 1
