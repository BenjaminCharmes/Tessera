"""The last step of a run: the site answers, and so does a route that reads the database — ticket-503.

A build that does not apply the migrations leaves every page answering 200 over
an empty database. The route declared as ``health_path`` reads a table, so a
missing or unreachable database shows up the day the project is put online.
Without it, only the root is checked, and the detail says the database is not.
"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Optional

import httpx

from tessera.services.provisioning.steps import ProvisioningContext, StepResult, StepState

_TIMEOUT_S = 10.0
_ATTEMPTS = 6
_DELAY_S = 10.0
_BODY_CHARS = 200
_NOT_CHECKED = "database not checked: declare health_path"

Sleep = Callable[[float], Awaitable[None]]


class HealthCheckStep:
    """``GET https://<domain><health_path>`` until it answers 200, a few times."""

    name = "health_check"

    def __init__(
        self,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        attempts: int = _ATTEMPTS,
        delay_s: float = _DELAY_S,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._transport = transport
        self._attempts = max(1, attempts)
        self._delay_s = delay_s
        self._sleep = sleep

    @staticmethod
    def url(ctx: ProvisioningContext) -> str:
        """The address probed: the declared health route, the root otherwise."""
        return f"https://{ctx.online.domain}{ctx.online.health_path or '/'}"

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Nothing to read without waiting on a deployment: say what apply would probe."""
        return StepResult(StepState.TODO, f"will check {self.url(ctx)}")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Probe the site, spacing the attempts; the last answer decides."""
        url = self.url(ctx)
        echec = ""
        for essai in range(self._attempts):
            if essai:
                await self._sleep(self._delay_s)
            reponse = await self._get(url)
            if isinstance(reponse, httpx.Response):
                if reponse.status_code == 200:
                    return self._done(ctx, url)
                echec = f"{reponse.status_code} {reponse.text[:_BODY_CHARS]}".strip()
            else:
                echec = reponse
        return StepResult(StepState.FAILED, f"{url} did not answer 200: {echec}")

    def _done(self, ctx: ProvisioningContext, url: str) -> StepResult:
        if ctx.online.health_path:
            return StepResult(StepState.DONE, f"{url} answers 200")
        return StepResult(StepState.DONE, f"{url} answers 200; {_NOT_CHECKED}")

    async def _get(self, url: str) -> httpx.Response | str:
        """The response, or the kind of network failure (never its message)."""
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=_TIMEOUT_S) as http:
                return await http.get(url)
        except httpx.HTTPError as erreur:
            # Le message d'une erreur réseau peut citer la requête : seul le type sort.
            return f"unreachable ({type(erreur).__name__})"
