"""Test doubles for a process started under the dedicated account."""
from collections.abc import Mapping, Sequence
from typing import Any

from anyio import EndOfStream
from anyio.abc import Process

from tessera.services.providers.noms import ProviderIndisponible


class FluxDouble:
    """A readable pipe that gives its bytes once, then ends."""

    def __init__(self, donnees: bytes) -> None:
        self._donnees = donnees

    async def receive(self, max_bytes: int = 65536) -> bytes:
        if not self._donnees:
            raise EndOfStream
        donnees, self._donnees = self._donnees, b""
        return donnees

    async def aclose(self) -> None:
        self._donnees = b""


class ProcessDouble:
    """The surface of `anyio.abc.Process` that the adapter uses."""

    def __init__(self, sortie: bytes = b"", erreur: bytes = b"", code: int = 0) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.stdin = FluxDouble(b"")
        self.stdout = FluxDouble(sortie)
        self.stderr = FluxDouble(erreur)
        self._code = code
        self.tue = False

    async def wait(self) -> int:
        self.returncode = self._code
        return self._code

    def kill(self) -> None:
        self.tue = True
        self.returncode = 1

    def terminate(self) -> None:
        self.kill()


class LanceurDouble:
    """A `LanceurAgent` that records its calls, or refuses them."""

    def __init__(self, processus: ProcessDouble | None = None, refus: str | None = None) -> None:
        self.appels: list[dict[str, Any]] = []
        self.processus = processus or ProcessDouble()
        self._refus = refus

    async def lancer(
        self, commande: Sequence[str], *, compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        self.appels.append({"commande": list(commande), "compte": compte, "env": dict(env), "cwd": cwd})
        if self._refus is not None:
            raise ProviderIndisponible(self._refus)
        return self.processus  # type: ignore[return-value]
