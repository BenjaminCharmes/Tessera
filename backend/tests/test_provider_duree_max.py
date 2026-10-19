"""A total duration per call for the text roles, and a visible fallback — ticket-518.

Les bornes qui existaient — lecture d'Ollama, silence du SDK — se remettent à
zéro à chaque morceau reçu : un flux qui continue d'émettre n'avait pas de
fin, et rien dans le journal du pipeline ne disait qu'un repli avait joué.
"""
import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

import tessera.services.providers.agent_sdk as agent_sdk_module
from tessera.config import settings
from tessera.services.journal_pipeline import journal_vers
from tessera.services.providers import par_role
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.base import ProviderResult
from tessera.services.providers.duree_max import borner
from tessera.services.providers.enregistrant import activer_enregistrement
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.ollama import (
    OllamaProvider,
    _get_slot,
    _reset_cooldowns,
    _reset_slots,
)
from tessera.services.providers.par_role import ROLES_TEXTE, provider_pour_role
from tessera.services.providers.repli import ProviderAvecRepli
from tests.test_providers_base import FakeProvider
from claude_agent_sdk import AssistantMessage, TextBlock

_BASE = "http://duree-max.test:11434"


@pytest.fixture(autouse=True)
def _etat_propre() -> None:
    _reset_cooldowns()
    _reset_slots()


class _FluxSansFin(httpx.AsyncByteStream):
    """A response body that never ends: one chat line every few milliseconds."""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        ligne = {"message": {"role": "assistant", "content": "x"}, "done": False}
        while True:
            yield (json.dumps(ligne) + "\n").encode()
            await asyncio.sleep(0.005)


def _client_qui_emet_sans_fin() -> httpx.AsyncClient:
    def reponse(requete: httpx.Request) -> httpx.Response:
        if requete.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "q"}]})
        return httpx.Response(200, stream=_FluxSansFin())

    return httpx.AsyncClient(base_url=_BASE, transport=httpx.MockTransport(reponse))


# ------------------------------------------------------------------
# La borne elle-même
# ------------------------------------------------------------------


async def test_borner_laisse_passer_un_corps_assez_rapide() -> None:
    async with borner(1.0):
        await asyncio.sleep(0)


@pytest.mark.parametrize("duree", [None, 0.0, -1.0])
async def test_borner_sans_duree_positive_ne_borne_rien(duree: float | None) -> None:
    async with borner(duree):
        await asyncio.sleep(0.02)


async def test_borner_ne_convertit_pas_un_delai_venu_d_ailleurs() -> None:
    with pytest.raises(TimeoutError):
        async with borner(5.0):
            raise TimeoutError("délai d'un autre appel")


# ------------------------------------------------------------------
# Ollama
# ------------------------------------------------------------------


async def test_un_flux_ollama_qui_emet_sans_fin_leve_provider_indisponible() -> None:
    provider = OllamaProvider(_BASE, client=_client_qui_emet_sans_fin(), duree_max_s=0.1)

    with pytest.raises(ProviderIndisponible, match="durée maximale"):
        await provider.stream(system="s", user="u", model="q", max_tokens=10)


async def test_l_attente_d_un_creneau_compte_dans_la_duree_maximale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # L'attente de créneau (5 s) dépasse de loin la durée maximale (0,1 s) :
    # c'est la seconde qui doit couper.
    monkeypatch.setattr(settings, "ollama_max_concurrent", 1)
    monkeypatch.setattr(settings, "ollama_slot_wait_s", 5.0)
    slot = _get_slot(_BASE)
    assert slot is not None
    await slot.acquire()
    provider = OllamaProvider(_BASE, client=_client_qui_emet_sans_fin(), duree_max_s=0.1)

    debut = time.monotonic()
    try:
        with pytest.raises(ProviderIndisponible, match="durée maximale"):
            await provider.stream(system="s", user="u", model="q", max_tokens=10)
    finally:
        slot.release()

    assert time.monotonic() - debut < 2.0


