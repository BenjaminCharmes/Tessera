"""Both CLI transports report the pid of the process they start (ticket-900)."""
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from anyio.abc import Process
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

from tessera.services.providers.transport_agent import TransportCompteAgent, TransportSuivi


class LanceurPid:
    async def lancer(
        self, commande: Sequence[str], *, compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        faux: Any = SimpleNamespace(pid=777, stdout=None, stderr=None, stdin=None)
        return faux  # type: ignore[no-any-return]


def _options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(cli_path="cli", cwd=str(Path.cwd()), env={})


async def _icacls_double(args: list[str]) -> tuple[int, str]:
    return 0, ""


async def test_account_transport_reports_the_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tessera.services.providers.fichiers_appel._icacls_reel", _icacls_double)
    vus: list[int] = []
    transport = TransportCompteAgent(
        "p", _options(), lanceur=LanceurPid(), compte="c", mot_de_passe="m",
        au_demarrage=vus.append,
    )
    await transport.connect()
    assert vus == [777]


async def test_tracked_transport_reports_the_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    async def faux_connect(self: SubprocessCLITransport) -> None:
        self._process = SimpleNamespace(pid=555)  # type: ignore[assignment]

    monkeypatch.setattr(SubprocessCLITransport, "connect", faux_connect)
    vus: list[int] = []
    transport = TransportSuivi("p", _options(), au_demarrage=vus.append)
    await transport.connect()
    assert vus == [555]
