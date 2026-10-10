"""An Ollama provider for the tool-less roles — ticket-189.

Sept services ne font qu'un appel texte→JSON : un modèle local les sert à
coût nul. Le repli du ticket-188 est ce qui rend le manifeste portable sur
une machine où Ollama n'est pas là.
"""
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from tessera.config import settings
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType
from tessera.services.providers import get_provider
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.noms import PROVIDERS_CONNUS, ProviderIndisponible
import tessera.services.providers.ollama as ollama_module
from tessera.services.providers.ollama import OllamaProvider, _reset_slots, _reset_cooldowns
from tessera.services.providers import par_role
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.project_loader import load_agents_config
from tests.test_providers_base import FakeProvider

_BASE = "http://ollama.test:11434"


@pytest.fixture(autouse=True)
def _reset_module_state() -> None:
    """Remet l'état module-level à zéro avant chaque test.

    `_COOLDOWNS` est partagé par tout le processus ; un ReadTimeout dans un
    test activerait un cooldown qui ferait échouer les tests suivants sur la
    même base_url.
    """
    _reset_cooldowns()


def _tags(*modeles: str) -> dict[str, Any]:
    return {"models": [{"name": m, "model": m} for m in modeles]}


def _reponse(contenu: str, prompt: int = 120, sortie: int = 40) -> dict[str, Any]:
    return {
        "model": "qwen3-coder:30b",
        "message": {"role": "assistant", "content": contenu},
        "done": True,
        "prompt_eval_count": prompt,
        "eval_count": sortie,
    }


def _provider() -> OllamaProvider:
    return OllamaProvider(base_url=_BASE)


def test_le_provider_ollama_satisfait_le_protocole() -> None:
    assert isinstance(_provider(), LLMProvider)
    assert _provider().name == "ollama"


def test_ollama_est_un_provider_connu() -> None:
    assert "ollama" in PROVIDERS_CONNUS
    assert get_provider("ollama").name == "ollama"


@respx.mock
async def test_complete_appelle_api_chat_et_lit_les_compteurs() -> None:
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("qwen3-coder:30b")))
    route = respx.post(f"{_BASE}/api/chat").mock(
        return_value=httpx.Response(200, json=_reponse('{"verdict": "PASS"}'))
    )

    result = await _provider().complete(
        system="tu audites", user="du code", model="qwen3-coder:30b", max_tokens=2048
    )

    assert result.content == '{"verdict": "PASS"}'
    assert result.input_tokens == 120
    assert result.output_tokens == 40
    assert result.cost_usd == 0.0
    assert result.provider_name == "ollama"
    corps = json.loads(route.calls[0].request.content)
    assert corps["model"] == "qwen3-coder:30b"
    assert corps["stream"] is False
    assert [m["role"] for m in corps["messages"]] == ["system", "user"]


@respx.mock
async def test_num_ctx_est_toujours_envoye_avec_un_plancher() -> None:
    # Le défaut d'Ollama est 4 096 : le diff de 16 000 caractères de l'audit
    # serait tronqué en silence, et le verdict porterait sur sa moitié.
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    route = respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(200, json=_reponse("x")))

    await _provider().complete(system="s", user="u", model="q", max_tokens=1)

    corps = json.loads(route.calls[0].request.content)
    assert corps["options"]["num_ctx"] >= 16_384
    assert corps["options"]["num_predict"] == 1


@respx.mock
async def test_num_ctx_grandit_avec_le_prompt() -> None:
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    route = respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(200, json=_reponse("x")))

    await _provider().complete(system="s", user="x" * 120_000, model="q", max_tokens=4096)

    corps = json.loads(route.calls[0].request.content)
    assert corps["options"]["num_ctx"] > 16_384


