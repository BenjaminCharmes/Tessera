"""Any OpenAI-compatible endpoint, declared by base URL — ticket-669.

OpenRouter, LM Studio, vLLM : `POST {base_url}/chat/completions`. Comme
Ollama, il sert les rôles texte→JSON, jamais ceux qui ont besoin d'outils : la
boucle agentique, les gardes d'ADR-027 et ADR-031, le budget et le quota
vivent dans le SDK Claude. `cwd`, `ask_user` et `session` sont ignorés.

Seule l'indisponibilité (connexion, délai, statut ≥ 400, réponse qui n'est pas
du JSON compatible) lève `ProviderIndisponible` et déclenche le repli du rôle.
"""
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from tessera.services.providers import openai_corps
from tessera.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)
from tessera.services.providers.duree_max import borner
from tessera.services.providers.noms import ProviderIndisponible

#: Un modèle distant peut réfléchir longtemps avant le premier octet.
DELAI_LECTURE_S = 300.0
DELAI_CONNEXION_S = 5.0

_PREFIXE_SSE = "data:"
_FIN_SSE = "[DONE]"


class OpenAICompatibleProvider:
    """`/chat/completions` on an OpenAI-compatible server. Reports `cost_usd = 0.0`."""

    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        client: httpx.AsyncClient | None = None,
        duree_max_s: float | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client
        # Durée totale d'un appel (ticket-518). None : pas de borne.
        self._duree_max_s = duree_max_s

    def __repr__(self) -> str:
        # Jamais la clé : un repr finit dans un log ou une trace.
        return f"OpenAICompatibleProvider(base_url={self.base_url!r})"

    @property
    def _url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(DELAI_LECTURE_S, connect=DELAI_CONNEXION_S)
            )
        return self._client

    def _en_tetes(self) -> dict[str, str]:
        # Sans clé, aucun en-tête : un serveur local n'en demande pas.
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

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
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        requete = openai_corps.corps(
            system, user, model, max_tokens, stream=False, schema=schema
        )
        async with borner(self._duree_max_s):
            try:
                reponse = await self._http().post(
                    self._url, json=requete, headers=self._en_tetes()
                )
            except httpx.HTTPError as exc:
                raise ProviderIndisponible(
                    f"Point d'accès compatible OpenAI injoignable : {_cause(exc)}"
                ) from exc
        openai_corps.verifier_statut(reponse)
        donnees = openai_corps.lire_json(reponse)
        choix = openai_corps.premier_choix(donnees)
        return openai_corps.resultat(
            openai_corps.texte_du_message(choix),
            donnees.get("usage"), choix.get("finish_reason"), schema,
        )

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
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        requete = openai_corps.corps(
            system, user, model, max_tokens, stream=True, schema=schema
        )
        async with borner(self._duree_max_s):
            fragments, usage, fin = await self._lire_flux(requete, on_token)
        return openai_corps.resultat("".join(fragments), usage, fin, schema)

    async def _lire_flux(
        self, requete: dict[str, Any], on_token: StreamCallback | None
    ) -> tuple[list[str], object, object]:
        """Reads the SSE stream: the text fragments, the usage, the finish reason."""
        fragments: list[str] = []
        usage: object = None
        fin: object = None
        try:
            async with self._http().stream(
                "POST", self._url, json=requete, headers=self._en_tetes()
            ) as reponse:
                if reponse.status_code >= 400:
                    await reponse.aread()
                openai_corps.verifier_statut(reponse)
                async for ligne in reponse.aiter_lines():
                    morceau = _morceau(ligne)
                    if morceau is None:
                        continue
                    usage = morceau.get("usage") or usage
                    fin, fragment = _lire_morceau(morceau, fin)
                    if fragment:
                        fragments.append(fragment)
                        if on_token is not None:
                            await on_token(fragment)
        except httpx.HTTPError as exc:
            raise ProviderIndisponible(
                f"Point d'accès compatible OpenAI injoignable : {_cause(exc)}"
            ) from exc
        return fragments, usage, fin


def _cause(exc: httpx.HTTPError) -> str:
    """Le type de l'erreur et son texte ; `httpx` n'y met jamais d'en-tête."""
    return f"{type(exc).__name__} {exc}".strip()


def _morceau(ligne: str) -> dict[str, Any] | None:
    """The JSON object of one SSE line, or ``None`` for a comment, a blank
    line, the closing `[DONE]` or a line that is not an object."""
    ligne = ligne.strip()
    if not ligne.startswith(_PREFIXE_SSE):
        return None
    charge = ligne[len(_PREFIXE_SSE):].strip()
    if not charge or charge == _FIN_SSE:
        return None
    try:
        valeur = json.loads(charge)
    except ValueError:
        return None
    return valeur if isinstance(valeur, dict) else None


def _lire_morceau(morceau: dict[str, Any], fin: object) -> tuple[object, str]:
    """The finish reason so far and the text carried by one chunk."""
    choix = morceau.get("choices")
    if not isinstance(choix, list) or not choix or not isinstance(choix[0], dict):
        return fin, ""
    delta = choix[0].get("delta")
    texte = delta.get("content") if isinstance(delta, dict) else None
    return choix[0].get("finish_reason") or fin, texte if isinstance(texte, str) else ""
