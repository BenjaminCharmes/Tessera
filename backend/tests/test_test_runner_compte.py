"""ticket-934: the test command runs under the dedicated account when declared."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from tessera.config import settings
from tessera.services.verification.test_runner import TestRunnerService
from tests.doubles_compte import LanceurDouble, ProcessDouble


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw"))


async def test_command_goes_through_the_account_launcher(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble(ProcessDouble(b"1 passed in 0.1s", b"", code=0))
    runner = TestRunnerService(compte_agent=True, lanceur=lanceur, env={"PYTHONPATH": "src"})
    with patch("asyncio.create_subprocess_exec") as direct:
        result = await runner.run_tests(tmp_path, test_command="pytest -q")
    direct.assert_not_called()
    assert result.passed is True
    assert lanceur.appels[0]["compte"] == "tessera-agent"
    assert lanceur.appels[0]["env"]["PYTHONPATH"] == "src"
    assert lanceur.appels[0]["cwd"] == str(tmp_path.resolve())


async def test_without_the_declared_account_the_command_starts_as_before(
    compte: None, tmp_path: Path
) -> None:
    lanceur = LanceurDouble()
    proc = MagicMock()
    proc.returncode = 0
    proc.pid = 1
    proc.communicate = AsyncMock(return_value=(b"1 passed", b""))
    with patch("asyncio.create_subprocess_exec", return_value=proc) as direct:
        await TestRunnerService(lanceur=lanceur).run_tests(tmp_path, test_command="pytest")
    direct.assert_called()
    assert lanceur.appels == []


async def test_launcher_failure_does_not_fall_back_to_the_backend_account(
    compte: None, tmp_path: Path
) -> None:
    lanceur = LanceurDouble(refus="logon refuse")
    runner = TestRunnerService(compte_agent=True, lanceur=lanceur)
    with patch("asyncio.create_subprocess_exec") as direct:
        result = await runner.run_tests(tmp_path, test_command="pytest")
    direct.assert_not_called()
    assert result.passed is False
    assert result.demarree is False
    assert "environnement" in result.output_summary


async def test_missing_password_is_an_environment_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr(""))
    runner = TestRunnerService(compte_agent=True, lanceur=LanceurDouble())
    with patch("asyncio.create_subprocess_exec") as direct:
        result = await runner.run_tests(tmp_path, test_command="pytest")
    direct.assert_not_called()
    assert result.demarree is False
