"""An Ollama provider for the tool-less roles — ticket-189.

Sept services ne font qu'un appel texte→JSON : un modèle local les sert à
coût nul. Le repli du ticket-188 est ce qui rend le manifeste portable sur
une machine où Ollama n'est pas là.
"""
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
from tessera.services.providers.ollama import OllamaProvider
from tessera.services.providers import par_role
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.project_loader import load_agents_config
from tests.test_providers_base import FakeProvider

_BASE = "http://ollama.test:11434"


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


def test_les_manifestes_du_depot_declarent_les_roles_locaux() -> None:
    racine = Path(__file__).resolve().parents[2] / "projects"
    attendus = {"validateur", "doc-technique", "doc-fonctionnelle", "project-analyzer"}
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
