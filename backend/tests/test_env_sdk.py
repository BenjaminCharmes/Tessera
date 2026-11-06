"""The CLI subprocess inherits no vault secret nor GitHub credential (ticket-796, ticket-873)."""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers.env_sdk import env_du_sous_processus


@pytest.fixture(autouse=True)
def _state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "state")
    return tmp_path / "state"


def test_subprocess_env_blanks_static_token_and_forbidden_terms() -> None:
    env = env_du_sous_processus(None)

    assert env["STATIC_TOKEN"] == ""
    assert env["FORBIDDEN_TERMS"] == ""
    assert env["ANTHROPIC_API_KEY"] == ""
    assert env["VERCEL_TOKEN"] == ""


def test_subprocess_env_blanks_github_tokens() -> None:
    env = env_du_sous_processus(None)

    assert env["GITHUB_TOKEN"] == ""
    assert env["GH_TOKEN"] == ""


def test_subprocess_env_points_gh_to_an_existing_empty_directory(_state_dir: Path) -> None:
    env = env_du_sous_processus(None)

    dossier = Path(env["GH_CONFIG_DIR"])
    assert dossier.is_dir()
    assert list(dossier.iterdir()) == []
    assert dossier.is_relative_to(_state_dir)
    # Un second appel réutilise le même dossier sans échouer.
    assert env_du_sous_processus(None)["GH_CONFIG_DIR"] == env["GH_CONFIG_DIR"]


def test_subprocess_env_disables_the_git_credential_helper() -> None:
    env = env_du_sous_processus(None)

    assert env["GIT_CONFIG_COUNT"] == "1"
    assert env["GIT_CONFIG_KEY_0"] == "credential.helper"
    assert env["GIT_CONFIG_VALUE_0"] == ""
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_subprocess_env_keeps_the_git_bash_path() -> None:
    env = env_du_sous_processus("C:/outils/bash.exe")

    assert env["CLAUDE_CODE_GIT_BASH_PATH"] == "C:/outils/bash.exe"
    assert "CLAUDE_CODE_GIT_BASH_PATH" not in env_du_sous_processus(None)
