"""Tests pour GitCloneService (ticket-030)."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera.models.project import AnalysisResult
from tessera.services.git_clone import (
    CloneError,
    GitCloneService,
    _build_clone_url,
    _repo_name,
    _sanitize_id,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def _make_analyzer_mock(
    detected_stack: list[str] | None = None,
    claude_md_written: bool = True,
) -> MagicMock:
    analyzer = MagicMock()
    result = AnalysisResult(
        claude_md="# CLAUDE.md\n",
        detected_stack=detected_stack or ["Python"],
        suggested_agents=["codeur"],
        claude_md_written=claude_md_written,
    )
    analyzer.analyze = AsyncMock(return_value=result)
    return analyzer


def _make_successful_clone(tmp_path: Path, dest_name: str = "my-repo") -> MagicMock:
    """Retourne un mock de subprocess qui crée le dossier dest au moment de l'appel."""
    async def _fake_clone(url: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "README.md").write_text("# My Repo\n", encoding="utf-8")

    return _fake_clone


# ------------------------------------------------------------------
# Unit helpers
# ------------------------------------------------------------------


def test_sanitize_id_basic() -> None:
    assert _sanitize_id("My.Repo") == "my-repo"


def test_sanitize_id_truncates() -> None:
    assert len(_sanitize_id("a" * 60)) == 50


def test_repo_name_extracts_last_segment() -> None:
    assert _repo_name("https://github.com/owner/my-repo") == "my-repo"
    assert _repo_name("https://github.com/owner/my-repo/") == "my-repo"


def test_build_clone_url_without_token() -> None:
    url = "https://github.com/owner/repo"
    assert _build_clone_url(url, None) == url


def test_build_clone_url_with_token() -> None:
    url = "https://github.com/owner/repo"
    result = _build_clone_url(url, "mytoken123")
    assert result == "https://mytoken123@github.com/owner/repo"
    assert "github.com/owner/repo" in result


# ------------------------------------------------------------------
# URL validation
# ------------------------------------------------------------------


async def test_clone_rejects_invalid_url(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())

    with pytest.raises(CloneError, match="URL GitHub invalide"):
        await svc.clone("git@github.com:owner/repo.git")


async def test_clone_rejects_non_github_url(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())

    with pytest.raises(CloneError, match="URL GitHub invalide"):
        await svc.clone("https://gitlab.com/owner/repo")


async def test_clone_rejects_path_traversal_attempt(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())

    with pytest.raises(CloneError, match="URL GitHub invalide"):
        await svc.clone("https://github.com/../../../etc/passwd")


async def test_clone_rejects_url_with_extra_path(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())

    with pytest.raises(CloneError, match="URL GitHub invalide"):
        await svc.clone("https://github.com/owner/repo/tree/main")


# ------------------------------------------------------------------
# Duplicate detection
# ------------------------------------------------------------------


