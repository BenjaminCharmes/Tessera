"""The test step writes no bytecode (ticket-979)."""
import sys
from pathlib import Path

from tessera.services.verification.test_runner import TestRunnerService


def test_step_env_carries_the_variable_and_keeps_the_declared_env() -> None:
    env = TestRunnerService(env={"PYTHONPATH": "src"})._env

    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PYTHONPATH"] == "src"


def test_step_env_without_declared_env() -> None:
    assert TestRunnerService()._env == {"PYTHONDONTWRITEBYTECODE": "1"}


async def test_launched_step_sees_the_variable(tmp_path: Path) -> None:
    proc = await TestRunnerService()._lancer(
        [sys.executable, "-c", "import os; print(os.environ['PYTHONDONTWRITEBYTECODE'])"],
        tmp_path,
    )
    sortie, _ = await proc.communicate()

    assert sortie.decode().strip() == "1"
