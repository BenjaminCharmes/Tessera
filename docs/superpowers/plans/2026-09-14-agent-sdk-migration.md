# Migration vers le Claude Agent SDK — plan d'implémentation (phases 2–3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire passer les agents de vibe-ide de l'API Messages au Claude Agent SDK, derrière une couche `LLMProvider`, pour qu'ils écrivent réellement dans le workspace et consomment l'abonnement plutôt que des crédits API.

**Architecture :** Un package `services/providers/` définit un protocole `LLMProvider` avec deux implémentations : `AnthropicApiProvider` (le code actuel, déplacé sans changement de comportement) et `ClaudeAgentSDKProvider` (SDK, outils fichier, auth par abonnement). `AgentRunner` conserve sa signature publique et son `AgentResult` ; il reçoit un provider à la construction au lieu d'un `AsyncAnthropic`. Tout l'aval — orchestrateur, routers, events WebSocket — reste inchangé.

**Tech Stack :** Python 3.11, `claude-agent-sdk` 0.2.152 (déjà installé), `anthropic`, FastAPI, pytest, uv.

## État de départ

**La suite de tests est rouge à la collecte avant la Task 1.** `Settings()` est
instancié à l'import de `config.py` et exige `anthropic_api_key` ; il n'existe ni
`backend/.env` ni variable d'environnement. `uv run pytest` échoue donc sur
`tests/test_agent_admin.py` avec une `ValidationError` de pydantic. Ce n'est pas
une régression : c'est le défaut que la Task 1 corrige. À partir de la Task 1,
toute suite rouge est une vraie régression.

## Global Constraints

- Type hints partout, sans exception. `snake_case`. Docstrings en anglais, commentaires en français.
- `async/await` partout ; aucun appel bloquant dans un chemin async.
- Fichiers de moins de 200 lignes ; un test par fonction publique au minimum.
- Commits en Conventional Commits, en anglais. Branche courante : `ticket-044-agent-sdk-migration`. Aucun commit sur `main`.
- Toutes les commandes s'exécutent depuis `backend/` avec `uv run`.
- `allowed_tools` doit toujours être explicite : `["Read", "Write", "Edit", "Bash", "Glob", "Grep"]`. `permission_mode` seul ne suffit pas (établi au spike).
- Tout `cwd` passé au SDK doit être résolu via `Path.resolve()` — un chemin court Windows 8.3 fait refuser les écritures (établi au spike).
- Modèle par défaut : `claude-sonnet-4-6`. Ne pas basculer sur Opus sans demande explicite.

## File Structure

| Fichier | Responsabilité |
|---|---|
| `src/vibe_ide/services/providers/__init__.py` (créer) | Fabrique `get_provider()` et ré-exports |
| `src/vibe_ide/services/providers/base.py` (créer) | Protocole `LLMProvider`, dataclass `ProviderResult`, alias de callbacks |
| `src/vibe_ide/services/providers/anthropic_api.py` (créer) | `AnthropicApiProvider` — code extrait d'`AgentRunner` |
| `src/vibe_ide/services/providers/agent_sdk.py` (créer) | `ClaudeAgentSDKProvider` — enveloppe `query()` |
| `src/vibe_ide/services/agent_runner.py` (modifier) | Délègue au provider ; perd la connaissance d'`AsyncAnthropic` |
| `src/vibe_ide/config.py` (modifier) | `anthropic_api_key` optionnel, ajout de `llm_provider` |
| `src/vibe_ide/routers/{agents,orchestrator,projects}.py` (modifier) | Construisent un provider au lieu d'un client |
| `tests/test_providers_base.py` (créer) | `ProviderResult`, `FakeProvider` |
| `tests/test_provider_anthropic_api.py` (créer) | Parité du provider API |
| `tests/test_provider_agent_sdk.py` (créer) | Mapping options / usage / streaming |
| `tests/test_agent_runner.py` (modifier) | Bascule des mocks `AsyncAnthropic` vers `FakeProvider` |

---

### Task 1: Débloquer le démarrage sans clé API

Le backend refuse aujourd'hui de booter sans `ANTHROPIC_API_KEY` (`config.py:9`, champ obligatoire). C'est la situation actuelle de l'utilisateur. Rien d'autre n'est testable tant que ce n'est pas corrigé.

**Files:**
- Modify: `backend/src/vibe_ide/config.py:9`
- Test: `backend/tests/test_config.py` (créer)

**Interfaces:**
- Consumes: rien.
- Produces: `Settings.anthropic_api_key: str = ""`, `Settings.llm_provider: str = "agent_sdk"`.

- [ ] **Step 1: Write the failing test**

Créer `backend/tests/test_config.py` :

```python
import pytest

from vibe_ide.config import Settings


def test_settings_boot_sans_cle_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le backend doit démarrer sans ANTHROPIC_API_KEY (usage abonnement)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert Settings(_env_file=None).anthropic_api_key == ""


def test_settings_provider_par_defaut() -> None:
    assert Settings(_env_file=None).llm_provider == "agent_sdk"
```

`_env_file=None` neutralise la lecture du `.env` ; c'est ce qui rend le test
indépendant de la machine. Inutile de recharger le module.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ValidationError: anthropic_api_key Field required` sur le premier test, `AttributeError`/`ValidationError` sur le second.

- [ ] **Step 3: Write minimal implementation**

Dans `backend/src/vibe_ide/config.py`, remplacer la ligne `anthropic_api_key: str` et ajouter le champ provider :

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Optionnel : vide lorsque le provider est `agent_sdk` (auth par abonnement).
    anthropic_api_key: str = ""
    # Provider LLM par défaut : "agent_sdk" (abonnement) ou "anthropic_api" (crédits).
    llm_provider: str = "agent_sdk"
    ide_workspace_dir: Path = Path.home() / "vibe-ide-workspace"
```