@respx.mock
async def test_stream_livre_chaque_fragment_et_le_contenu_entier() -> None:
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    lignes = [
        {"message": {"role": "assistant", "content": "bon"}, "done": False},
        {"message": {"role": "assistant", "content": "jour"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True,
         "prompt_eval_count": 7, "eval_count": 2},
    ]
    respx.post(f"{_BASE}/api/chat").mock(
        return_value=httpx.Response(200, content="\n".join(json.dumps(l) for l in lignes))
    )
    recus: list[str] = []

    async def on_token(t: str) -> None:
        recus.append(t)

    result = await _provider().stream(
        system="s", user="u", model="q", max_tokens=1, on_token=on_token
    )

    assert recus == ["bon", "jour"]
    assert result.content == "bonjour"
    assert result.input_tokens == 7 and result.output_tokens == 2


@respx.mock
async def test_connexion_refusee_rend_provider_indisponible() -> None:
    respx.get(f"{_BASE}/api/tags").mock(side_effect=httpx.ConnectError("refusée"))
    with pytest.raises(ProviderIndisponible):
        await _provider().complete(system="s", user="u", model="q", max_tokens=1)


@respx.mock
async def test_delai_depasse_rend_provider_indisponible() -> None:
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    respx.post(f"{_BASE}/api/chat").mock(side_effect=httpx.ReadTimeout("trop long"))
    with pytest.raises(ProviderIndisponible):
        await _provider().complete(system="s", user="u", model="q", max_tokens=1)


@respx.mock
async def test_modele_absent_rend_provider_indisponible_sans_le_tirer() -> None:
    # 19 Go ne se téléchargent pas en silence au milieu d'un run.
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("autre:7b")))
    pull = respx.post(f"{_BASE}/api/pull").mock(return_value=httpx.Response(200, json={}))
    chat = respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(200, json=_reponse("x")))

    with pytest.raises(ProviderIndisponible, match="qwen3-coder:30b"):
        await _provider().complete(system="s", user="u", model="qwen3-coder:30b", max_tokens=1)

    assert not pull.called
    assert not chat.called


@respx.mock
async def test_un_modele_sans_tag_correspond_a_sa_version_latest() -> None:
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("qwen3:latest")))
    respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(200, json=_reponse("ok")))
    result = await _provider().complete(system="s", user="u", model="qwen3", max_tokens=1)
    assert result.content == "ok"


@respx.mock
async def test_une_erreur_http_du_serveur_rend_provider_indisponible() -> None:
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(ProviderIndisponible):
        await _provider().complete(system="s", user="u", model="q", max_tokens=1)


def test_l_url_vient_du_reglage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_base_url", "http://gpu.local:11434")
    provider = get_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://gpu.local:11434"


# ------------------------------------------------------------------
# De bout en bout : Ollama absent, l'audit rend son verdict via le repli
# ------------------------------------------------------------------


