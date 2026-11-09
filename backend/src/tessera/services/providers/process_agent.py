"""An ``anyio`` process over handles the agent launcher gives back (ADR-083).

Le transport du SDK ne parle qu'à l'interface `anyio.abc.Process` : tuyaux
d'octets, `wait`, `terminate`, `kill`. Les lectures bloquantes passent par un fil.
"""
from collections.abc import Callable
from typing import BinaryIO

import anyio
from anyio import EndOfStream
from anyio.abc import ByteReceiveStream, ByteSendStream, Process

#: Un code de sortie que le système n'a pas encore donné.
_ENCORE_ACTIF = None


class FluxLecture(ByteReceiveStream):
    """Reads a blocking binary file, one thread hop per call."""

    def __init__(self, fichier: BinaryIO) -> None:
        self._fichier = fichier

    async def receive(self, max_bytes: int = 65536) -> bytes:
        # Fichier sans tampon : `read(n)` rend ce qui est là, dès qu'il y a un octet.
        octets: bytes = await anyio.to_thread.run_sync(
            self._fichier.read, max_bytes, abandon_on_cancel=True
        )
        if not octets:
            raise EndOfStream
        return octets

    async def aclose(self) -> None:
        self._fichier.close()


class FluxEcriture(ByteSendStream):
    """Writes a blocking binary file, flushing after each item."""

    def __init__(self, fichier: BinaryIO) -> None:
        self._fichier = fichier

    def _ecrire(self, item: bytes) -> None:
        self._fichier.write(item)
        self._fichier.flush()

    async def send(self, item: bytes) -> None:
        await anyio.to_thread.run_sync(self._ecrire, item)

    async def aclose(self) -> None:
        self._fichier.close()


class ProcessAgent(Process):
    """The child started under the agent account."""

    def __init__(
        self,
        *,
        pid: int,
        attendre: Callable[[], int],
        arreter: Callable[[], None],
        sonder: Callable[[], int | None],
        stdin: BinaryIO,
        stdout: BinaryIO,
        stderr: BinaryIO | None,
    ) -> None:
        self._pid = pid
        self._attendre = attendre
        self._arreter = arreter
        self._sonder = sonder
        self._code: int | None = _ENCORE_ACTIF
        self._stdin = FluxEcriture(stdin)
        self._stdout = FluxLecture(stdout)
        self._stderr = FluxLecture(stderr) if stderr is not None else None

    async def wait(self) -> int:
        if self._code is None:
            self._code = await anyio.to_thread.run_sync(self._attendre, abandon_on_cancel=True)
        return self._code

    def terminate(self) -> None:
        self._arreter()

    def kill(self) -> None:
        self._arreter()

    def send_signal(self, signal: int) -> None:  # noqa: ARG002 — Windows n'en a pas d'autre
        self._arreter()

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def returncode(self) -> int | None:
        if self._code is None:
            self._code = self._sonder()
        return self._code

    @property
    def stdin(self) -> ByteSendStream:
        return self._stdin

    @property
    def stdout(self) -> ByteReceiveStream:
        return self._stdout

    @property
    def stderr(self) -> ByteReceiveStream | None:
        return self._stderr

    async def aclose(self) -> None:
        await self._stdin.aclose()
        await self._stdout.aclose()
        if self._stderr is not None:
            await self._stderr.aclose()
