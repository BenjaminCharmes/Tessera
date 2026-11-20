"""Stopping a service whose process is already gone is not a failure (ticket-744)."""
import asyncio
from typing import Any

import pytest

from tessera.services.verification import process_registry
from tessera.services.verification.process_registry import ProcessRegistry, Service


class FakeProcess:
    """Process double: `terminate` raises what it is told to."""

    pid = 4242

    def __init__(self, terminate_error: Exception | None) -> None:
        self.returncode: int | None = None
        self.waited = False
        self._terminate_error = terminate_error

    def terminate(self) -> None:
        if self._terminate_error is not None:
            raise self._terminate_error

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        self.waited = True
        self.returncode = 0
        return 0


class RecordingLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict[str, Any]]] = []

    def warning(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self.warnings.append((message, extra or {}))


@pytest.fixture
def journal(monkeypatch: pytest.MonkeyPatch) -> RecordingLogger:
    logger = RecordingLogger()

    async def fake_kill_tree(pid: int) -> None:
        return None

    monkeypatch.setattr(process_registry, "_logger", logger)
    monkeypatch.setattr(process_registry, "tuer_l_arbre", fake_kill_tree)
    return logger


def _stop(error: Exception | None) -> FakeProcess:
    process = FakeProcess(error)
    service = Service(nom="web", project_id="p", pid=process.pid, processus=process)
    asyncio.run(ProcessRegistry()._terminer(service))
    return process


def test_terminate_on_a_dead_process_is_not_logged_as_failure(
    journal: RecordingLogger,
) -> None:
    process = _stop(ProcessLookupError())

    assert journal.warnings == []
    assert process.waited is True


def test_other_exception_is_logged_with_its_type_even_when_message_is_empty(
    journal: RecordingLogger,
) -> None:
    _stop(PermissionError())

    assert journal.warnings == [
        ("arret_service_echoue", {"erreur": "PermissionError"})
    ]


def test_other_exception_keeps_its_message_after_the_type(
    journal: RecordingLogger,
) -> None:
    _stop(OSError("boom"))

    assert journal.warnings == [
        ("arret_service_echoue", {"erreur": "OSError: boom"})
    ]