@respx.mock
async def test_ollama_injoignable_l_audit_passe_par_le_repli_et_le_dit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    respx.get(f"{_BASE}/api/tags").mock(side_effect=httpx.ConnectError("refusée"))
    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "agents.json").write_text(json.dumps({"agents": [{
        "role": "securite", "model": "qwen3-coder:30b", "max_tokens": 2048,
        "prompt_file": "agents/prompts/securite.md", "active": True,
        "provider": "ollama",
        "fallback": {"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    }]}), encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "securite.md").write_text("Tu audites.", encoding="utf-8")

    repli = FakeProvider(content='{"issues": [], "verdict": "PASS", "summary": "rien"}')
    repli.name = "agent_sdk"  # type: ignore[misc]
    vrai_get_provider = par_role.get_provider

    def fabrique(name: str | None = None, api_key: str = "", **kwargs: Any) -> Any:
        if name == "ollama":
            monkeypatch.setattr(settings, "ollama_base_url", _BASE)
            return vrai_get_provider("ollama")
        return repli

    monkeypatch.setattr(par_role, "get_provider", fabrique)

    abonnement = EVENT_HUB.subscribe()
    try:
        provider = provider_pour_role(projet, "securite", allow_tools=False, project_id="demo")
        audit = SecurityAuditorService(provider, prompts, model="qwen3-coder:30b")
        resultat = await audit.audit("diff", projet)
        evenements = [e for e in abonnement.vider() if e.type == EventType.PROVIDER_FALLBACK]
    finally:
        EVENT_HUB.retirer(abonnement)

    assert resultat.verdict == "PASS"
    assert repli.calls[0]["model"] == "claude-haiku-4-5"
    assert len(evenements) == 1
    assert evenements[0].data["tente"] == "ollama"


# ------------------------------------------------------------------
# Sérialisation des requêtes Ollama par serveur (ticket-350)
# ------------------------------------------------------------------


class _CountingTransport(httpx.AsyncBaseTransport):
    """Fake transport that counts concurrent /api/chat requests."""

    def __init__(
        self,
        tags_json: dict[str, Any],
        chat_json: dict[str, Any],
        hold_s: float = 0.05,
    ) -> None:
        self._tags_json = tags_json
        self._chat_json = chat_json
        self._hold_s = hold_s
        self.concurrent = 0
        self.max_concurrent = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=self._tags_json)
        # /api/chat
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        await asyncio.sleep(self._hold_s)
        self.concurrent -= 1
        return httpx.Response(
            200,
            content=json.dumps(self._chat_json).encode(),
            headers={"content-type": "application/json"},
        )


async def test_deux_complete_sur_meme_url_ne_se_chevauchent_pas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Deux providers distincts vers le même serveur Ollama doivent se sérialiser :
    # le compteur de requêtes simultanées dans le transport ne doit jamais dépasser 1.
    monkeypatch.setattr(settings, "ollama_max_concurrent", 1)
    _reset_slots()

    base = "http://serial-same.local:11434"
    transport = _CountingTransport(_tags("q"), _reponse("ok"), hold_s=0.05)

    def _make() -> OllamaProvider:
        client = httpx.AsyncClient(transport=transport, base_url=base)
        return OllamaProvider(base_url=base, client=client)

    await asyncio.gather(
        _make().complete(system="s", user="u", model="q", max_tokens=1),
        _make().complete(system="s", user="u", model="q", max_tokens=1),
    )

    assert transport.max_concurrent == 1, (
        f"Attendu 1 requête simultanée max, observé {transport.max_concurrent}"
    )


async def test_deux_urls_differentes_ne_se_bloquent_pas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Des providers sur deux serveurs distincts doivent tourner en parallèle.
    monkeypatch.setattr(settings, "ollama_max_concurrent", 1)
    _reset_slots()

    base_a = "http://parallel-a.local:11434"
    base_b = "http://parallel-b.local:11434"

    total_concurrent: list[int] = [0]  # mutable pour nonlocal dans la closure
    max_total: list[int] = [0]

    class _TrackingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(200, json=_tags("q"))
            total_concurrent[0] += 1
            max_total[0] = max(max_total[0], total_concurrent[0])
            await asyncio.sleep(0.05)
            total_concurrent[0] -= 1
            return httpx.Response(200, json=_reponse("ok"))

    p_a = OllamaProvider(base_url=base_a, client=httpx.AsyncClient(transport=_TrackingTransport(), base_url=base_a))
    p_b = OllamaProvider(base_url=base_b, client=httpx.AsyncClient(transport=_TrackingTransport(), base_url=base_b))

    await asyncio.gather(
        p_a.complete(system="s", user="u", model="q", max_tokens=1),
        p_b.complete(system="s", user="u", model="q", max_tokens=1),
    )

    assert max_total[0] == 2, (
        f"Les deux URLs doivent tourner en parallèle, max observé : {max_total[0]}"
    )


async def test_stream_abandonne_rend_le_creneau(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Si on_token lève une exception, le créneau est rendu et un complete suivant aboutit.
    monkeypatch.setattr(settings, "ollama_max_concurrent", 1)
    _reset_slots()

    base = "http://stream-abort.local:11434"
    lignes = [
        {"message": {"role": "assistant", "content": "token"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True,
         "prompt_eval_count": 3, "eval_count": 1},
    ]
    stream_content = "\n".join(json.dumps(l) for l in lignes).encode()

    class _StreamTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(200, json=_tags("q"))
            if request.url.path == "/api/chat":
                body = json.loads(request.content)
                if body.get("stream"):
                    return httpx.Response(200, content=stream_content)
                return httpx.Response(200, json=_reponse("ok"))
            return httpx.Response(404)

    client = httpx.AsyncClient(transport=_StreamTransport(), base_url=base)
    provider = OllamaProvider(base_url=base, client=client)

    async def _on_token_raises(t: str) -> None:
        raise RuntimeError("consumer stopped")

    with pytest.raises(RuntimeError, match="consumer stopped"):
        await provider.stream(system="s", user="u", model="q", max_tokens=1, on_token=_on_token_raises)

    # Le créneau a été rendu — un complete suivant doit aboutir sans se bloquer.
    result = await provider.complete(system="s", user="u", model="q", max_tokens=1)
    assert result.content == "ok"


async def test_erreur_complete_rend_le_creneau(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Une erreur réseau pendant complete rend le créneau : l'appel suivant aboutit.
    monkeypatch.setattr(settings, "ollama_max_concurrent", 1)
    _reset_slots()

    base = "http://error-release.local:11434"
    calls: list[int] = [0]

    class _ErrorThenOkTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(200, json=_tags("q"))
            calls[0] += 1
            if calls[0] == 1:
                raise httpx.ConnectError("réseau KO")
            return httpx.Response(200, json=_reponse("ok"))

    client = httpx.AsyncClient(transport=_ErrorThenOkTransport(), base_url=base)
    provider = OllamaProvider(base_url=base, client=client)

    with pytest.raises(ProviderIndisponible):
        await provider.complete(system="s", user="u", model="q", max_tokens=1)

    # Le créneau a été rendu — l'appel suivant aboutit.
    result = await provider.complete(system="s", user="u", model="q", max_tokens=1)
    assert result.content == "ok"


# ------------------------------------------------------------------
# Attente de créneau bornée et disjoncteur par serveur (ticket-380)
# ------------------------------------------------------------------


@respx.mock
async def test_creneau_occupe_leve_provider_indisponible_sans_requete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un créneau occupé fait lever ProviderIndisponible sans requête HTTP."""
    monkeypatch.setattr(settings, "ollama_max_concurrent", 1)
    monkeypatch.setattr(settings, "ollama_slot_wait_s", 0.1)
    _reset_slots()
    _reset_cooldowns()

    base = "http://slot-wait.local:11434"
    respx.get(f"{base}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    chat_route = respx.post(f"{base}/api/chat").mock(
        return_value=httpx.Response(200, json=_reponse("ok"))
    )

    # Occuper manuellement le créneau pour le bloquer
    from tessera.services.providers.ollama import _get_slot

    slot = _get_slot(base)
    assert slot is not None
    await slot.acquire()

    try:
        with pytest.raises(ProviderIndisponible):
            await OllamaProvider(base_url=base).complete(
                system="s", user="u", model="q", max_tokens=1
            )
    finally:
        slot.release()

    assert not chat_route.called, "Aucune requête /api/chat ne doit avoir été envoyée"


async def test_apres_delai_lecture_le_serveur_est_en_refroidissement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Après un ReadTimeout, l'appel suivant lève ProviderIndisponible immédiatement."""
    monkeypatch.setattr(settings, "ollama_max_concurrent", 0)
    monkeypatch.setattr(settings, "ollama_cooldown_s", 600.0)
    _reset_slots()
    _reset_cooldowns()

    base = "http://timeout-cooldown.local:11434"
    fake_now = [0.0]
    monkeypatch.setattr(ollama_module, "_clock", lambda: fake_now[0])

    chat_calls: list[int] = [0]

    class _TimeoutTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(200, json=_tags("q"))
            chat_calls[0] += 1
            raise httpx.ReadTimeout("too slow")

    client = httpx.AsyncClient(transport=_TimeoutTransport(), base_url=base)
    provider = OllamaProvider(base_url=base, client=client)

    # Premier appel : ReadTimeout → cooldown activé
    with pytest.raises(ProviderIndisponible):
        await provider.complete(system="s", user="u", model="q", max_tokens=1)

    assert chat_calls[0] == 1

    # Deuxième appel : doit lever ProviderIndisponible aussitôt, sans requête
    with pytest.raises(ProviderIndisponible):
        await provider.complete(system="s", user="u", model="q", max_tokens=1)

    assert chat_calls[0] == 1, "Aucune nouvelle requête /api/chat ne doit avoir été envoyée"


async def test_apres_refroidissement_les_requetes_reprennent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Une fois ollama_cooldown_s écoulé, un appel envoie de nouveau une requête."""
    monkeypatch.setattr(settings, "ollama_max_concurrent", 0)
    monkeypatch.setattr(settings, "ollama_cooldown_s", 600.0)
    _reset_slots()
    _reset_cooldowns()

    base = "http://cooldown-resume.local:11434"
    fake_now = [0.0]
    monkeypatch.setattr(ollama_module, "_clock", lambda: fake_now[0])

    chat_calls: list[int] = [0]

    class _TimeoutThenOkTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(200, json=_tags("q"))
            chat_calls[0] += 1
            if chat_calls[0] == 1:
                raise httpx.ReadTimeout("too slow")
            return httpx.Response(200, json=_reponse("ok"))

    client = httpx.AsyncClient(transport=_TimeoutThenOkTransport(), base_url=base)
    provider = OllamaProvider(base_url=base, client=client)

    # Premier appel : timeout → cooldown activé
    with pytest.raises(ProviderIndisponible):
        await provider.complete(system="s", user="u", model="q", max_tokens=1)

    assert chat_calls[0] == 1

    # Simuler l'écoulement du refroidissement
    fake_now[0] = 601.0

    # Troisième appel : le cooldown est expiré, une requête est envoyée
    result = await provider.complete(system="s", user="u", model="q", max_tokens=1)
    assert result.content == "ok"
    assert chat_calls[0] == 2


@respx.mock
async def test_delai_depasse_message_contient_delai_depasse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un dépassement de délai produit un message contenant 'délai dépassé'."""
    monkeypatch.setattr(settings, "ollama_max_concurrent", 0)
    _reset_slots()
    _reset_cooldowns()

    base = "http://timeout-msg.local:11434"
    respx.get(f"{base}/api/tags").mock(return_value=httpx.Response(200, json=_tags("q")))
    respx.post(f"{base}/api/chat").mock(side_effect=httpx.ReadTimeout("trop long"))

    with pytest.raises(ProviderIndisponible, match="délai dépassé"):
        await OllamaProvider(base_url=base).complete(
            system="s", user="u", model="q", max_tokens=1
        )


def test_les_manifestes_du_depot_declarent_les_roles_locaux() -> None:
    racine = Path(__file__).resolve().parents[2] / "projects"
    # La doc est sortie d'Ollama : à ~6 tokens/s elle retenait chaque run
    # quatre minutes, pour des éditions sur un texte qui n'existait pas.
    attendus = {"validateur", "project-analyzer"}
    # Seul `ide-core` est versionné ici ; `demineur` est un dépôt à part, et
    # son manifeste se met à jour dans ce dépôt-là.
    for nom in ("ide-core",):
        configs = {c.role: c for c in load_agents_config(racine / nom)}
        assert attendus <= set(configs), nom
        for role in attendus:
            assert configs[role].provider == "ollama", (nom, role)
            assert configs[role].fallback is not None, (nom, role)
            assert configs[role].fallback.provider == "agent_sdk", (nom, role)
        # L'audit sécurité reste sur Claude : rejoué sur une traversée de
        # chemin réelle, le modèle local rendait PASS (ticket-212).
        assert configs["securite"].provider == "agent_sdk", nom
