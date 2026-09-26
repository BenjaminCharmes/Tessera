"""A provider that falls back to another one when the first cannot answer — ticket-188.

Un modèle local n'est pas sur toutes les machines. Le repli est ce qui rend
un `agents.json` portable : le même manifeste tourne là où Ollama est là,
et retombe sur Claude ailleurs — en le disant.
"""
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)
from tessera.services.providers.noms import ProviderIndisponible
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


class ProviderAvecRepli:
    """Calls `principal`; on `ProviderIndisponible`, calls `repli` with
    `modele_repli` instead and says so on the observation channel.

    Seule l'indisponibilité déclenche le repli. Une réponse illisible ou une
    faille de contenu passe telle quelle : ADR-039 fait échouer fermé les
    portes du pipeline, et un repli silencieux masquerait un modèle qui ne
    tient pas au lieu de le montrer.
    """

    def __init__(
        self,
        principal: LLMProvider,
        repli: LLMProvider,
        *,
        modele_repli: str,
        role: str,
        project_id: str | None,
    ) -> None:
        self._principal = principal
        self._repli = repli
        self._modele_repli = modele_repli
        self._role = role
        self._project_id = project_id
        # Attribut et non propriété : le protocole `LLMProvider` déclare
        # `name` comme variable, et mypy refuse une lecture seule à sa place.
        self.name: str = principal.name

    @property
    def quota(self) -> Any:
        """Le quota du principal, s'il en suit un : le routeur le lit par
        `getattr`, et un enveloppement ne doit pas l'en priver (ticket-054)."""
        return getattr(self._principal, "quota", None)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        **extra: Any,
    ) -> ProviderResult:
        try:
            return await self._principal.complete(
                system=system, user=user, model=model, max_tokens=max_tokens, cwd=cwd, **extra
            )
        except ProviderIndisponible as exc:
            await self._annoncer(exc)
            result = await self._repli.complete(
                system=system, user=user, model=self._modele_repli,
                max_tokens=max_tokens, cwd=cwd, **extra,
            )
            return self._marquer(result)

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
        **extra: Any,
    ) -> ProviderResult:
        try:
            return await self._principal.stream(
                system=system, user=user, model=model, max_tokens=max_tokens, cwd=cwd,
                on_token=on_token, on_tool_use=on_tool_use, **extra,
            )
        except ProviderIndisponible as exc:
            await self._annoncer(exc)
            result = await self._repli.stream(
                system=system, user=user, model=self._modele_repli,
                max_tokens=max_tokens, cwd=cwd,
                on_token=on_token, on_tool_use=on_tool_use, **extra,
            )
            return self._marquer(result)

    def _marquer(self, result: ProviderResult) -> ProviderResult:
        # Ce qui a réellement tourné, pour la ventilation des coûts : le
        # modèle demandé n'est pas celui qui a répondu.
        result.model = self._modele_repli
        if not result.provider_name:
            result.provider_name = self._repli.name
        return result

    async def _annoncer(self, cause: ProviderIndisponible) -> None:
        _logger.warning(
            "provider_fallback",
            extra={
                "role": self._role, "tente": self._principal.name,
                "utilise": self._repli.name, "error": str(cause),
            },
        )
        try:
            await EVENT_HUB.publish(
                OrchestratorEvent(
                    type=EventType.PROVIDER_FALLBACK,
                    ticket_id="",
                    project_id=self._project_id,
                    data={
                        "role": self._role,
                        "tente": self._principal.name,
                        "utilise": self._repli.name,
                        "modele": self._modele_repli,
                        "raison": str(cause),
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001 — un émetteur qui lève n'arrête rien (ADR-038)
            _logger.warning("provider_fallback_emit_failed", extra={"error": str(exc)})


#: Ce que la fabrique par rôle rend : un provider, éventuellement enveloppé.
FabriqueParRole = Callable[[str], LLMProvider]
Annonceur = Callable[[OrchestratorEvent], Awaitable[None]]
