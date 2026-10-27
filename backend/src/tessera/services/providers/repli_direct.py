"""The fallback provider used straight away, for a run launched in fast mode — ticket-578.

Le repli déclaré d'un rôle (ADR-046) ne joue d'ordinaire qu'à l'indisponibilité
du principal. Un run « rapide » le choisit d'emblée : le principal n'est pas
construit, et chaque appel porte le modèle du repli, pas celui que l'appelant
tient du principal — Haiku ne doit pas recevoir le nom d'un modèle Ollama.
"""
from pathlib import Path
from typing import Any

from tessera.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)


class ProviderRepliDirect:
    """Wraps `repli` and forces `modele` on every call."""

    def __init__(self, repli: LLMProvider, *, modele: str) -> None:
        self._repli = repli
        self._modele = modele
        self.name: str = repli.name

    @property
    def quota(self) -> Any:
        """Le quota du provider enveloppé, s'il en suit un (ticket-054)."""
        return getattr(self._repli, "quota", None)

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
        result = await self._repli.complete(
            system=system, user=user, model=self._modele,
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
        result = await self._repli.stream(
            system=system, user=user, model=self._modele, max_tokens=max_tokens,
            cwd=cwd, on_token=on_token, on_tool_use=on_tool_use, **extra,
        )
        return self._marquer(result)

    def _marquer(self, result: ProviderResult) -> ProviderResult:
        # Ce qui a réellement tourné, pour la ventilation des coûts.
        result.model = self._modele
        if not result.provider_name:
            result.provider_name = self._repli.name
        return result
