"""Normalisation du github_remote : any form → (forge, 'owner/repo') — ticket-215."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.services.github_workflow import forge_supportee, parse_remote
from tessera.services.project_loader import load_project


# ---------------------------------------------------------------------------
# parse_remote — critères 1 & 2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "BenjaminCharmes/Tessera",
        "https://github.com/BenjaminCharmes/Tessera",
        "https://github.com/BenjaminCharmes/Tessera.git",
        "git@github.com:BenjaminCharmes/Tessera.git",
    ],
)
def test_all_github_forms_return_same_slug(raw: str) -> None:
    """All four remote forms normalise to the same owner/repo slug."""
    forge, slug = parse_remote(raw)
    assert slug == "BenjaminCharmes/Tessera"
    assert forge == "GitHub"


def test_gitlab_remote_returns_gitlab_forge_and_is_not_pr_supported() -> None:
    """A GitLab HTTPS remote is identified correctly and is not PR-supported."""
    forge, slug = parse_remote("https://gitlab.com/a/b")
    assert forge == "GitLab"
    assert slug == "a/b"
    # forge_supportee still works with raw URL forms (used by existing callers)
    assert forge_supportee("https://gitlab.com/a/b") is False


def test_parse_remote_none_returns_none_none() -> None:
    forge, slug = parse_remote(None)
    assert forge is None
    assert slug is None


def test_parse_remote_empty_returns_none_none() -> None:
    forge, slug = parse_remote("")
    assert forge is None
    assert slug is None


def test_github_enterprise_host_is_not_assumed_github() -> None:
    """A GitHub Enterprise URL must not be mistaken for github.com."""
    forge, slug = parse_remote("https://github.mycompany.com/org/repo")
    assert forge != "GitHub"
    assert slug == "org/repo"


# ---------------------------------------------------------------------------
# GitHubService avec un remote en forme URL — critère 3
# ---------------------------------------------------------------------------

_BASE = "https://api.github.com"
_TOKEN = "tok_test"


@respx.mock
async def test_github_service_with_url_form_remote_calls_correct_repo() -> None:
    """After normalisation, GitHubService hits repos/owner/repo/…,
    not repos/https://github.com/…/…."""
    route = respx.get(f"{_BASE}/repos/owner/repo/issues").mock(
        return_value=httpx.Response(200, json=[])
    )

    from tessera.services.github_service import GitHubService

    _, slug = parse_remote("https://github.com/owner/repo.git")
    assert slug == "owner/repo"
    svc = GitHubService(token=_TOKEN, repo=slug)
    await svc.list_agent_ready_issues()

    assert route.called
    assert "/repos/owner/repo/" in str(route.calls[0].request.url)


# ---------------------------------------------------------------------------
# load_project normalise github_remote
# ---------------------------------------------------------------------------


def test_load_project_normalises_https_to_slug(tmp_path: Path) -> None:
    """load_project converts an HTTPS URL in agents.json to owner/repo."""
    p = tmp_path / "myproj"
    p.mkdir()
    (p / "CLAUDE.md").write_text("# myproj\n", encoding="utf-8")
    (p / "agents.json").write_text(
        json.dumps({
            "github_remote": "https://github.com/alice/myproj.git",
            "agents": [],
        }),
        encoding="utf-8",
    )

    project = load_project(p)

    assert project.github_remote == "alice/myproj"
    assert project.github_forge == "GitHub"


def test_load_project_short_form_stays_as_is(tmp_path: Path) -> None:
    """A short 'owner/repo' form is preserved verbatim as the slug."""
    p = tmp_path / "myproj2"
    p.mkdir()
    (p / "CLAUDE.md").write_text("# myproj2\n", encoding="utf-8")
    (p / "agents.json").write_text(
        json.dumps({
            "github_remote": "alice/myproj",
            "agents": [],
        }),
        encoding="utf-8",
    )

    project = load_project(p)

    assert project.github_remote == "alice/myproj"
    assert project.github_forge == "GitHub"


def test_load_project_ssh_form_normalises(tmp_path: Path) -> None:
    """An SSH remote is normalised to owner/repo."""
    p = tmp_path / "myproj3"
    p.mkdir()
    (p / "CLAUDE.md").write_text("# myproj3\n", encoding="utf-8")
    (p / "agents.json").write_text(
        json.dumps({
            "github_remote": "git@github.com:alice/myproj.git",
            "agents": [],
        }),
        encoding="utf-8",
    )

    project = load_project(p)

    assert project.github_remote == "alice/myproj"
    assert project.github_forge == "GitHub"


# ---------------------------------------------------------------------------
# /activity renvoie pr_supported: true pour un remote en forme courte — critère 4
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace_with_short_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Project directory with a short-form github_remote and one todo ticket."""
    ws = tmp_path / "workspace"
    proj = ws / "proj"
    for sub in ["tickets/todo", "tickets/done", "tickets/in-progress",
                "tickets/in-review", "tickets/blocked", "memory"]:
        (proj / sub).mkdir(parents=True)

    (proj / "CLAUDE.md").write_text("# proj\n", encoding="utf-8")
    (proj / "agents.json").write_text(
        json.dumps({
            "github_remote": "alice/proj",
            "autonomy": "commit",
            "agents": [],
        }),
        encoding="utf-8",
    )
    # Minimal ticket file — TicketService finds it by name prefix.
    (proj / "tickets" / "todo" / "ticket-001-test.md").write_text(
        "---\ntitle: Test\n---\n# ticket-001\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))

    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "github_token", "")
    return ws


def test_activity_endpoint_pr_supported_for_short_form(
    workspace_with_short_remote: Path,
) -> None:
    """GET /activity returns pr_supported=true when github_remote is 'alice/proj'."""
    client = TestClient(app)
    resp = client.get("/api/v1/projects/proj/tickets/ticket-001/activity")

    assert resp.status_code == 200
    data = resp.json()
    assert data["pr_supported"] is True
    assert data["forge"] == "GitHub"
    assert data["github_remote"] == "alice/proj"
