"""Vue d'ensemble des projets, icône et catégorie — ticket-398."""
import asyncio
import json
import os
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.project_overview import clear_overview_cache
from tessera.services.run_registry import RUN_REGISTRY

_BASE = "/api/v1/projects"


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    clear_overview_cache()


def _project(ws: Path, name: str) -> Path:
    folder = ws / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "CLAUDE.md").write_text(f"# {name}\n\nProjet {name}.\n", encoding="utf-8")
    return folder


def _commit(repo: Path, message: str, date: str) -> None:
    env = {**os.environ, "GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date}
    base = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run([*base, "commit", "-m", message], cwd=repo, check=True,
                   capture_output=True, env=env)


def _same_instant(actual: str | None, expected: str) -> bool:
    return actual is not None and datetime.fromisoformat(actual) == datetime.fromisoformat(expected)


def _overview() -> dict[str, dict[str, object]]:
    resp = TestClient(app).get(f"{_BASE}/overview")
    assert resp.status_code == 200
    return {item["id"]: item for item in resp.json()}


@pytest.fixture
def repo_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un seul dépôt git à la racine du workspace, comme `git_root: ancestor`."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True, capture_output=True)
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


@pytest.fixture
def plain_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def test_dates_follow_the_project_folder_not_the_whole_repository(repo_workspace: Path) -> None:
    alpha = _project(repo_workspace, "alpha")
    _commit(repo_workspace, "feat: add alpha", "2026-01-10T12:00:00+00:00")
    _project(repo_workspace, "beta")
    _commit(repo_workspace, "feat: add beta", "2026-02-01T12:00:00+00:00")
    (alpha / "notes.md").write_text("notes\n", encoding="utf-8")
    _commit(repo_workspace, "docs: alpha notes", "2026-03-05T12:00:00+00:00")

    body = _overview()

    assert _same_instant(str(body["alpha"]["created_at"]), "2026-01-10T12:00:00+00:00")
    assert _same_instant(str(body["alpha"]["last_activity"]), "2026-03-05T12:00:00+00:00")
    assert _same_instant(str(body["beta"]["created_at"]), "2026-02-01T12:00:00+00:00")
    assert _same_instant(str(body["beta"]["last_activity"]), "2026-02-01T12:00:00+00:00")


def test_ticket_counts_reflect_the_ticket_folders(plain_workspace: Path) -> None:
    folder = _project(plain_workspace, "alpha")
    for status, names in {"todo": ["a", "b"], "in-progress": ["c"], "done": ["d", "e", "f"]}.items():
        (folder / "tickets" / status).mkdir(parents=True)
        for name in names:
            (folder / "tickets" / status / f"ticket-{name}.md").write_text("x", encoding="utf-8")

    tickets = _overview()["alpha"]["tickets"]

    assert tickets == {"todo": 2, "in_progress": 1, "in_review": 0, "blocked": 0, "done": 3}


def _count_git_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    appels: list[tuple[str, ...]] = []
    reel = asyncio.create_subprocess_exec

    async def espion(*args: str, **kwargs: object) -> asyncio.subprocess.Process:
        appels.append(args)
        return await reel(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(asyncio, "create_subprocess_exec", espion)
    return appels


def test_second_call_without_change_runs_no_git_command(
    repo_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _project(repo_workspace, "alpha")
    _commit(repo_workspace, "feat: add alpha", "2026-01-10T12:00:00+00:00")
    appels = _count_git_calls(monkeypatch)

    first = _overview()
    after_first = len(appels)
    second = _overview()

    assert after_first > 0
    assert len(appels) == after_first
    assert second == first


def test_a_new_commit_invalidates_the_cache(
    repo_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alpha = _project(repo_workspace, "alpha")
    _commit(repo_workspace, "feat: add alpha", "2026-01-10T12:00:00+00:00")
    _overview()
    (alpha / "more.md").write_text("more\n", encoding="utf-8")
    _commit(repo_workspace, "docs: more", "2026-04-01T12:00:00+00:00")

    assert _same_instant(str(_overview()["alpha"]["last_activity"]), "2026-04-01T12:00:00+00:00")


def test_a_moved_ticket_invalidates_the_counts(plain_workspace: Path) -> None:
    folder = _project(plain_workspace, "alpha")
    (folder / "tickets" / "todo").mkdir(parents=True)
    (folder / "tickets" / "done").mkdir(parents=True)
    fiche = folder / "tickets" / "todo" / "ticket-1.md"
    fiche.write_text("x", encoding="utf-8")
    assert _overview()["alpha"]["tickets"]["todo"] == 1  # type: ignore[index]

    fiche.rename(folder / "tickets" / "done" / "ticket-1.md")

    tickets = _overview()["alpha"]["tickets"]
    assert (tickets["todo"], tickets["done"]) == (0, 1)  # type: ignore[index]


def test_icon_is_served_with_its_content_type(plain_workspace: Path) -> None:
    folder = _project(plain_workspace, "alpha")
    _project(plain_workspace, "beta")
    public = folder / "frontend" / "public"
    public.mkdir(parents=True)
    (public / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    client = TestClient(app)

    resp = client.get(f"{_BASE}/alpha/icon")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/svg+xml"
    assert client.get(f"{_BASE}/beta/icon").status_code == 404
    body = _overview()
    assert body["alpha"]["icon"] is True
    assert body["beta"]["icon"] is False


def test_manifest_is_updated_with_category_and_empty_string_removes_it(
    plain_workspace: Path,
) -> None:
    folder = _project(plain_workspace, "alpha")
    manifeste = folder / "agents.json"
    manifeste.write_text(json.dumps({"autonomy": "pr", "agents": []}), encoding="utf-8")
    client = TestClient(app)

    resp = client.patch(f"{_BASE}/alpha/pipeline", json={"category": "Outils"})
    assert resp.status_code == 200
    ecrit = json.loads(manifeste.read_text(encoding="utf-8"))
    assert ecrit["category"] == "Outils"
    assert ecrit["autonomy"] == "pr"
    assert _overview()["alpha"]["category"] == "Outils"

    resp = client.patch(f"{_BASE}/alpha/pipeline", json={"category": ""})
    assert resp.status_code == 200
    assert "category" not in json.loads(manifeste.read_text(encoding="utf-8"))
    assert _overview()["alpha"]["category"] is None


def test_category_change_is_refused_during_a_run(
    plain_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _project(plain_workspace, "alpha")
    (folder / "agents.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(RUN_REGISTRY, "projet_occupe", lambda project_id: True)

    resp = TestClient(app).patch(f"{_BASE}/alpha/pipeline", json={"category": "Outils"})

    assert resp.status_code == 409


def test_project_without_git_repository_still_appears(plain_workspace: Path) -> None:
    _project(plain_workspace, "alpha")

    item = _overview()["alpha"]

    assert item["last_activity"] is None
    assert datetime.fromisoformat(str(item["created_at"]))
    assert item["run_actif"] is False


def test_overview_flags_an_active_run(
    plain_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _project(plain_workspace, "alpha")
    _project(plain_workspace, "beta")
    occupe: Callable[[str], bool] = lambda project_id: project_id == "alpha"
    monkeypatch.setattr(RUN_REGISTRY, "projet_occupe", occupe)

    body = _overview()

    assert body["alpha"]["run_actif"] is True
    assert body["beta"]["run_actif"] is False


def test_tessera_icon_wins_and_next_and_root_favicons_are_found(plain_workspace: Path) -> None:
    """Ticket-404: `.tessera/icon.svg` (projects without a web app) comes first;
    a Next.js `src/app/icon.svg`, a root `favicon.svg` (static games) and a
    `frontend/public/logo.svg` are found too."""
    from tessera.services.project_overview import find_icon

    svg = "<svg xmlns='http://www.w3.org/2000/svg'/>"
    profil = _project(plain_workspace, "profil")
    (profil / ".tessera").mkdir()
    (profil / ".tessera" / "icon.svg").write_text(svg, encoding="utf-8")
    (profil / "favicon.svg").write_text(svg, encoding="utf-8")
    site = _project(plain_workspace, "site")
    (site / "src" / "app").mkdir(parents=True)
    (site / "src" / "app" / "icon.svg").write_text(svg, encoding="utf-8")
    jeu = _project(plain_workspace, "jeu")
    (jeu / "favicon.svg").write_text(svg, encoding="utf-8")
    app_logo = _project(plain_workspace, "app")
    (app_logo / "frontend" / "public").mkdir(parents=True)
    (app_logo / "frontend" / "public" / "logo.svg").write_text(svg, encoding="utf-8")

    trouvees = {p.name: find_icon(p) for p in (profil, site, jeu, app_logo)}

    assert trouvees["profil"][0].relative_to(profil.resolve()).as_posix() == ".tessera/icon.svg"  # type: ignore[index]
    assert trouvees["site"][0].name == "icon.svg"  # type: ignore[index]
    assert trouvees["jeu"][0].name == "favicon.svg"  # type: ignore[index]
    assert trouvees["app"][0].name == "logo.svg"  # type: ignore[index]


def test_ancestor_project_uses_the_repository_icon(repo_workspace: Path) -> None:
    """Ticket-404: a `git_root: ancestor` project (ide-core) shows the icon of
    the repository that contains it — the IDE's own; a plain project does not."""
    from tessera.services.project_overview import find_icon

    public = repo_workspace / "frontend" / "public"
    public.mkdir(parents=True)
    (public / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    bootstrap = _project(repo_workspace / "projects", "bootstrap")
    (bootstrap / "agents.json").write_text(json.dumps({"git_root": "ancestor"}), encoding="utf-8")
    voisin = _project(repo_workspace / "projects", "voisin")

    trouvee = find_icon(bootstrap)

    assert trouvee is not None
    assert trouvee[0] == (public / "favicon.svg").resolve()
    assert find_icon(voisin) is None
