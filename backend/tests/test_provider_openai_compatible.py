"""An OpenAI-compatible provider for the tool-less roles — ticket-669.

Comme Ollama, il sert les rôles texte→JSON. Le double HTTP est `respx` : aucune
requête ne part vers un vrai serveur.
"""
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType
from tessera.services.providers import get_provider, par_role
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.noms import PROVIDERS_CONNUS, ProviderIndisponible
from tessera.services.providers.openai_compatible import OpenAICompatibleProvider
from tessera.services.providers.par_role import provider_pour_role
from tests.test_providers_base import FakeProvider

_BASE = "http://llm.test:1234/v1"
_URL = f"{_BASE}/chat/completions"
_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"verdict": {"type": "string"}},
    "required": ["verdict"],
}


def _provider(api_key: str = "") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(base_url=_BASE, api_key=api_key)


def _reponse(contenu: str, fin: str = "stop") -> dict[str, Any]:
    return {
        "choices": [{
            "index": 0, "finish_reason": fin,
            "message": {"role": "assistant", "content": contenu},
        }],
        "usage": {"prompt_tokens": 120, "completion_tokens": 40},
    }


async def _complete(provider: LLMProvider, **extra: Any) -> Any:
    return await provider.complete(
        system="tu audites", user="du code", model="modele-x", max_tokens=512, **extra
    )


def test_le_provider_satisfait_le_protocole_et_est_connu() -> None:
    assert isinstance(_provider(), LLMProvider)
    assert _provider().name == "openai_compatible"
    assert "openai_compatible" in PROVIDERS_CONNUS


def test_get_provider_exige_une_base_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        get_provider("openai_compatible")
    provider = get_provider("openai_compatible", base_url=f"{_BASE}/")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == _BASE


@respx.mock
async def test_complete_envoie_le_modele_et_les_messages_et_rend_le_texte() -> None:
    route = respx.post(_URL).mock(
        return_value=httpx.Response(200, json=_reponse("tout va bien"))
    )

    result = await _complete(_provider())

    assert result.content == "tout va bien"
    assert (result.input_tokens, result.output_tokens) == (120, 40)
    assert result.cost_usd == 0.0
    assert result.provider_name == "openai_compatible"
    requete = route.calls[0].request
    corps = json.loads(requete.content)
    assert corps["model"] == "modele-x"
    assert corps["max_tokens"] == 512
    assert corps["stream"] is False
    assert corps["messages"] == [
        {"role": "system", "content": "tu audites"},
        {"role": "user", "content": "du code"},
    ]
    assert "response_format" not in corps
    assert "authorization" not in requete.headers


@respx.mock
async def test_la_cle_part_en_authorization_bearer() -> None:
    route = respx.post(_URL).mock(return_value=httpx.Response(200, json=_reponse("ok")))
    await _complete(_provider(api_key="cle-inventee"))
    assert route.calls[0].request.headers["authorization"] == "Bearer cle-inventee"


def test_le_repr_ne_montre_pas_la_cle() -> None:
    assert "cle-inventee" not in repr(_provider(api_key="cle-inventee"))


@respx.mock
async def test_un_schema_part_dans_response_format_et_revient_structure() -> None:
    route = respx.post(_URL).mock(
        return_value=httpx.Response(200, json=_reponse('{"verdict": "PASS"}'))
    )

    result = await _complete(_provider(), schema=_SCHEMA)

    corps = json.loads(route.calls[0].request.content)
    assert corps["response_format"]["type"] == "json_schema"
    assert corps["response_format"]["json_schema"]["schema"] == _SCHEMA
    assert result.structured == {"verdict": "PASS"}
    assert result.content == '{"verdict": "PASS"}'


@respx.mock
@pytest.mark.parametrize(
    ("contenu", "fin"),
    [('{"verdict": "PA', "length"), ("pas du json", "stop"), ("[1, 2]", "stop")],
)
async def test_une_sortie_coupee_ou_invalide_n_est_pas_structuree(
    contenu: str, fin: str
) -> None:
    respx.post(_URL).mock(return_value=httpx.Response(200, json=_reponse(contenu, fin)))
    result = await _complete(_provider(), schema=_SCHEMA)
    assert result.structured is None
    assert result.content == contenu


