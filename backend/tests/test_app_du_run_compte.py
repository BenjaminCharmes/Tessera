"""ticket-934: the visual-check app starts under the dedicated account when declared."""
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from tessera.config import settings
from tessera.services.verification.app_du_run import DemarrageEchoue, demarrer_processus, demarreur_du_run
from tests.doubles_compte import LanceurDouble, ProcessDouble


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw"))


async def test_app_starts_through_the_account_launcher(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble()
    with patch("asyncio.create_subprocess_exec") as direct:
        app = await demarreur_du_run(True, lanceur)(["npm", "run", "dev"], tmp_path)
    direct.assert_not_called()
    assert lanceur.appels[0]["compte"] == "tessera-agent"
    assert lanceur.appels[0]["cwd"] == str(tmp_path)
    assert app.code_de_sortie is None


async def test_stopping_the_app_kills_the_process_handle(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble(ProcessDouble())
    app = await demarreur_du_run(True, lanceur)(["x"], tmp_path)
    await app.arreter()
    assert lanceur.processus.tue is True


async def test_launcher_failure_is_a_start_failure_without_fallback(
    compte: None, tmp_path: Path
) -> None:
    starter = demarreur_du_run(True, LanceurDouble(refus="logon refuse"))
    with patch("asyncio.create_subprocess_exec") as direct:
        with pytest.raises(DemarrageEchoue):
            await starter(["x"], tmp_path)
    direct.assert_not_called()


def test_without_the_declared_account_the_default_starter_is_kept(compte: None) -> None:
    assert demarreur_du_run(False) is demarrer_processus


def test_empty_agent_user_keeps_the_default_starter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    assert demarreur_du_run(True) is demarrer_processus
