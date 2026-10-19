"""ticket-512: a test command never inherits the backend's standard input."""
import asyncio
import shlex
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from tessera.services.test_runner import TestRunnerService


async def test_each_step_is_launched_with_a_closed_stdin(tmp_path: Path) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"1 passed", b""))
    captured: dict[str, object] = {}

    async def fake_exec(*args: object, **kwargs: object) -> MagicMock:
        captured.update(kwargs)
        return mock_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        await TestRunnerService().run_tests(tmp_path, test_command="make test")

    assert captured["stdin"] == asyncio.subprocess.DEVNULL


async def test_a_command_reading_stdin_ends_at_once_with_empty_input(
    tmp_path: Path,
) -> None:
    # Le code de sortie vaut la longueur de ce qui a été lu : 0 si l'entrée
    # est vide. Sans entrée fermée, le test se bloquerait jusqu'au délai.
    code = "import sys; sys.exit(len(sys.stdin.read()))"
    python = Path(sys.executable).as_posix()
    commande = f"{shlex.quote(python)} -c {shlex.quote(code)}"

    result = await TestRunnerService().run_tests(
        tmp_path, test_command=commande, timeout=30
    )

    assert result.expiree is False
    assert result.passed is True
    assert result.etapes[0].code == 0