Le reste de la classe est inchangé.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS, 2 passed.

- [ ] **Step 5: Verify no regression**

Run: `uv run pytest -q`
Expected: la suite complète passe (aucun test ne dépendait du caractère obligatoire du champ).

- [ ] **Step 6: Commit**

```bash
git add backend/src/vibe_ide/config.py backend/tests/test_config.py
git commit -m "fix: make anthropic_api_key optional and add llm_provider setting"
```

---

### Task 2: Protocole `LLMProvider` et `ProviderResult`

Le contrat commun aux deux providers. Aucun appel réseau ici — uniquement des types et un double de test réutilisé par toutes les tâches suivantes.

**Files:**
- Create: `backend/src/vibe_ide/services/providers/__init__.py`
- Create: `backend/src/vibe_ide/services/providers/base.py`
- Test: `backend/tests/test_providers_base.py`

**Interfaces:**
- Consumes: rien.
- Produces :
  - `ProviderResult(content: str, input_tokens: int = 0, output_tokens: int = 0, cache_read_tokens: int = 0, cache_creation_tokens: int = 0, cost_usd: float | None = None, provider_name: str = "")`
  - `LLMProvider` — protocole à attribut `name: str` et deux coroutines :
    `complete(*, system, user, model, max_tokens, cwd=None) -> ProviderResult`
    `stream(*, system, user, model, max_tokens, cwd=None, on_token=None, on_tool_use=None) -> ProviderResult`
  - `StreamCallback = Callable[[str], Awaitable[None]]`
  - `ToolEventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]`
  - `FakeProvider` (dans le test, pas dans le paquet applicatif).

- [ ] **Step 1: Write the failing test**

Créer `backend/tests/test_providers_base.py` :

```python
from pathlib import Path
from typing import Any

import pytest

from vibe_ide.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)


class FakeProvider:
    """Double de test implémentant LLMProvider. Enregistre les appels reçus."""

    name = "fake"

    def __init__(self, content: str = "réponse", tokens: int = 10) -> None:
        self._content = content
        self._tokens = tokens
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        self.calls.append(
            {"mode": "complete", "system": system, "user": user,
             "model": model, "max_tokens": max_tokens, "cwd": cwd}
        )
        return ProviderResult(
            content=self._content,
            input_tokens=self._tokens,
            output_tokens=self._tokens,
            provider_name=self.name,
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
    ) -> ProviderResult:
        self.calls.append(
            {"mode": "stream", "system": system, "user": user,
             "model": model, "max_tokens": max_tokens, "cwd": cwd}
        )
        if on_token is not None:
            for chunk in self._content.split(" "):
                await on_token(chunk + " ")
        return ProviderResult(
            content=self._content,
            input_tokens=self._tokens,
            output_tokens=self._tokens,
            provider_name=self.name,
        )


def test_provider_result_defauts() -> None:
    result = ProviderResult(content="abc")
    assert result.content == "abc"
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.cache_read_tokens == 0
    assert result.cache_creation_tokens == 0
    assert result.cost_usd is None
    assert result.provider_name == ""


def test_fake_provider_satisfait_le_protocole() -> None:
    provider: LLMProvider = FakeProvider()
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_complete_renvoie_un_provider_result() -> None:
    provider = FakeProvider(content="bonjour")
    result = await provider.complete(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=100
    )
    assert result.content == "bonjour"
    assert result.provider_name == "fake"


@pytest.mark.asyncio
async def test_stream_appelle_on_token() -> None:
    provider = FakeProvider(content="un deux trois")
    recus: list[str] = []

    async def on_token(chunk: str) -> None:
        recus.append(chunk)

    result = await provider.stream(
        system="sys", user="usr", model="claude-sonnet-4-6",
        max_tokens=100, on_token=on_token,
    )
    assert "".join(recus).strip() == "un deux trois"
    assert result.content == "un deux trois"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_providers_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vibe_ide.services.providers'`.

- [ ] **Step 3: Write minimal implementation**

Créer `backend/src/vibe_ide/services/providers/__init__.py` :

```python
from vibe_ide.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)

__all__ = ["LLMProvider", "ProviderResult", "StreamCallback", "ToolEventCallback"]
```

Créer `backend/src/vibe_ide/services/providers/base.py` :

```python
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

StreamCallback = Callable[[str], Awaitable[None]]
ToolEventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class ProviderResult:
    """Normalized outcome of a single LLM call, whatever the backing provider."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    # Renseigné par les providers qui rapportent eux-mêmes leur coût (SDK).
    # Laissé à None par ceux dont le coût se calcule à partir des tokens.
    cost_usd: float | None = None
    provider_name: str = ""


@runtime_checkable
class LLMProvider(Protocol):
    """Contract every LLM backend must satisfy to be used by AgentRunner."""

    name: str

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        """Runs a single call and returns the full response."""
        ...

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
    ) -> ProviderResult:
        """Runs a single call, forwarding incremental output to the callbacks."""
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_providers_base.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/services/providers/ backend/tests/test_providers_base.py
git commit -m "feat: add LLMProvider protocol and ProviderResult"
```

---

### Task 3: `AnthropicApiProvider`

Déplacement du code existant d'`AgentRunner._complete` / `_stream`. Aucun changement de comportement — c'est le point de reprise sûr.

**Files:**
- Create: `backend/src/vibe_ide/services/providers/anthropic_api.py`
- Test: `backend/tests/test_provider_anthropic_api.py`

