"""Ollama backend: a model served locally, no tools, no cost — ticket-189.

Il sert les rôles texte→JSON — sécurité, validateur, documentation,
analyseur — jamais ceux qui ont besoin d'outils : la boucle agentique, les
gardes d'ADR-027 et ADR-031, le budget et le quota vivent dans le SDK Claude.

L'API native (`/api/chat`) plutôt qu'une compatibilité OpenAI : elle rend les
compteurs de tokens, et c'est tout ce qu'on lui demande de plus que du texte.
"""
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from tessera.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)
from tessera.services.providers.noms import ProviderIndisponible

#: Le défaut d'Ollama est 4 096 tokens de contexte : le diff de 16 000
#: caractères que reçoit l'audit sécurité serait tronqué en silence, et le
#: verdict porterait sur sa moitié. Toujours envoyé, jamais en dessous.
NUM_CTX_MINIMUM = 16_384
#: Un modèle qui se charge en mémoire prend bien plus que les 5 s par défaut.
DELAI_LECTURE_S = 300.0
DELAI_CONNEXION_S = 5.0
#: Estimation grossière, volontairement pessimiste : un token vaut environ
#: trois caractères de code ou de français.
CARACTERES_PAR_TOKEN = 3


class OllamaProvider:
    """`/api/chat` on a local Ollama server. Reports `cost_usd = 0.0`."""

    name = "ollama"

    def __init__(
        self, base_url: str, client: httpx.AsyncClient | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client
        # Les modèles présents, lus une fois par instance : une instance vit
        # le temps d'un run, et un modèle n'y apparaît pas tout seul.
        self._modeles: set[str] | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(DELAI_LECTURE_S, connect=DELAI_CONNEXION_S),
            )
        return self._client

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
        # `cwd`, `ask_user`, `session` : pas d'outils, pas de conversation à
        # reprendre — ignorés, comme dans `AnthropicApiProvider`.
        await self._verifier_modele(model)
        corps = _corps(system, user, model, max_tokens, stream=False)
        try:
            reponse = await self._http().post("/api/chat", json=corps)
        except httpx.HTTPError as exc:
            raise ProviderIndisponible(f"Ollama injoignable : {exc}") from exc
        _verifier_statut(reponse)
        donnees = reponse.json()
        return _resultat(str(donnees.get("message", {}).get("content", "")), donnees)

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
        await self._verifier_modele(model)
        corps = _corps(system, user, model, max_tokens, stream=True)
        fragments: list[str] = []
        dernier: dict[str, Any] = {}
        try:
            async with self._http().stream("POST", "/api/chat", json=corps) as reponse:
                _verifier_statut(reponse)
                async for ligne in reponse.aiter_lines():
                    if not ligne.strip():
                        continue
                    donnees = json.loads(ligne)
                    fragment = str(donnees.get("message", {}).get("content", ""))
                    if fragment:
                        fragments.append(fragment)
                        if on_token is not None:
                            await on_token(fragment)
                    if donnees.get("done"):
                        dernier = donnees
        except httpx.HTTPError as exc:
            raise ProviderIndisponible(f"Ollama injoignable : {exc}") from exc
        return _resultat("".join(fragments), dernier)

    async def _verifier_modele(self, model: str) -> None:
        """Raises `ProviderIndisponible` when `model` is not installed.

        Jamais de `/api/pull` : dix-neuf gigaoctets ne se téléchargent pas en
        silence au milieu d'un run. Le repli prend le relais, et le dit.
        """
        if self._modeles is None:
            try:
                reponse = await self._http().get("/api/tags")
            except httpx.HTTPError as exc:
                raise ProviderIndisponible(f"Ollama injoignable : {exc}") from exc
            _verifier_statut(reponse)
            self._modeles = {
                str(m.get("name", "")) for m in reponse.json().get("models", [])
            }
        if model not in self._modeles and f"{model}:latest" not in self._modeles:
            raise ProviderIndisponible(
                f"Modèle {model!r} absent d'Ollama ({self.base_url}) : "
                f"`ollama pull {model}` pour l'installer."
            )


def _corps(system: str, user: str, model: str, max_tokens: int, *, stream: bool) -> dict[str, Any]:
    num_ctx = max(
        NUM_CTX_MINIMUM, (len(system) + len(user)) // CARACTERES_PAR_TOKEN + max_tokens
    )
    messages: list[dict[str, str]] = []
    if system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    return {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"num_ctx": num_ctx, "num_predict": max_tokens},
    }


def _verifier_statut(reponse: httpx.Response) -> None:
    if reponse.status_code >= 400:
        raise ProviderIndisponible(
            f"Ollama a répondu {reponse.status_code} : {reponse.text[:200]}"
        )


def _resultat(contenu: str, donnees: dict[str, Any]) -> ProviderResult:
    return ProviderResult(
        content=contenu,
        input_tokens=int(donnees.get("prompt_eval_count", 0) or 0),
        output_tokens=int(donnees.get("eval_count", 0) or 0),
        cost_usd=0.0,
        provider_name=OllamaProvider.name,
    )