async def test_clone_rejects_existing_project(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    (ws / "my-repo").mkdir()
    svc = GitCloneService(ws, _make_analyzer_mock())

    with pytest.raises(CloneError, match="existe déjà"):
        await svc.clone("https://github.com/owner/my-repo")


# ------------------------------------------------------------------
# Successful clone
# ------------------------------------------------------------------


async def test_clone_creates_project_in_workspace(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock(detected_stack=["Python", "FastAPI"])
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        result = await svc.clone("https://github.com/owner/my-repo")

    assert result.project.id == "my-repo"
    assert (ws / "my-repo").is_dir()


async def test_clone_stores_github_remote_in_agents_json(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        await svc.clone("https://github.com/owner/my-repo")

    agents_json = ws / "my-repo" / "agents.json"
    assert agents_json.exists()
    data = json.loads(agents_json.read_text(encoding="utf-8"))
    assert data["github_remote"] == "https://github.com/owner/my-repo"


async def test_clone_github_remote_surfaced_in_project(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        result = await svc.clone("https://github.com/owner/my-repo")

    # github_remote is normalised to 'owner/repo' at load time (ticket-215).
    assert result.project.github_remote == "owner/my-repo"
    assert result.project.github_forge == "GitHub"


async def test_clone_returns_detected_stack(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock(detected_stack=["TypeScript", "React"])
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        result = await svc.clone("https://github.com/owner/my-repo")

    assert result.detected_stack == ["TypeScript", "React"]


async def test_clone_uses_explicit_project_id(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        result = await svc.clone(
            "https://github.com/owner/my-repo",
            project_id="custom-id",
        )

    assert result.project.id == "custom-id"
    assert (ws / "custom-id").is_dir()


async def test_clone_scaffolds_artifact_dirs(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        await svc.clone("https://github.com/owner/my-repo")

    dest = ws / "my-repo"
    assert (dest / "tickets" / "todo").is_dir()
    assert (dest / "memory").is_dir()


async def test_clone_calls_analyzer(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=lambda url, dest: dest.mkdir(parents=True))):
        await svc.clone("https://github.com/owner/my-repo")

    analyzer.analyze.assert_called_once_with(ws / "my-repo")


async def test_clone_preserves_existing_agents_json_fields(tmp_path: Path) -> None:
    """_store_github_remote ne doit pas écraser les champs existants."""
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    async def _make_dest_with_agents(url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        (dest / "agents.json").write_text(
            json.dumps({"project_id": "my-repo", "agents": []}, indent=2),
            encoding="utf-8",
        )

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=_make_dest_with_agents)):
        await svc.clone("https://github.com/owner/my-repo")

    data = json.loads((ws / "my-repo" / "agents.json").read_text(encoding="utf-8"))
    assert data["project_id"] == "my-repo"
    assert data["github_remote"] == "https://github.com/owner/my-repo"


# ------------------------------------------------------------------
# Error / cleanup
# ------------------------------------------------------------------


async def test_clone_cleans_up_dest_on_git_failure(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    async def _failing_clone(url: str, dest: Path) -> None:
        dest.mkdir(parents=True)  # git crée le dossier avant d'échouer
        raise CloneError("git clone a échoué (code 128).")

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=_failing_clone)):
        with pytest.raises(CloneError):
            await svc.clone("https://github.com/owner/my-repo")

    assert not (ws / "my-repo").exists()


async def test_clone_cleans_up_dest_on_timeout(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    analyzer = _make_analyzer_mock()
    svc = GitCloneService(ws, analyzer)

    async def _timeout_clone(url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        raise CloneError("Le clone a dépassé 60s.")

    with patch.object(svc, "_run_clone", new=AsyncMock(side_effect=_timeout_clone)):
        with pytest.raises(CloneError, match="60s"):
            await svc.clone("https://github.com/owner/my-repo")

    assert not (ws / "my-repo").exists()


# ------------------------------------------------------------------
# _run_clone subprocess behaviour
# ------------------------------------------------------------------


async def test_run_clone_raises_on_nonzero_returncode(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())
    dest = tmp_path / "dest"

    mock_proc = AsyncMock()
    mock_proc.returncode = 128
    mock_proc.communicate = AsyncMock(return_value=(b"", b"fatal: repo not found"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(CloneError, match="git clone a échoué"):
            await svc._run_clone("https://github.com/owner/repo", dest)


async def test_run_clone_raises_on_timeout(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())
    dest = tmp_path / "dest"

    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.kill = MagicMock()
    # First call (inside wait_for) raises TimeoutError; second call (cleanup) returns.
    mock_proc.communicate = AsyncMock(
        side_effect=[asyncio.TimeoutError(), (b"", b"")]
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(CloneError, match="dépassé"):
            await svc._run_clone("https://github.com/owner/repo", dest)

    mock_proc.kill.assert_called_once()


async def test_run_clone_succeeds_on_zero_returncode(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    svc = GitCloneService(ws, _make_analyzer_mock())
    dest = tmp_path / "dest"

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        await svc._run_clone("https://github.com/owner/repo", dest)
