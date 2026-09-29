"""Recording wrapper for every LLM call within a pipeline run — ticket-211.

`AgentRunner` used to be the only recording point. Services like
`SecurityAuditorService`, `ValidatorService` and `DocumentationService` called
`provider.complete()` directly, and nothing tracked those calls.

`ProviderEnregistrant` wraps any `LLMProvider`. Each call is persisted to
`agent_calls` whenever an active run context is set. The context is set at the
start of `_run_pipeline` via `activer_enregistrement`, before the first agent,
so every call in the chain — codeur, security, reviewer, validator,
documentation — is recorded without the services knowing about it.

Calls made outside a run context (chat, project analysis) are transparent: the
provider behaves exactly as its inner provider, nothing is written.
"""
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from tessera.services.cost_calculator import calculate_cost
from tessera.services.database import save_agent_call
from tessera.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: The run currently in progress in this async task, or None outside a run.
_ctx_run_id: ContextVar[str | None] = ContextVar("recording_run_id", default=None)
_ctx_ticket_id: ContextVar[str | None] = ContextVar("recording_ticket_id", default=None)


def activer_enregistrement(run_id: str | None, ticket_id: str | None) -> None:
    """Set the recording context for the current async task.

    Must be called once at the start of ``_run_pipeline``. All LLM calls in
    the task's async chain then carry this context, and
    ``ProviderEnregistrant`` instances persist each call without the services
    having to know about it.
    """
    _ctx_run_id.set(run_id)
    _ctx_ticket_id.set(ticket_id)


class ProviderEnregistrant:
    """Transparent LLM provider wrapper that persists every call to ``agent_calls``.

    The services using the wrapped provider see no change in return values,
    parameters, or error behaviour. Recording is a side-effect that happens
    after the inner call completes — a failure to write to the database does
    not raise to the caller.

    Outside a run context (chat, project analysis) the wrapper is a
    pass-through: nothing is written.
    """

    def __init__(
        self,
        inner: LLMProvider,
        *,
        role: str,
        db_path: Path | str | None,
    ) -> None:
        self._inner = inner
        self._role = role
        self._db_path = db_path
        # Attribut et non propriété : le protocole `LLMProvider` déclare
        # `name` comme variable, et mypy refuse une lecture seule à sa place.
        self.name: str = inner.name

    def __getattr__(self, nom: str) -> Any:
        """Forward any other attribute to the inner provider.

        Callers inspect provider settings (`_allowed_tools`, `_tools`…); an
        envelope that hid them would change what they see.
        """
        return getattr(self._inner, nom)

    @property
    def quota(self) -> Any:
        """Forward the subscription quota if the inner provider tracks one."""
        return getattr(self._inner, "quota", None)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
    ) -> ProviderResult:
        """Forward to inner, then record."""
        kw: dict[str, Any] = {}
        if cwd is not None:
            kw["cwd"] = cwd
        if ask_user is not None:
            kw["ask_user"] = ask_user
        if session is not None:
            kw["session"] = session
        t0 = time.monotonic()
        result = await self._inner.complete(
            system=system, user=user, model=model, max_tokens=max_tokens, **kw
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        await self._enregistrer(result, model, duration_ms)
        return result

    async def stream(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        on_token: StreamCallback | None = None,
        on_tool_use: ToolEventCallback | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
    ) -> ProviderResult:
        """Forward to inner, then record."""
        kw: dict[str, Any] = {}
        if cwd is not None:
            kw["cwd"] = cwd
        if on_token is not None:
            kw["on_token"] = on_token
        if on_tool_use is not None:
            kw["on_tool_use"] = on_tool_use
        if ask_user is not None:
            kw["ask_user"] = ask_user
        if session is not None:
            kw["session"] = session
        t0 = time.monotonic()
        result = await self._inner.stream(
            system=system, user=user, model=model, max_tokens=max_tokens, **kw
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        await self._enregistrer(result, model, duration_ms)
        return result

    async def _enregistrer(
        self, result: ProviderResult, model_arg: str, duration_ms: int
    ) -> None:
        """Persist the call if a run context is active, silently otherwise."""
        run_id = _ctx_run_id.get()
        ticket_id = _ctx_ticket_id.get()
        if not run_id or not ticket_id or not self._db_path:
            return

        modele_utilise = result.model or model_arg
        provider_name = result.provider_name or self._inner.name
        cost_usd: float = (
            result.cost_usd
            if result.cost_usd is not None
            else calculate_cost(
                modele_utilise,
                result.input_tokens,
                result.output_tokens,
                result.cache_read_tokens,
            )
        )
        try:
            await save_agent_call(
                self._db_path,
                run_id,
                ticket_id,
                self._role,
                modele_utilise,
                result.input_tokens,
                result.output_tokens,
                result.cache_read_tokens,
                cost_usd,
                duration_ms,
                provider=provider_name,
            )
        except Exception as exc:  # noqa: BLE001 — un enregistrement raté ne casse rien
            _logger.warning(
                "provider_enregistrant_save_failed",
                extra={"role": self._role, "error": str(exc)},
            )