async def test_la_duree_maximale_pose_le_refroidissement_du_serveur() -> None:
    provider = OllamaProvider(_BASE, client=_client_qui_emet_sans_fin(), duree_max_s=0.05)
    with pytest.raises(ProviderIndisponible):
        await provider.stream(system="s", user="u", model="q", max_tokens=10)

    # L'appel suivant est refusé aussitôt, sans requête : le repli prend le relais.
    with pytest.raises(ProviderIndisponible, match="refroidissement"):
        await provider.stream(system="s", user="u", model="q", max_tokens=10)


# ------------------------------------------------------------------
# agent_sdk
# ------------------------------------------------------------------


async def test_un_appel_agent_sdk_qui_emet_sans_fin_leve_provider_indisponible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Un message toutes les 10 ms : le silence maximal (1 s) ne se déclenche
    # jamais, seule la durée totale peut couper.
    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        while True:
            yield AssistantMessage(content=[TextBlock(text="x")], model="m")
            await asyncio.sleep(0.01)

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    provider = ClaudeAgentSDKProvider(silence_max_s=1.0, duree_max_s=0.1)

    with pytest.raises(ProviderIndisponible, match="durée maximale"):
        await provider.complete(system="s", user="u", model="m", max_tokens=10)


# ------------------------------------------------------------------
# La fabrique par rôle
# ------------------------------------------------------------------


