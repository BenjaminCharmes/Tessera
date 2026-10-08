"""Ollama backend: a model served locally, no tools, no cost — ticket-189.

Il sert les rôles texte→JSON — sécurité, validateur, documentation,
analyseur — jamais ceux qui ont besoin d'outils : la boucle agentique, les
gardes d'ADR-027 et ADR-031, le budget et le quota vivent dans le SDK Claude.

L'API native (`/api/chat`) plutôt qu'une compatibilité OpenAI : elle rend les
compteurs de tokens, et c'est tout ce qu'on lui demande de plus que du texte.
"""
import asyncio
import json
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
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

# --- Sérialisation par serveur (ticket-350) ---

# Registre module-level : base_url → sémaphore.
# Partagé par tous les OllamaProvider du processus pour sérialiser les
# requêtes vers le même serveur Ollama. Créé paresseusement à la première
# demande pour chaque serveur distinct.
_SLOTS: dict[str, asyncio.Semaphore] = {}


def _get_slot(base_url: str) -> asyncio.Semaphore | None:
    """Returns the shared semaphore for *base_url*, or None when unbounded."""
    from tessera.config import settings

    limit = settings.ollama_max_concurrent
    if limit <= 0:
        return None
    if base_url not in _SLOTS:
        _SLOTS[base_url] = asyncio.Semaphore(limit)
    return _SLOTS[base_url]


@asynccontextmanager
async def _maybe_slot(base_url: str) -> AsyncGenerator[None, None]:
    """Acquiert le créneau avant d'entrer, le rend à la sortie.

    Raises `ProviderIndisponible` si le créneau n'est pas libre dans
    `ollama_slot_wait_s` secondes — sans envoyer aucune requête HTTP.
    """
    slot = _get_slot(base_url)
    if slot is None:
        yield
        return

    from tessera.config import settings

    wait_s = settings.ollama_slot_wait_s
    try:
        await asyncio.wait_for(slot.acquire(), timeout=wait_s)
    except asyncio.TimeoutError:
        raise ProviderIndisponible(
            f"Ollama : créneau occupé depuis plus de {wait_s:.0f} s"
        )
    try:
        yield
    finally:
        slot.release()


def _reset_slots() -> None:
    """Clear the semaphore registry — for tests only."""
    _SLOTS.clear()


# --- Disjoncteur par serveur (ticket-380) ---

# Registre module-level : base_url → horodatage d'expiry du refroidissement.
# Après un dépassement du délai de lecture, le serveur est marqué lent pendant
# `ollama_cooldown_s` secondes ; tout appel pendant ce temps lève
# `ProviderIndisponible` aussitôt, sans requête HTTP.
_COOLDOWNS: dict[str, float] = {}

#: Horloge utilisée par le disjoncteur. Variable pour permettre les tests.
_clock: Callable[[], float] = time.monotonic


def _check_cooldown(base_url: str) -> None:
    """Raises `ProviderIndisponible` immédiatement si le serveur est en refroidissement."""
    expiry = _COOLDOWNS.get(base_url)
    if expiry is not None and _clock() < expiry:
        raise ProviderIndisponible(
            f"Ollama : serveur {base_url!r} en refroidissement"
        )


def _set_cooldown(base_url: str) -> None:
    """Marque *base_url* comme lent pour `ollama_cooldown_s` secondes."""
    from tessera.config import settings

    _COOLDOWNS[base_url] = _clock() + settings.ollama_cooldown_s


def _reset_cooldowns() -> None:
    """Clear the cooldown registry — for tests only."""
    _COOLDOWNS.clear()


# --- Provider ---


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
        _check_cooldown(self.base_url)
        await self._verifier_modele(model)
        corps = _corps(system, user, model, max_tokens, stream=False)
        # Le créneau est pris avant d'envoyer la requête : le délai de lecture
        # httpx ne court qu'à partir de l'envoi, pas pendant l'attente du slot.
        async with _maybe_slot(self.base_url):
            try:
                reponse = await self._http().post("/api/chat", json=corps)
            except httpx.ReadTimeout as exc:
                _set_cooldown(self.base_url)
                raise ProviderIndisponible(
                    f"Ollama : délai dépassé ({DELAI_LECTURE_S:.0f} s)"
                ) from exc
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
        _check_cooldown(self.base_url)
        await self._verifier_modele(model)
        corps = _corps(system, user, model, max_tokens, stream=True)
        fragments: list[str] = []
        dernier: dict[str, Any] = {}
        # Le créneau est tenu pendant tout le flux : un flux interrompu (exception
        # du consommateur ou réseau) sort du contextmanager et rend le créneau.
        async with _maybe_slot(self.base_url):
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
            except httpx.ReadTimeout as exc:
                _set_cooldown(self.base_url)
                raise ProviderIndisponible(
                    f"Ollama : délai dépassé ({DELAI_LECTURE_S:.0f} s)"
                ) from exc
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
