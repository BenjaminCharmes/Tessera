"""ticket-934: a process started under the dedicated account, never a fallback."""
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from tessera.config import settings
from tessera.services.verification.lancement_compte import EchecLancementCompte, env_du_compte, lancer_sous_compte
from tests.doubles_compte import LanceurDouble, ProcessDouble


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw"))


async def test_launcher_receives_account_command_and_directory(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble()
    await lancer_sous_compte(["echo", "x"], tmp_path, None, lanceur)
    appel = lanceur.appels[0]
    assert appel["compte"] == "tessera-agent"
    assert appel["cwd"] == str(tmp_path)
    assert appel["commande"][0].startswith("echo")


async def test_adapter_returns_both_pipes_and_the_exit_code(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble(ProcessDouble(b"out", b"err", code=3))
    processus = await lancer_sous_compte(["x"], tmp_path, None, lanceur)
    assert await processus.communicate() == (b"out", b"err")
    assert processus.returncode == 3
    assert processus.pid == 4242


async def test_kill_goes_to_the_process_handle(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble()
    processus = await lancer_sous_compte(["x"], tmp_path, None, lanceur)
    processus.kill()
    assert lanceur.processus.tue is True


async def test_launcher_refusal_becomes_a_launch_failure(compte: None, tmp_path: Path) -> None:
    with pytest.raises(EchecLancementCompte):
        await lancer_sous_compte(["x"], tmp_path, None, LanceurDouble(refus="logon refuse"))


async def test_missing_password_refuses_without_calling_the_launcher(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr(""))
    lanceur = LanceurDouble()
    with patch("asyncio.create_subprocess_exec") as sous_processus:
        with pytest.raises(EchecLancementCompte):
            await lancer_sous_compte(["x"], tmp_path, None, lanceur)
    assert lanceur.appels == []
    sous_processus.assert_not_called()


async def test_empty_account_refuses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    with pytest.raises(EchecLancementCompte):
        await lancer_sous_compte(["x"], tmp_path, None, LanceurDouble())


def test_environment_is_built_from_nothing_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "/bin")
    monkeypatch.setenv("UNE_AUTRE_VARIABLE", "fuite")
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    env = env_du_compte({"PYTHONPATH": "src"})
    assert env["PYTHONPATH"] == "src"
    assert any(nom.lower() == "path" for nom in env)
    assert "UNE_AUTRE_VARIABLE" not in env
    assert "GITHUB_TOKEN" not in env
