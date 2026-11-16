"""ticket-983: the doctor launches the tools under the agent account."""
import asyncio
from pathlib import Path

import pytest
from pydantic import SecretStr

from tessera.agent_doctor_cli import verifier_outils
from tessera.config import settings
from tests.chaine_factice import chaine_factice  # noqa: F401
from tests.doubles_compte import LanceurDouble, ProcessDouble


class ProcessLent(ProcessDouble):
    async def wait(self) -> int:
        await asyncio.sleep(10)
        return 0


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch, chaine: Path) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw-secret"))


async def test_all_tools_ok(compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lanceur = LanceurDouble()
    assert await verifier_outils(tmp_path, lanceur) == 0
    sortie = capsys.readouterr().out
    assert [a["commande"][0].split(".")[0] for a in lanceur.appels] == ["node", "uv", "python"]
    assert sortie.count(": ok") == 3
    assert "pw-secret" not in sortie


async def test_one_tool_failing_stops_and_names_it(
    compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lanceur = LanceurDouble(refus="EPERM")
    assert await verifier_outils(tmp_path, lanceur) == 1
    sortie = capsys.readouterr().out
    assert "node" in sortie and "EPERM" in sortie and "agent setup" in sortie
    assert len(lanceur.appels) >= 1 and "uv :" not in sortie


async def test_non_zero_exit_code_fails(compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lanceur = LanceurDouble(ProcessDouble(code=2))
    assert await verifier_outils(tmp_path, lanceur) == 1
    assert "code de sortie 2" in capsys.readouterr().out


async def test_timeout_fails(compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lanceur = LanceurDouble(ProcessLent())
    assert await verifier_outils(tmp_path, lanceur, delai_s=0.05) == 1
    assert "délai" in capsys.readouterr().out


async def test_missing_password_fails_without_launching(
    monkeypatch: pytest.MonkeyPatch, chaine: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr(""))
    lanceur = LanceurDouble()
    assert await verifier_outils(tmp_path, lanceur) == 1
    assert lanceur.appels == []
    assert "mot de passe" in capsys.readouterr().out


async def test_missing_account_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    assert await verifier_outils(tmp_path, LanceurDouble()) == 1
