"""Git Bash detection and health reporting — ticket-319.

Quatre critères d'acceptation :
1. ``_build_options`` pose ``CLAUDE_CODE_GIT_BASH_PATH`` dans ``env`` quand
   ``git_bash_path`` est connu, et ne le pose pas sinon.
2. Sous Windows, ``git_bash_path`` est déduit de l'emplacement de ``git``
   quand la variable d'environnement est absente.
3. ``GET /health`` rend ``agent_shell: false`` quand aucun Git Bash n'est
   trouvé sous Windows.
4. Hors Windows, rien de tout cela ne s'applique et ``agent_shell`` vaut
   ``true``.
"""
import platform
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import tessera.main
import tessera.services.shell_detection as shell_mod
from tessera.services.providers.agent_sdk import _build_options
from tessera.services.shell_detection import agent_shell_ok, resolve_git_bash


# ── critère 1 : _build_options et CLAUDE_CODE_GIT_BASH_PATH ─────────────────


def test_build_options_sets_git_bash_path_in_env() -> None:
    """Quand git_bash_path est connu, l'env du sous-process le porte."""
    options = _build_options(
        system="sys",
        model="claude-sonnet-4-6",
        max_turns=30,
        max_budget_usd=None,
        cwd=None,
        git_bash_path="/c/git/bin/bash.exe",
    )
    assert options.env is not None
    assert options.env.get("CLAUDE_CODE_GIT_BASH_PATH") == "/c/git/bin/bash.exe"


def test_build_options_omits_git_bash_path_when_none() -> None:
    """Quand git_bash_path est None, la clef n'apparaît pas dans l'env."""
    options = _build_options(
        system="sys",
        model="claude-sonnet-4-6",
        max_turns=30,
        max_budget_usd=None,
        cwd=None,
        git_bash_path=None,
    )
    assert options.env is not None
    assert "CLAUDE_CODE_GIT_BASH_PATH" not in options.env


# ── critère 2 : déduction Windows depuis l'emplacement de git ───────────────


def test_resolve_git_bash_deduces_from_git_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sous Windows sans env var, bash.exe est déduit du dossier parent de git."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Windows")

    # Simule une installation style scoop / Git for Windows :
    # <root>/cmd/git.exe et <root>/bin/bash.exe
    git_root = tmp_path / "git"
    cmd_dir = git_root / "cmd"
    cmd_dir.mkdir(parents=True)
    bin_dir = git_root / "bin"
    bin_dir.mkdir()
    git_exe = cmd_dir / "git.exe"
    git_exe.touch()
    bash_exe = bin_dir / "bash.exe"
    bash_exe.touch()

    result = resolve_git_bash(env_value="", which_fn=lambda _: str(git_exe))

    assert result == str(bash_exe.resolve())


def test_resolve_git_bash_returns_none_when_git_not_in_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sous Windows sans git dans le PATH, aucun chemin ne peut être déduit."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Windows")

    result = resolve_git_bash(env_value="", which_fn=lambda _: None)

    assert result is None


def test_resolve_git_bash_prefers_env_value_over_deduction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La variable d'environnement a la priorité sur la déduction."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Windows")

    result = resolve_git_bash(
        env_value="/explicit/bash.exe",
        which_fn=lambda _: "/other/git.exe",
    )

    assert result == "/explicit/bash.exe"


# ── critère 3 et 4 : GET /health et agent_shell ─────────────────────────────


def test_agent_shell_ok_returns_false_on_windows_without_bash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sous Windows sans bash.exe, agent_shell_ok vaut False."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Windows")
    assert agent_shell_ok(None) is False


def test_agent_shell_ok_returns_true_on_windows_with_bash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sous Windows avec un bash.exe connu, agent_shell_ok vaut True."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Windows")
    assert agent_shell_ok("/c/git/bin/bash.exe") is True


def test_agent_shell_ok_returns_true_on_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hors Windows, le Bash natif est disponible sans configuration."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Linux")
    assert agent_shell_ok(None) is True


def test_health_reports_agent_shell_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /health rend agent_shell: false quand aucun Git Bash n'est trouvé."""
    monkeypatch.setattr(tessera.main, "_AGENT_SHELL_OK", False)
    client = TestClient(tessera.main.app, raise_server_exceptions=True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["agent_shell"] is False


def test_health_reports_agent_shell_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /health rend agent_shell: true quand le shell est disponible."""
    monkeypatch.setattr(tessera.main, "_AGENT_SHELL_OK", True)
    client = TestClient(tessera.main.app, raise_server_exceptions=True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["agent_shell"] is True


def test_resolve_git_bash_returns_none_on_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hors Windows, resolve_git_bash renvoie None sans rien chercher."""
    monkeypatch.setattr(shell_mod.platform, "system", lambda: "Linux")
    called: list[str] = []

    result = resolve_git_bash(env_value="anything", which_fn=lambda x: called.append(x) or "/git")  # type: ignore[return-value]

    assert result is None
    assert called == []  # which_fn n'est jamais appelé hors Windows