**Interfaces:**
- Consumes: `ProviderResult`, `StreamCallback`, `ToolEventCallback` (Task 2).
- Produces: `AnthropicApiProvider(client: AsyncAnthropic)` avec `name = "anthropic_api"`. Ignore `cwd` et `on_tool_use` (l'API n'a pas d'outils ici). Laisse `cost_usd` à `None` — le calcul reste à la charge d'`AgentRunner`.

- [ ] **Step 1: Write the failing test**

Créer `backend/tests/test_provider_anthropic_api.py` :

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.services.providers.anthropic_api import AnthropicApiProvider


def _mock_client(text: str = "réponse") -> MagicMock:
    mock = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage = MagicMock(
        input_tokens=120,
        output_tokens=80,
        cache_creation_input_tokens=30,
        cache_read_input_tokens=10,
    )
    mock.messages.create = AsyncMock(return_value=resp)
    return mock


def test_nom_du_provider() -> None:
    assert AnthropicApiProvider(_mock_client()).name == "anthropic_api"


@pytest.mark.asyncio
async def test_complete_renvoie_contenu_et_tokens() -> None:
    provider = AnthropicApiProvider(_mock_client("bonjour"))
    result = await provider.complete(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    assert result.content == "bonjour"
    assert result.input_tokens == 120
    assert result.output_tokens == 80
    assert result.cache_read_tokens == 10
    assert result.cache_creation_tokens == 30
    assert result.cost_usd is None
    assert result.provider_name == "anthropic_api"


@pytest.mark.asyncio
async def test_complete_passe_le_cache_control_sur_le_system() -> None:
    client = _mock_client()
    provider = AnthropicApiProvider(client)
    await provider.complete(
        system="mon prompt", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 1000
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["system"][0]["text"] == "mon prompt"
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]


@pytest.mark.asyncio
async def test_complete_ignore_les_blocs_sans_texte() -> None:
    client = _mock_client()
    bloc_sans_texte = MagicMock(spec=[])
    client.messages.create.return_value.content = [
        bloc_sans_texte,
        MagicMock(text="visible"),
    ]
    provider = AnthropicApiProvider(client)
    result = await provider.complete(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    assert result.content == "visible"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_provider_anthropic_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vibe_ide.services.providers.anthropic_api'`.

- [ ] **Step 3: Write minimal implementation**

Créer `backend/src/vibe_ide/services/providers/anthropic_api.py` :

```python
from pathlib import Path

from anthropic import AsyncAnthropic

from vibe_ide.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)


def _system_blocks(system: str) -> list[dict[str, object]]:
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def _result_from(content: str, usage: object) -> ProviderResult:
    return ProviderResult(
        content=content,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        provider_name=AnthropicApiProvider.name,
    )


class AnthropicApiProvider:
    """Messages API backend. Billed against prepaid API credits, no file tools."""

    name = "anthropic_api"

    def __init__(self, client: AsyncAnthropic) -> None:
        self._client = client

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
        )
        content = "".join(b.text for b in response.content if hasattr(b, "text"))
        return _result_from(content, response.usage)

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
    ) -> ProviderResult:
        chunks: list[str] = []
        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                if on_token is not None:
                    await on_token(text)
            message = await stream.get_final_message()
        return _result_from("".join(chunks), message.usage)
```

Note pour l'implémenteur : `cwd` et `on_tool_use` sont acceptés puis ignorés — l'API Messages n'expose pas d'outils dans ce chemin. Les garder dans la signature est ce qui permet à `AgentRunner` de traiter les deux providers identiquement.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_provider_anthropic_api.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/services/providers/anthropic_api.py backend/tests/test_provider_anthropic_api.py
git commit -m "feat: extract Messages API calls into AnthropicApiProvider"
```

---

### Task 4: `AgentRunner` délègue au provider

`AgentRunner` cesse de connaître `AsyncAnthropic`. Sa signature publique (`run()`, `AgentResult`) ne bouge pas, donc l'orchestrateur et ses tests restent valides.

**Files:**
- Modify: `backend/src/vibe_ide/services/agent_runner.py:6`, `:40-50`, `:65-76`, `:136-173`
- Modify: `backend/tests/test_agent_runner.py:31-48`, et les tests qui mockent `AsyncAnthropic`

**Interfaces:**
- Consumes: `LLMProvider`, `ProviderResult` (Task 2) ; `AnthropicApiProvider` (Task 3).
- Produces: `AgentRunner(provider: LLMProvider, registry: AgentRegistryService, db_path=None, project_path: Path | None = None)`. `run()` garde sa signature actuelle et renvoie toujours `AgentResult`.

- [ ] **Step 1: Write the failing test**

Dans `backend/tests/test_agent_runner.py`, remplacer les helpers `_mock_complete_client` et `_runner` (lignes 31 à 48) par :

```python
from tests.test_providers_base import FakeProvider


def _runner(
    tmp_path: Path,
    provider: FakeProvider | None = None,
    project_path: Path | None = None,
) -> AgentRunner:
    registry = AgentRegistryService(tmp_path / "prompts")
    return AgentRunner(
        provider or FakeProvider(),
        registry,
        project_path=project_path,
    )
```

Puis ajouter ces tests à la fin du fichier :

```python
@pytest.mark.asyncio
async def test_run_delegue_au_provider(tmp_path: Path) -> None:
    provider = FakeProvider(content="## Statut suggéré\nIN_REVIEW")
    runner = _runner(tmp_path, provider)
    result = await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="contexte",
    )
    assert len(provider.calls) == 1
    assert provider.calls[0]["mode"] == "complete"
    assert result.content == "## Statut suggéré\nIN_REVIEW"
    assert result.suggested_status == TicketStatus.in_review


@pytest.mark.asyncio
async def test_run_utilise_le_modele_de_l_agent_config(tmp_path: Path) -> None:
    provider = FakeProvider()
    runner = _runner(tmp_path, provider)
    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="contexte",
        agent_config=AgentConfig(
            role="codeur", model="claude-opus-4-8", max_tokens=4096,
            prompt_file="codeur.md",
        ),
    )
    assert provider.calls[0]["model"] == "claude-opus-4-8"
    assert provider.calls[0]["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_run_transmet_le_project_path_en_cwd(tmp_path: Path) -> None:
    provider = FakeProvider()
    projet = tmp_path / "mon-projet"
    projet.mkdir()
    runner = _runner(tmp_path, provider, project_path=projet)
    await runner.run(
        role=AgentRole.codeur, ticket=_make_ticket(), project_context="ctx"
    )
    assert provider.calls[0]["cwd"] == projet.resolve()


@pytest.mark.asyncio
async def test_run_en_streaming_utilise_stream(tmp_path: Path) -> None:
    provider = FakeProvider(content="un deux")
    runner = _runner(tmp_path, provider)
    recus: list[str] = []

    async def cb(token: str) -> None:
        recus.append(token)

    result = await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
        stream_callback=cb,
    )
    assert provider.calls[0]["mode"] == "stream"
    assert "".join(recus).strip() == "un deux"
    assert result.content == "un deux"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent_runner.py -v`
Expected: FAIL — `TypeError` sur `AgentRunner(...)` (paramètre `project_path` inconnu) et `AttributeError` sur `provider.calls`.

- [ ] **Step 3: Write minimal implementation**

Dans `backend/src/vibe_ide/services/agent_runner.py`, remplacer l'import ligne 6 :

```python
from vibe_ide.services.providers.base import LLMProvider, ProviderResult
```

Remplacer le constructeur (lignes 40 à 50) :

```python
class AgentRunner:
    def __init__(
        self,
        provider: LLMProvider,
        registry: AgentRegistryService,
        db_path: Path | str | None = None,
        project_path: Path | None = None,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._db_path = db_path
        self._project_path = project_path
```

Remplacer le bloc d'appel (lignes 65 à 81), qui choisissait entre `_stream` et `_complete` :

```python
        model = agent_config.model if agent_config else _DEFAULT_MODEL
        max_tokens = agent_config.max_tokens if agent_config else _DEFAULT_MAX_TOKENS
        # Chemin long obligatoire : un chemin court Windows fait refuser les
        # écritures côté SDK (cf. spike ticket-044).
        cwd = self._project_path.resolve() if self._project_path else None

        if stream_callback is not None:
            provider_result = await self._provider.stream(
                system=system_prompt,
                user=user_prompt,
                model=model,
                max_tokens=max_tokens,
                cwd=cwd,
                on_token=stream_callback,
            )
        else:
            provider_result = await self._provider.complete(
                system=system_prompt,
                user=user_prompt,
                model=model,
                max_tokens=max_tokens,
                cwd=cwd,
            )

        content = provider_result.content
        duration_ms = int((time.monotonic() - t0) * 1000)

        input_tokens = provider_result.input_tokens
        output_tokens = provider_result.output_tokens
        cache_read_tokens = provider_result.cache_read_tokens
```

Dans le bloc de persistance, utiliser le coût rapporté par le provider quand il existe :

```python
        if run_id and self._db_path:
            cost_usd = (
                provider_result.cost_usd
                if provider_result.cost_usd is not None
                else calculate_cost(model, input_tokens, output_tokens, cache_read_tokens)
            )
```

Supprimer entièrement les méthodes `_complete` (lignes 136-150) et `_stream` (lignes 152-173) : leur contenu vit désormais dans `AnthropicApiProvider`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agent_runner.py -v`
Expected: PASS. Les tests d'intégration marqués `integration` restent ignorés.

- [ ] **Step 5: Update the call sites**

Trois routers construisent aujourd'hui `AsyncAnthropic` puis `AgentRunner`. Les repérer :

Run: `grep -rn "AsyncAnthropic(" src/vibe_ide/routers/`
Expected: `agents.py:33`, `agents.py:39`, `agents.py:44`, `orchestrator.py:44`, `projects.py`.

À chaque emplacement, remplacer la construction du client par celle du provider :

```python
from vibe_ide.services.providers.anthropic_api import AnthropicApiProvider

provider = AnthropicApiProvider(AsyncAnthropic(api_key=settings.anthropic_api_key))
runner = AgentRunner(provider, registry, db_path=settings.ide_db_path)
```

**Ce câblage est intentionnellement transitoire.** La fabrique de la Task 7 le
remplacera. Il existe pour que la suite reste verte entre les deux tâches plutôt
que de laisser le dépôt cassé sur trois commits — ce n'est pas du code mort à
signaler en review, c'est le prix d'un point de reprise sûr.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: toute la suite passe.

- [ ] **Step 7: Commit**

```bash
git add backend/src/vibe_ide/services/agent_runner.py backend/src/vibe_ide/routers/ backend/tests/test_agent_runner.py
git commit -m "refactor: make AgentRunner depend on LLMProvider instead of AsyncAnthropic"
```

---

### Task 5: `ClaudeAgentSDKProvider` — appel non-streamé

Première implémentation SDK. Les options sont testées par introspection plutôt qu'en appelant le réseau ; l'appel réel est couvert par le test d'intégration de la Task 8.

**Files:**
- Create: `backend/src/vibe_ide/services/providers/agent_sdk.py`
- Test: `backend/tests/test_provider_agent_sdk.py`

**Interfaces:**
- Consumes: `ProviderResult`, `StreamCallback`, `ToolEventCallback` (Task 2).
- Produces:
  - `ClaudeAgentSDKProvider(max_turns: int = 30, max_budget_usd: float | None = None)` avec `name = "agent_sdk"`.
  - `ClaudeAgentSDKProvider.ALLOWED_TOOLS: list[str]`
  - `_build_options(*, system: str, model: str, max_turns: int, max_budget_usd: float | None, cwd: Path | None) -> ClaudeAgentOptions` (module-level, keyword-only)
  - `_usage_from(result) -> tuple[int, int, int, int]` renvoyant `(input, output, cache_read, cache_creation)` (module-level)

- [ ] **Step 1: Write the failing test**

Créer `backend/tests/test_provider_agent_sdk.py` :

```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibe_ide.services.providers.agent_sdk import (
    ClaudeAgentSDKProvider,
    _build_options,
    _usage_from,
)


def test_nom_du_provider() -> None:
    assert ClaudeAgentSDKProvider().name == "agent_sdk"


def test_allowed_tools_est_explicite() -> None:
    # permission_mode seul ne suffit pas : sans allowed_tools les écritures
    # sont refusées (constat du spike ticket-044).
    assert ClaudeAgentSDKProvider.ALLOWED_TOOLS == [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep"
    ]


def test_build_options_resout_le_cwd_en_chemin_long(tmp_path: Path) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    options = _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=projet,
    )
    assert options.cwd == str(projet.resolve())


def test_build_options_sans_cwd(tmp_path: Path) -> None:
    options = _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=None,
    )
    assert options.cwd is None


def test_build_options_porte_les_garde_fous() -> None:
    options = _build_options(
        system="mon prompt", model="claude-sonnet-4-6", max_turns=12,
        max_budget_usd=1.5, cwd=None,
    )
    assert options.system_prompt == "mon prompt"
    assert options.model == "claude-sonnet-4-6"
    assert options.max_turns == 12
    assert options.max_budget_usd == 1.5
    assert options.permission_mode == "acceptEdits"
    assert options.allowed_tools == ClaudeAgentSDKProvider.ALLOWED_TOOLS
    assert options.setting_sources == ["project"]
    assert options.include_partial_messages is True


def test_usage_from_extrait_les_quatre_compteurs() -> None:
    result = MagicMock()
    result.usage = {
        "input_tokens": 10,
        "output_tokens": 801,
        "cache_read_input_tokens": 109258,
        "cache_creation_input_tokens": 10313,
    }
    assert _usage_from(result) == (10, 801, 109258, 10313)


def test_usage_from_tolere_un_usage_absent() -> None:
    result = MagicMock()
    result.usage = None
    assert _usage_from(result) == (0, 0, 0, 0)


def test_usage_from_tolere_des_champs_manquants() -> None:
    result = MagicMock()
    result.usage = {"input_tokens": 5}
    assert _usage_from(result) == (5, 0, 0, 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_provider_agent_sdk.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vibe_ide.services.providers.agent_sdk'`.

- [ ] **Step 3: Write minimal implementation**

Créer `backend/src/vibe_ide/services/providers/agent_sdk.py` :

```python
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

from vibe_ide.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)

_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]


def _build_options(
    *,
    system: str,
    model: str,
    max_turns: int,
    max_budget_usd: float | None,
    cwd: Path | None,
) -> ClaudeAgentOptions:
    """Builds SDK options with the guardrails established by the ticket-044 spike."""
    return ClaudeAgentOptions(
        # Chemin long obligatoire : un chemin court Windows 8.3 fait refuser
        # les écritures.
        cwd=str(cwd.resolve()) if cwd is not None else None,
        system_prompt=system,
        model=model,
        # permission_mode seul ne suffit pas — allowed_tools doit être explicite.
        permission_mode="acceptEdits",
        allowed_tools=_ALLOWED_TOOLS,
        setting_sources=["project"],
        include_partial_messages=True,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
    )


def _usage_from(result: Any) -> tuple[int, int, int, int]:
    """Extracts (input, output, cache_read, cache_creation) from a ResultMessage."""
    usage = getattr(result, "usage", None) or {}
    return (
        int(usage.get("input_tokens", 0) or 0),
        int(usage.get("output_tokens", 0) or 0),
        int(usage.get("cache_read_input_tokens", 0) or 0),
        int(usage.get("cache_creation_input_tokens", 0) or 0),
    )


class ClaudeAgentSDKProvider:
    """Claude Agent SDK backend: real file tools, billed against the subscription."""

    name = "agent_sdk"
    ALLOWED_TOOLS = _ALLOWED_TOOLS

    def __init__(
        self,
        max_turns: int = 30,
        max_budget_usd: float | None = None,
    ) -> None:
        self._max_turns = max_turns
        self._max_budget_usd = max_budget_usd

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        return await self._run(system=system, user=user, model=model, cwd=cwd)

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
    ) -> ProviderResult:
        return await self._run(
            system=system, user=user, model=model, cwd=cwd,
            on_token=on_token, on_tool_use=on_tool_use,
        )

    async def _run(
        self,
        *,
        system: str,
        user: str,
        model: str,
        cwd: Path | None,
        on_token: StreamCallback | None = None,
        on_tool_use: ToolEventCallback | None = None,
    ) -> ProviderResult:
        options = _build_options(
            system=system, model=model, max_turns=self._max_turns,
            max_budget_usd=self._max_budget_usd, cwd=cwd,
        )
        chunks: list[str] = []
        result: ResultMessage | None = None

        async for message in query(prompt=user, options=options):
            if isinstance(message, ResultMessage):
                result = message
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    kind = type(block).__name__
                    if kind == "TextBlock":
                        chunks.append(block.text)
                        if on_token is not None:
                            await on_token(block.text)
                    elif kind == "ToolUseBlock" and on_tool_use is not None:
                        await on_tool_use(block.name, dict(block.input))

        if result is None:
            raise RuntimeError("Agent SDK: aucun ResultMessage reçu")

        inp, out, cache_read, cache_creation = _usage_from(result)
        return ProviderResult(
            content="".join(chunks),
            input_tokens=inp,
            output_tokens=out,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            cost_usd=result.total_cost_usd,
            provider_name=self.name,
        )
```

Note pour l'implémenteur : `max_tokens` est accepté mais non transmis — le SDK borne l'exécution par `max_turns` et `max_budget_usd`, pas par un plafond de tokens de sortie. Le paramètre reste dans la signature pour respecter le protocole.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_provider_agent_sdk.py -v`
Expected: PASS, 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/services/providers/agent_sdk.py backend/tests/test_provider_agent_sdk.py
git commit -m "feat: add ClaudeAgentSDKProvider with file tools and spike guardrails"
```

---

### Task 6: Remonter les appels d'outils jusqu'à l'UI

Un nouvel event `AGENT_TOOL_USE` permet au panneau d'agent d'afficher « écriture de `src/foo.py` » au lieu d'un mur de Markdown.

**Files:**
- Modify: `backend/src/vibe_ide/services/orchestrator.py:31-42` (enum `EventType`), `:170-187` (bloc codeur)
- Modify: `backend/src/vibe_ide/services/agent_runner.py` (signature de `run()`)
- Test: `backend/tests/test_agent_runner.py`

**Interfaces:**
- Consumes: `ToolEventCallback` (Task 2), `ClaudeAgentSDKProvider` (Task 5).
- Produces: `EventType.AGENT_TOOL_USE = "agent_tool_use"` ; `AgentRunner.run()` accepte `tool_callback: ToolEventCallback | None = None`.

- [ ] **Step 1: Write the failing test**

Ajouter à `backend/tests/test_agent_runner.py` :

```python
@pytest.mark.asyncio
async def test_run_transmet_le_tool_callback_au_provider(tmp_path: Path) -> None:
    class ToolProvider(FakeProvider):
        async def stream(self, **kwargs: object) -> object:
            on_tool_use = kwargs.get("on_tool_use")
            if on_tool_use is not None:
                await on_tool_use("Write", {"file_path": "src/foo.py"})
            return await super().stream(**kwargs)  # type: ignore[arg-type]

    provider = ToolProvider(content="fait")
    runner = _runner(tmp_path, provider)
    outils: list[tuple[str, dict]] = []

    async def on_tool(name: str, payload: dict) -> None:
        outils.append((name, payload))

    async def on_token(_: str) -> None:
        return None

    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
        stream_callback=on_token,
        tool_callback=on_tool,
    )
    assert outils == [("Write", {"file_path": "src/foo.py"})]
```

Ajouter à `backend/tests/test_orchestrator.py` :

```python
def test_agent_tool_use_event_existe() -> None:
    from vibe_ide.services.orchestrator import EventType

    assert EventType.AGENT_TOOL_USE.value == "agent_tool_use"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent_runner.py::test_run_transmet_le_tool_callback_au_provider tests/test_orchestrator.py::test_agent_tool_use_event_existe -v`
Expected: FAIL — `TypeError: run() got an unexpected keyword argument 'tool_callback'` et `AttributeError: AGENT_TOOL_USE`.

- [ ] **Step 3: Write minimal implementation**

Dans `backend/src/vibe_ide/services/orchestrator.py`, ajouter le membre à l'enum `EventType`, après `AGENT_TOKEN` :

```python
    AGENT_TOOL_USE = "agent_tool_use"
```

Dans `backend/src/vibe_ide/services/agent_runner.py`, ajouter le paramètre à `run()` après `stream_callback` :

```python
        tool_callback: ToolEventCallback | None = None,
```

et le transmettre dans l'appel `stream` :

```python
            provider_result = await self._provider.stream(
                system=system_prompt,
                user=user_prompt,
                model=model,
                max_tokens=max_tokens,
                cwd=cwd,
                on_token=stream_callback,
                on_tool_use=tool_callback,
            )
```

Compléter l'import :

```python
from vibe_ide.services.providers.base import (
    LLMProvider,
    ProviderResult,
    ToolEventCallback,
)
```

Dans `orchestrator.py`, à côté de `_emit_token` (ligne 170), ajouter l'émetteur d'outils et le passer au runner :

```python
            async def _emit_tool(name: str, payload: dict, tid: str = ticket_id) -> None:
                await on_event(
                    OrchestratorEvent(
                        type=EventType.AGENT_TOOL_USE,
                        agent=AgentRole.codeur,
                        ticket_id=tid,
                        data={"tool": name, "input": payload},
                    )
                )

            codeur_result = await self._runner.run(
                role=AgentRole.codeur,
                ticket=ticket,
                project_context=context,
                agent_config=codeur_cfg,
                stream_callback=_emit_token,
                tool_callback=_emit_tool,
                run_id=run_id,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agent_runner.py tests/test_orchestrator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/services/agent_runner.py backend/src/vibe_ide/services/orchestrator.py backend/tests/
git commit -m "feat: surface agent tool calls as AGENT_TOOL_USE events"
```

---

### Task 7: Fabrique `get_provider` et câblage

Un seul point de construction, piloté par `Settings.llm_provider`.

**Files:**
- Modify: `backend/src/vibe_ide/services/providers/__init__.py`
- Modify: `backend/src/vibe_ide/routers/agents.py:33,39,44`, `orchestrator.py:44`, `projects.py`
- Test: `backend/tests/test_providers_factory.py` (créer)

**Interfaces:**
- Consumes: `AnthropicApiProvider` (Task 3), `ClaudeAgentSDKProvider` (Task 5).
- Produces: `get_provider(name: str | None = None, api_key: str = "") -> LLMProvider`.

- [ ] **Step 1: Write the failing test**

Créer `backend/tests/test_providers_factory.py` :

```python
import pytest

from vibe_ide.services.providers import get_provider
from vibe_ide.services.providers.agent_sdk import ClaudeAgentSDKProvider
from vibe_ide.services.providers.anthropic_api import AnthropicApiProvider


def test_get_provider_agent_sdk() -> None:
    assert isinstance(get_provider("agent_sdk"), ClaudeAgentSDKProvider)


def test_get_provider_anthropic_api() -> None:
    provider = get_provider("anthropic_api", api_key="sk-test")
    assert isinstance(provider, AnthropicApiProvider)


def test_get_provider_api_sans_cle_est_une_erreur_explicite() -> None:
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_provider("anthropic_api", api_key="")


def test_get_provider_inconnu_est_une_erreur_explicite() -> None:
    with pytest.raises(ValueError, match="inconnu"):
        get_provider("gpt5")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_providers_factory.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_provider'`.

- [ ] **Step 3: Write minimal implementation**

Remplacer `backend/src/vibe_ide/services/providers/__init__.py` :

```python
from anthropic import AsyncAnthropic

from vibe_ide.services.providers.agent_sdk import ClaudeAgentSDKProvider
from vibe_ide.services.providers.anthropic_api import AnthropicApiProvider
from vibe_ide.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)

__all__ = [
    "AnthropicApiProvider",
    "ClaudeAgentSDKProvider",
    "LLMProvider",
    "ProviderResult",
    "StreamCallback",
    "ToolEventCallback",
    "get_provider",
]


def get_provider(name: str | None = None, api_key: str = "") -> LLMProvider:
    """Builds the configured LLM provider. Defaults to the subscription-backed SDK."""
    resolved = name or "agent_sdk"
    if resolved == "agent_sdk":
        return ClaudeAgentSDKProvider()
    if resolved == "anthropic_api":
        if not api_key:
            raise ValueError(
                "Le provider 'anthropic_api' exige une ANTHROPIC_API_KEY. "
                "Renseignez-la dans .env, ou laissez llm_provider='agent_sdk' "
                "pour utiliser votre abonnement."
            )
        return AnthropicApiProvider(AsyncAnthropic(api_key=api_key))
    raise ValueError(
        f"Provider LLM inconnu : {resolved!r}. "
        "Valeurs acceptées : 'agent_sdk', 'anthropic_api'."
    )
```

Dans chacun des trois routers, remplacer la construction intermédiaire de la Task 4 :

```python
from vibe_ide.services.providers import get_provider

provider = get_provider(settings.llm_provider, settings.anthropic_api_key)
runner = AgentRunner(provider, registry, db_path=settings.ide_db_path)
```

Supprimer l'import désormais inutile d'`AsyncAnthropic` dans ces fichiers.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_providers_factory.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: toute la suite passe.

Run: `grep -rn "AgentRunner(" src/vibe_ide/routers/`
Expected: chaque construction d'`AgentRunner` reçoit le résultat de `get_provider(...)`, plus aucune un `AnthropicApiProvider` construit à la main.

Note : `AsyncAnthropic` subsiste volontairement dans les routers à ce stade. Sept
services — `agent_creator`, `doc_updater`, `planner`, `project_analyzer`,
`project_creator`, `security_auditor`, `validator` — appellent `messages.create`
sans passer par `AgentRunner` et reçoivent encore un client brut. Les Tasks 9 et
10 les migrent ; c'est seulement à l'issue de la Task 10 que
`grep -rn "AsyncAnthropic" src/vibe_ide/routers/` doit être vide.

- [ ] **Step 6: Commit**

```bash
git add backend/src/vibe_ide/services/providers/__init__.py backend/src/vibe_ide/routers/ backend/tests/test_providers_factory.py
git commit -m "feat: add get_provider factory and wire routers through it"
```

---

### Task 8: Test d'intégration bout en bout

Vérifie sur une vraie session ce que les tests unitaires ne peuvent pas : que l'agent écrit réellement un fichier, avec l'authentification par abonnement. Marqué `integration`, donc exclu de la CI comme les tests existants.

**Files:**
- Test: `backend/tests/test_provider_agent_sdk_integration.py` (créer)

**Interfaces:**
- Consumes: `ClaudeAgentSDKProvider` (Task 5).
- Produces: rien.

- [ ] **Step 1: Write the test**

Créer `backend/tests/test_provider_agent_sdk_integration.py` :

```python
import shutil
from pathlib import Path

import pytest

from vibe_ide.services.providers.agent_sdk import ClaudeAgentSDKProvider

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_agent_ecrit_un_fichier_reel(tmp_path: Path) -> None:
    """Nécessite une session Claude Code authentifiée (`claude` en PATH)."""
    if shutil.which("claude") is None:
        pytest.skip("CLI Claude Code absent du PATH")

    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text(
        "Tout fichier Python commence par le commentaire `# vibe-ide`.\n",
        encoding="utf-8",
    )

    provider = ClaudeAgentSDKProvider(max_turns=8, max_budget_usd=1.0)
    outils: list[str] = []

    async def on_tool(name: str, _: dict) -> None:
        outils.append(name)

    result = await provider.stream(
        system="Tu es un agent de test. Sois bref.",
        user="Crée hello.py avec une fonction hello() retournant 'bonjour'. "
        "Respecte les conventions du projet.",
        model="claude-sonnet-4-6",
        max_tokens=4096,
        cwd=projet,
        on_tool_use=on_tool,
    )

    cree = projet / "hello.py"
    assert cree.exists(), f"fichier non écrit ; outils appelés : {outils}"
    assert cree.read_text(encoding="utf-8").startswith("# vibe-ide")
    assert "Write" in outils
    assert result.output_tokens > 0
    assert result.cost_usd is not None
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/test_provider_agent_sdk_integration.py -v -m integration`
Expected: PASS. Durée attendue : 30 à 90 secondes. En cas d'échec sur l'écriture, vérifier d'abord que `cwd` est bien un chemin long résolu.

- [ ] **Step 3: Verify it is excluded from the default run**

Run: `uv run pytest -q`
Expected: le test apparaît en `deselected` ou `skipped`, jamais exécuté par défaut.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_provider_agent_sdk_integration.py
git commit -m "test: add end-to-end integration test for the Agent SDK provider"
```

---

### Task 9: Migrer les services du pipeline vers le provider

Quatre services appellent `messages.create` en direct sans passer par
`AgentRunner`, et exigeraient donc encore des crédits API après la Task 8. Ils
partagent tous la même forme : `__init__(self, client: AsyncAnthropic, ...)` puis
`await self._client.messages.create(...)`.

**Files:**
- Modify: `backend/src/vibe_ide/services/doc_updater.py`
- Modify: `backend/src/vibe_ide/services/security_auditor.py`
- Modify: `backend/src/vibe_ide/services/validator.py`
- Modify: `backend/src/vibe_ide/services/planner.py`
- Modify: les tests correspondants dans `backend/tests/`
- Modify: `backend/src/vibe_ide/routers/orchestrator.py`, `projects.py` (sites de construction)

**Interfaces:**
- Consumes: `LLMProvider`, `ProviderResult` (Task 2) ; `get_provider()` (Task 7).
- Produces: chaque service prend `provider: LLMProvider` au lieu de `client: AsyncAnthropic`.

- [ ] **Step 1: Migrer un service en TDD, comme gabarit**

Commencer par `planner.py`, le plus simple. Adapter son test pour injecter un
`FakeProvider` au lieu de mocker `AsyncAnthropic`, le regarder échouer, puis
remplacer dans le service :

```python
from vibe_ide.services.providers.base import LLMProvider


class PlannerService:
    def __init__(self, provider: LLMProvider, prompts_dir: Path, workspace_dir: Path) -> None:
        self._provider = provider
```

et l'appel :

```python
        result = await self._provider.complete(
            system=system_prompt,
            user=user_prompt,
            model=_DEFAULT_MODEL,
            max_tokens=_DEFAULT_MAX_TOKENS,
        )
        content = result.content
```

Le reste du service — chargement du prompt, `extract_json`, construction du
`PlanResult` — est inchangé. `extract_json` continue de fonctionner : le SDK
renvoie de la prose contenant le bloc JSON, exactement comme l'API.

- [ ] **Step 2: Vérifier le gabarit**

Run: `uv run pytest tests/test_planner.py -v`
Expected: PASS.

- [ ] **Step 3: Appliquer le même gabarit aux trois autres**

`doc_updater.py`, `security_auditor.py`, `validator.py` — même substitution,
mêmes adaptations de tests. Ne pas factoriser une classe de base commune : les
services diffèrent par leurs prompts et leurs modèles de retour, et une
abstraction prématurée coûterait plus qu'elle ne rapporte.

- [ ] **Step 4: Recâbler les sites de construction**

Dans `routers/orchestrator.py` et `routers/projects.py`, ces services reçoivent
désormais `get_provider(settings.llm_provider, settings.anthropic_api_key)` au
lieu du client brut.

- [ ] **Step 5: Vérifier**

Run: `uv run pytest -q`
Expected: la suite passe, modulo les 11 échecs environnementaux connus.

- [ ] **Step 6: Commit**

```bash
git add backend/src/vibe_ide/services/ backend/src/vibe_ide/routers/ backend/tests/
git commit -m "refactor: migrate pipeline services to the LLMProvider layer"
```

---

### Task 10: Migrer les services conversationnels vers le provider

Mêmes substitutions pour les trois services restants, qui pilotent des
conversations multi-tours et extraient du JSON de la réponse.

**Files:**
- Modify: `backend/src/vibe_ide/services/agent_creator.py`
- Modify: `backend/src/vibe_ide/services/project_creator.py`
- Modify: `backend/src/vibe_ide/services/project_analyzer.py`
- Modify: les tests correspondants
- Modify: `backend/src/vibe_ide/routers/agents.py`, `projects.py`

**Interfaces:**
- Consumes: `LLMProvider` (Task 2), `get_provider()` (Task 7), le gabarit de la Task 9.
- Produces: plus aucun `AsyncAnthropic` dans `services/` ni `routers/`.

- [ ] **Step 1: Vérifier la forme des conversations multi-tours**

Ces services passent une liste de messages, pas un seul `user`. Le protocole
`LLMProvider` n'expose qu'un `user: str`. Avant de coder, lire les trois
services et déterminer si leur conversation peut être aplatie en une seule
chaîne — c'est le cas si chaque tour est déjà sérialisé en texte. Si un service
exige réellement une liste de messages structurée, **s'arrêter et le signaler**
plutôt que de tordre le protocole : ce serait une modification du contrat de la
Task 2, donc une décision d'architecture.

- [ ] **Step 2: Migrer les trois services en TDD**

Même substitution que la Task 9 : `provider: LLMProvider` au constructeur,
`await self._provider.complete(...)` à l'appel, `extract_json` inchangé.

- [ ] **Step 3: Recâbler et vérifier**

Run: `grep -rn "AsyncAnthropic" src/vibe_ide/services/ src/vibe_ide/routers/`
Expected: aucun résultat hors `providers/anthropic_api.py`.

Run: `uv run pytest -q`
Expected: la suite passe, modulo les 11 échecs environnementaux connus.

- [ ] **Step 4: Commit**

```bash
git add backend/src/vibe_ide/services/ backend/src/vibe_ide/routers/ backend/tests/
git commit -m "refactor: migrate conversational services to the LLMProvider layer"
```

---

## Après ce plan

À l'issue de la Task 8, le pipeline tourne sur l'abonnement et le codeur écrit réellement dans le workspace. Les phases 4 et 5 du spec feront l'objet d'un plan distinct :

- **Phase 4** — branche git par pipeline, reviewer et auditeur sécurité sur diff réel, suppression de l'injection de `project_context` pour les agents SDK.
- **Phase 5** — `QuotaTracker` alimenté par les `RateLimitEvent`, table `quota_events`, endpoint `/api/v1/usage`, mise en pause du mode autonome sur `status == "rejected"`, affichage des events d'outils côté frontend.