@pytest.fixture
def appels_de_fabrique(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> FakeProvider:
        appels.append({"name": name, **kwargs})
        return FakeProvider()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    return appels


def _projet_sans_manifeste(tmp_path: Path) -> Path:
    return tmp_path / "inexistant"


@pytest.mark.parametrize("role", sorted(ROLES_TEXTE))
def test_un_role_texte_recoit_la_duree_maximale(
    role: str, appels_de_fabrique: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "llm_duree_max_role_texte_s", 123.0)

    provider_pour_role(_projet_sans_manifeste(tmp_path), role, allow_tools=False)

    assert appels_de_fabrique[0]["duree_max_s"] == 123.0


@pytest.mark.parametrize("role", ["codeur", "reviewer", "planificateur"])
def test_les_autres_roles_ne_recoivent_aucune_duree_maximale(
    role: str, appels_de_fabrique: list[dict[str, Any]], tmp_path: Path,
) -> None:
    provider_pour_role(_projet_sans_manifeste(tmp_path), role)

    assert appels_de_fabrique[0]["duree_max_s"] is None


def test_la_duree_maximale_se_regle_par_la_variable_d_environnement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_DUREE_MAX_ROLE_TEXTE_S", "42")

    assert type(settings)().llm_duree_max_role_texte_s == 42.0


def test_le_repli_recoit_lui_aussi_la_duree_maximale(
    appels_de_fabrique: list[dict[str, Any]], tmp_path: Path,
) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text("# projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps({"project_id": "projet", "agents": [{
        "role": "validateur", "model": "q", "max_tokens": 100,
        "prompt_file": "agents/prompts/validateur.md", "active": True,
        "provider": "ollama",
        "fallback": {"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    }]}), encoding="utf-8")

    provider_pour_role(projet, "validateur", allow_tools=False)

    assert [a["name"] for a in appels_de_fabrique] == ["ollama", "agent_sdk"]
    assert all(a["duree_max_s"] == settings.llm_duree_max_role_texte_s for a in appels_de_fabrique)


# ------------------------------------------------------------------
# Le repli se voit dans le journal du pipeline
# ------------------------------------------------------------------


class _Indisponible(FakeProvider):
    name = "ollama"

    async def complete(
        self, *, system: str, user: str, model: str, max_tokens: int,
        cwd: Path | None = None, **extra: Any,
    ) -> ProviderResult:
        raise ProviderIndisponible("durée maximale dépassée (900 s)")


async def test_un_passage_au_repli_ecrit_une_ligne_dans_le_journal(tmp_path: Path) -> None:
    journal = tmp_path / "memory" / "pipeline-log.md"
    repli = FakeProvider()
    repli.name = "agent_sdk"  # type: ignore[misc]
    provider = ProviderAvecRepli(
        _Indisponible(), repli, modele_repli="claude-haiku-4-5",
        role="validateur", project_id="p", journal=journal_vers(journal),
    )
    activer_enregistrement(None, "ticket-029")
    try:
        await provider.complete(system="s", user="u", model="qwen", max_tokens=10)
    finally:
        activer_enregistrement(None, None)

    lignes = journal.read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 1
    assert lignes[0].endswith(
        "[ticket-029] validateur: repli vers agent_sdk/claude-haiku-4-5"
        " — durée maximale dépassée (900 s)"
    )


async def test_la_fabrique_par_role_transmet_le_journal_au_repli(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    # Sans ce câblage, `ProviderAvecRepli` serait construit sans journal et
    # le repli resterait silencieux malgré tout ce qui précède.
    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> FakeProvider:
        return _Indisponible() if name == "ollama" else FakeProvider()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text("# projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps({"project_id": "projet", "agents": [{
        "role": "validateur", "model": "q", "max_tokens": 100,
        "prompt_file": "agents/prompts/validateur.md", "active": True,
        "provider": "ollama",
        "fallback": {"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    }]}), encoding="utf-8")
    journal = tmp_path / "pipeline-log.md"

    provider = provider_pour_role(
        projet, "validateur", allow_tools=False, journal_repli=journal_vers(journal),
    )
    assert isinstance(provider, ProviderAvecRepli)
    activer_enregistrement(None, "ticket-029")
    try:
        await provider.complete(system="s", user="u", model="q", max_tokens=10)
    finally:
        activer_enregistrement(None, None)

    assert "[ticket-029] validateur: repli vers " in journal.read_text(encoding="utf-8")


async def test_la_ligne_de_repli_est_ecrite_avant_l_appel_du_repli(tmp_path: Path) -> None:
    # Un repli qui gèle à son tour ne doit pas emporter la trace avec lui.
    journal = tmp_path / "pipeline-log.md"
    vu: list[bool] = []

    class RepliQuiRegarde(FakeProvider):
        async def complete(
            self, *, system: str, user: str, model: str, max_tokens: int,
            cwd: Path | None = None, **extra: Any,
        ) -> ProviderResult:
            vu.append(journal.exists())
            return await super().complete(
                system=system, user=user, model=model, max_tokens=max_tokens, **extra
            )

    provider = ProviderAvecRepli(
        _Indisponible(), RepliQuiRegarde(), modele_repli="m",
        role="securite", project_id="p", journal=journal_vers(journal),
    )
    activer_enregistrement(None, "ticket-001")
    try:
        await provider.complete(system="s", user="u", model="q", max_tokens=10)
    finally:
        activer_enregistrement(None, None)

    assert vu == [True]


async def test_sans_ticket_en_cours_aucune_ligne_n_est_ecrite(tmp_path: Path) -> None:
    journal = tmp_path / "pipeline-log.md"
    provider = ProviderAvecRepli(
        _Indisponible(), FakeProvider(), modele_repli="m",
        role="validateur", project_id="p", journal=journal_vers(journal),
    )

    await provider.complete(system="s", user="u", model="q", max_tokens=10)

    assert not journal.exists()


async def test_un_journal_qui_leve_n_empeche_pas_le_repli() -> None:
    def casse(message: str) -> None:
        raise OSError("disque plein")

    provider = ProviderAvecRepli(
        _Indisponible(), FakeProvider(content="ok"), modele_repli="m",
        role="validateur", project_id="p", journal=casse,
    )
    activer_enregistrement(None, "ticket-001")
    try:
        resultat = await provider.complete(system="s", user="u", model="q", max_tokens=10)
    finally:
        activer_enregistrement(None, None)

    assert resultat.content == "ok"
