"""The Windows launcher starts suspended, assigns a job, then resumes — ticket-943."""
import ctypes
from types import SimpleNamespace
from typing import Any

import pytest

from tessera.services.providers import lanceur_windows
from tessera.services.providers.lanceur_windows import _ProcessInfo, _StartupInfo, lancer_dans_un_job
from tessera.services.providers.noms import ProviderIndisponible

CREATE_SUSPENDED = 0x4


class Appels:
    """Records the order of the Win32 calls of both DLLs."""

    def __init__(self, assignation_ok: bool = True, createur_ok: bool = True) -> None:
        self.ordre: list[str] = []
        self.flags = 0
        self._assignation_ok = assignation_ok
        self._createur_ok = createur_ok

    def CreateProcessWithLogonW(self, *args: Any) -> bool:  # noqa: N802
        self.ordre.append("create")
        self.flags = args[6]
        return self._createur_ok

    def AssignProcessToJobObject(self, job: Any, proc: Any) -> bool:  # noqa: N802
        self.ordre.append("assign")
        return self._assignation_ok

    def ResumeThread(self, thread: Any) -> int:  # noqa: N802
        self.ordre.append("resume")
        return 1

    def TerminateProcess(self, proc: Any, code: int) -> bool:  # noqa: N802
        self.ordre.append("terminate")
        return True

    def CloseHandle(self, handle: Any) -> bool:  # noqa: N802
        return True


@pytest.fixture(autouse=True)
def ctypes_sans_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lanceur_windows, "_CTYPES", SimpleNamespace(get_last_error=lambda: 0))


def _lancer(appels: Appels) -> tuple[bool, int]:
    si, info = _StartupInfo(), _ProcessInfo()
    si.cb = ctypes.sizeof(_StartupInfo)
    return lancer_dans_un_job(
        appels, appels, object(), ("agent", "mdp", "cmd", None, None), (si, info)
    )


def test_the_process_is_created_suspended_assigned_to_a_job_then_resumed() -> None:
    appels = Appels()
    ok, _ = _lancer(appels)
    assert ok
    assert appels.flags & CREATE_SUSPENDED
    assert appels.ordre == ["create", "assign", "resume"]


def test_a_refused_assignment_terminates_the_process_and_never_resumes_it() -> None:
    appels = Appels(assignation_ok=False)
    with pytest.raises(ProviderIndisponible):
        _lancer(appels)
    assert appels.ordre == ["create", "assign", "terminate"]


def test_a_refused_logon_touches_no_job() -> None:
    appels = Appels(createur_ok=False)
    ok, _ = _lancer(appels)
    assert not ok
    assert appels.ordre == ["create"]