@respx.mock
async def test_stream_livre_chaque_fragment_et_le_contenu_entier() -> None:
    morceaux = [
        {"choices": [{"delta": {"content": "bon"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "jour"}, "finish_reason": "stop"}]},
        {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 2}},
    ]
    sse = "".join(f"data: {json.dumps(m)}\n\n" for m in morceaux) + "data: [DONE]\n\n"
    route = respx.post(_URL).mock(return_value=httpx.Response(200, content=sse))
    recus: list[str] = []

    async def on_token(t: str) -> None:
        recus.append(t)

    result = await _provider().stream(
        system="s", user="u", model="m", max_tokens=1, on_token=on_token
    )

    assert recus == ["bon", "jour"]
    assert result.content == "bonjour"
    assert (result.input_tokens, result.output_tokens) == (7, 2)
    assert json.loads(route.calls[0].request.content)["stream"] is True


@respx.mock
async def test_une_erreur_de_connexion_rend_provider_indisponible() -> None:
    respx.post(_URL).mock(side_effect=httpx.ConnectError("refusée"))
    with pytest.raises(ProviderIndisponible):
        await _complete(_provider())


@respx.mock
@pytest.mark.parametrize(
    ("statut", "corps"),
    [
        (500, {"text": "boom"}),
        (401, {"json": {"error": "clé refusée"}}),
        (200, {"text": "<html>pas une API</html>"}),
        (200, {"json": {"error": {"message": "quota"}}}),
    ],
)
async def test_une_reponse_inexploitable_rend_provider_indisponible(
    statut: int, corps: dict[str, Any]
) -> None:
    respx.post(_URL).mock(
        side_effect=lambda request: httpx.Response(statut, **corps)
    )
    with pytest.raises(ProviderIndisponible):
        await _complete(_provider())
    # Le flux lit la même réponse : un statut ≥ 400 doit aussi lever. Un 200
    # sans ligne `data:` rend un texte vide, ce n'est pas une indisponibilité.
    if statut >= 400:
        with pytest.raises(ProviderIndisponible):
            await _provider().stream(system="s", user="u", model="m", max_tokens=1)


@respx.mock
async def test_une_connexion_refusee_declenche_le_repli_et_l_evenement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    respx.post(_URL).mock(side_effect=httpx.ConnectError("refusée"))
    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "agents.json").write_text(json.dumps({"agents": [{
        "role": "securite", "model": "modele-x", "max_tokens": 2048,
        "prompt_file": "agents/prompts/securite.md", "active": True,
        "provider": "openai_compatible", "base_url": _BASE,
        "fallback": {"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    }]}), encoding="utf-8")
    repli = FakeProvider(content='{"verdict": "PASS"}')
    repli.name = "agent_sdk"  # type: ignore[misc]
    vrai_get_provider = par_role.get_provider

    def fabrique(name: str | None = None, api_key: str = "", **kwargs: Any) -> Any:
        if name == "openai_compatible":
            return vrai_get_provider(name, api_key, **kwargs)
        return repli

    monkeypatch.setattr(par_role, "get_provider", fabrique)

    abonnement = EVENT_HUB.subscribe()
    try:
        provider = provider_pour_role(projet, "securite", allow_tools=False, project_id="demo")
        result = await _complete(provider)
        evenements = [e for e in abonnement.vider() if e.type == EventType.PROVIDER_FALLBACK]
    finally:
        EVENT_HUB.retirer(abonnement)

    assert result.content == '{"verdict": "PASS"}'
    assert repli.calls[0]["model"] == "claude-haiku-4-5"
    assert len(evenements) == 1
    assert evenements[0].data["tente"] == "openai_compatible"
    assert evenements[0].data["utilise"] == "agent_sdk"
