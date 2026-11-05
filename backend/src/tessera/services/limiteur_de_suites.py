"""Shared slot bounding concurrent test runs, whose limit is re-read (ticket-807).

Un `asyncio.Semaphore` fige sa valeur à la création : un réglage changé depuis
l'interface (ADR-075) n'y serait jamais lu. Ce limiteur relit la limite à chaque
acquisition. Un créneau déjà tenu se garde ; une limite relevée ne réveille pas
ceux qui attendent déjà, elle vaut à la prochaine libération ou acquisition.
"""
import asyncio
from types import TracebackType

from tessera import reglages


class LimiteurDeSuites:
    """Counting limiter with a limit read at each acquisition.

    `limite` force a value (tests only); otherwise the limit comes from
    `reglages.du_moment().max_parallel_test_runs`. A limit of 0 or less means
    no bound. A raised limit does not wake current waiters: it applies at the
    next release or acquisition.
    """

    def __init__(self, limite: int | None = None) -> None:
        self._forcee = limite
        self._tenus = 0
        self._attente: asyncio.Condition | None = None

    def _limite(self) -> int:
        if self._forcee is not None:
            return self._forcee
        return reglages.du_moment().max_parallel_test_runs

    def _condition(self) -> asyncio.Condition:
        # Créée à la demande : pas de boucle asyncio à l'import (ticket-348).
        if self._attente is None:
            self._attente = asyncio.Condition()
        return self._attente

    def tenus(self) -> int:
        """Number of slots currently held."""
        return self._tenus

    def libre(self) -> bool:
        """Whether a slot could be taken right now without waiting."""
        limite = self._limite()
        return limite <= 0 or self._tenus < limite

    async def acquire(self) -> None:
        """Take a slot, waiting while the limit read now is reached."""
        condition = self._condition()
        async with condition:
            await condition.wait_for(self.libre)
            self._tenus += 1

    def release(self) -> None:
        """Give a slot back and wake the waiters, which re-read the limit."""
        self._tenus = max(0, self._tenus - 1)
        if self._attente is not None:
            asyncio.get_running_loop().create_task(self._reveiller())

    async def _reveiller(self) -> None:
        async with self._condition():
            self._condition().notify_all()

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
