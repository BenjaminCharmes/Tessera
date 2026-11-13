"""ticket-948: the tester repairs a refused venv launcher, then retries once."""
from collections.abc import Awaitable, Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tessera.services.verification import reprise_sac
from tessera.services.verification.test_runner import TestRunnerService

REFUS = "error: failed to spawn .venv\\Scripts\\python.exe: os error 4551"


def _projet(racine: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    uv = racine / "uvroot" / "cpython-3.11"
    uv.mkdir(parents=True)
    for nom in ("python.exe", "pythonw.exe"):
        (uv / nom).write_bytes(b"base")
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(uv.parent))
    projet = racine / "projet"
    scripts = projet / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_bytes(b"lanceur")
    (projet / ".venv" / "pyvenv.cfg").write_text(f"home = {uv}\n", encoding="utf-8")
    (projet / "pyproject.toml").write_text("", encoding="utf-8")
    return projet


def _attente(sortie: str) -> Callable[[], Awaitable[tuple[bytes, bytes]]]:
    async def communicate() -> tuple[bytes, bytes]:
        return sortie.encode(), b""

    return communicate


def _proc(code: int, sortie: str) -> MagicMock:
    proc = MagicMock()
    proc.returncode = code
    proc.communicate = _attente(sortie)
    return proc


def _lanceur(monkeypatch: pytest.MonkeyPatch, procs: list[MagicMock]) -> list[int]:
    appels: list[int] = []

    async def lancer(self: TestRunnerService, args: list[str], dossier: Path) -> MagicMock:
        appels.append(1)
        return procs[min(len(appels), len(procs)) - 1]

    monkeypatch.setattr(TestRunnerService, "_lancer", lancer)
    return appels


async def test_tester_repairs_logs_and_retries_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, monkeypatch)
    monkeypatch.setattr(reprise_sac, "_est_windows", lambda: True)
    journal = MagicMock()
    monkeypatch.setattr(reprise_sac, "_logger", journal)
    appels = _lanceur(monkeypatch, [_proc(1, REFUS), _proc(0, "1 passed")])

    result = await TestRunnerService().run_tests(projet, test_command="python -m pytest")

    assert result.passed is True
    assert len(appels) == 2
    assert journal.warning.call_args.args[0] == "venv_repare"
    assert (projet / ".venv" / "Scripts" / "python.exe").read_bytes() == b"base"
    assert (projet / ".venv" / "Scripts" / "python.exe.lanceur-uv").exists()


async def test_two_failures_are_an_environment_failure_without_third_try(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, monkeypatch)
    monkeypatch.setattr(reprise_sac, "_est_windows", lambda: True)
    appels = _lanceur(monkeypatch, [_proc(1, REFUS)])

    result = await TestRunnerService().run_tests(projet, test_command="python -m pytest")

    assert result.passed is False
    assert result.demarree is False
    assert len(appels) == 2


async def test_repair_is_never_called_off_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, monkeypatch)
    monkeypatch.setattr(reprise_sac, "_est_windows", lambda: False)
    reparer = MagicMock()
    monkeypatch.setattr(reprise_sac, "reparer_venv", reparer)
    appels = _lanceur(monkeypatch, [_proc(1, REFUS)])

    result = await TestRunnerService().run_tests(projet, test_command="python -m pytest")

    reparer.assert_not_called()
    assert len(appels) == 1
    assert result.passed is False


def test_refusal_needs_a_venv_and_a_marker() -> None:
    assert reprise_sac.refuse_par_sac(REFUS)
    assert not reprise_sac.refuse_par_sac("os error 4551 on C:\\tools\\x.exe")
    assert not reprise_sac.refuse_par_sac("1 failed in .venv tests")


async def test_service_launch_retries_once_after_a_4551_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, monkeypatch)
    monkeypatch.setattr(reprise_sac, "_est_windows", lambda: True)
    erreur = OSError(4551, "refused")
    erreur.winerror = 4551  # type: ignore[attr-defined]

    async def refaire() -> str:
        return "relance"

    assert await reprise_sac.relancer_si_refuse(erreur, refaire, projet, projet, "p") == "relance"
    with pytest.raises(OSError):
        await reprise_sac.relancer_si_refuse(OSError("autre"), refaire, projet, projet, "p")
