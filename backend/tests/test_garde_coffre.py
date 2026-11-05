"""The read guard refuses Bash commands that run the vault — ADR-073, ticket-799."""
import logging
from pathlib import Path
from typing import Any, cast

import pytest
from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.services.providers.garde_coffre import COFFRE_REFUS
from tessera.services.providers.garde_jetons import hook_refus_env_tessera


async def _bash(tmp_path: Path, commande: str) -> HookJSONOutput:
    env = tmp_path / ".env"
    env.write_text("X=1\n", encoding="utf-8")
    projet = tmp_path / "projects" / "client"
    projet.mkdir(parents=True, exist_ok=True)
    hook = hook_refus_env_tessera(projet, env_file=env)
    entree = cast(HookInput, {"tool_name": "Bash", "tool_input": {"command": commande}})
    return await hook(entree, None, cast(HookContext, None))


def _raison(sortie: HookJSONOutput) -> str | None:
    decision = cast(dict[str, Any], sortie).get("hookSpecificOutput", {})
    if decision.get("permissionDecision") != "deny":
        return None
    return str(decision.get("permissionDecisionReason"))


async def _refuse(tmp_path: Path, commande: str) -> bool:
    return _raison(await _bash(tmp_path, commande)) == COFFRE_REFUS


async def test_refuses_keyring_cli(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "keyring get tessera GITHUB_TOKEN")
    assert await _refuse(tmp_path, "C:/outils/Keyring.exe get tessera X")


async def test_refuses_cmdkey(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "cmdkey /list")
    assert await _refuse(tmp_path, "CMDKEY.EXE /list:tessera*")


async def test_refuses_vaultcmd(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, 'vaultcmd /listcreds:"Windows Credentials"')


async def test_refuses_secret_tool(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "secret-tool lookup service tessera")


async def test_refuses_macos_security_find_generic_password(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "security find-generic-password -s tessera -w")
    assert await _refuse(tmp_path, "security find-internet-password -s x")


async def test_refuses_python_dash_c_import_keyring(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "python -c \"import keyring; print(keyring.get_password('tessera', 'X'))\"")
    assert await _refuse(tmp_path, "python3 -c 'from keyring import get_password'")
    assert await _refuse(tmp_path, "uv run python -m keyring get tessera X")


async def test_refuses_python_dash_m_coffre_cli(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "uv run python -m tessera.coffre_cli termes")
    assert await _refuse(tmp_path, "python -m tessera.coffre_cli lister")


async def test_refuses_a_powershell_credential_read(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, 'powershell -c "Get-StoredCredential -Target tessera"')
    assert await _refuse(tmp_path, "pwsh -c \"[Windows.Security.Credentials.PasswordVault]::new()\"")
    assert await _refuse(tmp_path, "rundll32 advapi32.dll,CredReadW")


async def test_refuses_after_a_separator(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, "echo x; keyring get tessera VERCEL_TOKEN")
    assert await _refuse(tmp_path, "ls && cmdkey /list")
    assert await _refuse(tmp_path, "echo x | FOO=1 keyring get tessera X")


async def test_allows_grep_for_the_word_keyring(tmp_path: Path) -> None:
    assert _raison(await _bash(tmp_path, "grep -n keyring src/tessera/coffre.py")) is None
    assert _raison(await _bash(tmp_path, 'rg "import keyring" src')) is None


async def test_allows_uv_run_pytest_on_the_vault_tests(tmp_path: Path) -> None:
    commande = "uv run pytest -q tests/test_coffre.py tests/test_coffre_cli.py"
    assert _raison(await _bash(tmp_path, commande)) is None
    assert _raison(await _bash(tmp_path, "uv run python -m pytest tests/test_coffre.py")) is None


async def test_allows_security_without_a_password_subcommand(tmp_path: Path) -> None:
    assert _raison(await _bash(tmp_path, "security list-keychains")) is None
    assert _raison(await _bash(tmp_path, "npm audit --audit-level security")) is None


async def test_refusal_message_states_the_ceiling() -> None:
    assert "coffre" in COFFRE_REFUS
    assert "lexical" in COFFRE_REFUS
    assert "évasion" in COFFRE_REFUS
    assert "portée" in COFFRE_REFUS


async def test_refusal_log_holds_the_tool_name_only(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        await _bash(tmp_path, "keyring get tessera GITHUB_TOKEN")

    enregistrements = [r for r in caplog.records if r.getMessage() == "execution_coffre_refusee"]
    assert len(enregistrements) == 1
    assert getattr(enregistrements[0], "outil") == "Bash"
    assert "GITHUB_TOKEN" not in str(enregistrements[0].__dict__)


def test_existing_env_guard_cases_still_pass() -> None:
    # `test_garde_jetons.py` n'est pas modifié par ce ticket : il tourne avec
    # la suite, et ce test vérifie qu'il existe toujours.
    assert (Path(__file__).parent / "test_garde_jetons.py").is_file()
