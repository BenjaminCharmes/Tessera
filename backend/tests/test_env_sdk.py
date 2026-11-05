"""The CLI subprocess inherits no vault secret (ticket-796, ADR-073)."""
from tessera.services.providers.env_sdk import env_du_sous_processus


def test_subprocess_env_blanks_static_token_and_forbidden_terms() -> None:
    env = env_du_sous_processus(None)

    assert env["STATIC_TOKEN"] == ""
    assert env["FORBIDDEN_TERMS"] == ""
    assert env["ANTHROPIC_API_KEY"] == ""
    assert env["VERCEL_TOKEN"] == ""
    # Design §9 : les lectures `gh` des agents peuvent en dépendre.
    assert "GITHUB_TOKEN" not in env


def test_subprocess_env_keeps_the_git_bash_path() -> None:
    env = env_du_sous_processus("C:/outils/bash.exe")

    assert env["CLAUDE_CODE_GIT_BASH_PATH"] == "C:/outils/bash.exe"
    assert "CLAUDE_CODE_GIT_BASH_PATH" not in env_du_sous_processus(None)
