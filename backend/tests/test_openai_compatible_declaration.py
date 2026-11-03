"""How `agents.json` declares an OpenAI-compatible endpoint, and its key — ticket-669.

La clé ne se lit que dans l'environnement, par le nom que `api_key_env`
déclare. Un manifeste qui la porte en clair est refusé, et le refus ne doit
être ni avalé par le chargeur ni recopier la valeur.
"""
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from tessera.services.project_loader import load_agents_config, set_agent_provider
from tessera.services.providers import par_role
from tessera.services.providers.declaration import resoudre_cle
from tessera.services.providers.noms import DeclarationRefusee, ProviderInconnu
from tessera.services.providers.openai_compatible import OpenAICompatibleProvider
from tessera.services.providers.par_role import provider_pour_role
from tessera.utils.secrets import SECRETS

_BASE = "http://llm.test:1234/v1"
_CLE = "valeur-de-cle-inventee-0042"


@pytest.fixture(autouse=True)
def _secrets_intacts() -> Iterator[None]:
    """Un test qui lit une clé la range dans `SECRETS` ; on rend l'état d'avant."""
    avant = SECRETS.valeurs()
    yield
    SECRETS.clear()
    SECRETS.register_all(avant)


def _manifeste(tmp_path: Path, **extra: Any) -> Path:
    projet = tmp_path / "projet"
    projet.mkdir(exist_ok=True)
    (projet / "agents.json").write_text(json.dumps({"agents": [{
        "role": "securite", "model": "modele-x", "max_tokens": 2048,
        "prompt_file": "agents/prompts/securite.md", "active": True,
        "provider": "openai_compatible", "base_url": _BASE, **extra,
    }]}), encoding="utf-8")
    return projet


def test_un_manifeste_valide_porte_base_url_et_nom_de_variable(tmp_path: Path) -> None:
    [config] = load_agents_config(_manifeste(tmp_path, api_key_env="OPENROUTER_API_KEY"))
    assert config.provider == "openai_compatible"
    assert config.base_url == _BASE
    assert config.api_key_env == "OPENROUTER_API_KEY"


@respx.mock
async def test_la_cle_est_lue_dans_l_environnement_par_api_key_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_ENDPOINT_KEY", _CLE)
    route = respx.post(f"{_BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        })
    )
    projet = _manifeste(tmp_path, api_key_env="TEST_ENDPOINT_KEY")

    provider = provider_pour_role(projet, "securite", allow_tools=False)
    await provider.complete(system="s", user="u", model="modele-x", max_tokens=1)

    assert route.calls[0].request.headers["authorization"] == f"Bearer {_CLE}"
    assert _CLE in SECRETS.valeurs()


@pytest.mark.parametrize("champ", ["api_key", "apiKey", "api-key", "token", "Authorization"])
def test_une_cle_en_clair_est_refusee_sans_etre_recopiee(
    tmp_path: Path, champ: str
) -> None:
    projet = _manifeste(tmp_path, **{champ: _CLE})
    # Le refus doit sortir du chargeur : `[]` enverrait le rôle sur le défaut.
    with pytest.raises(DeclarationRefusee, match="securite") as erreur:
        load_agents_config(projet)
    assert _CLE not in str(erreur.value)
    assert isinstance(erreur.value, ProviderInconnu)


@pytest.mark.parametrize("valeur", ["sk-live-abc123", "SK_LIVE_ABC123", "cle_en_minuscules", "A B", ""])
def test_un_api_key_env_qui_ressemble_a_une_cle_est_refuse(
    tmp_path: Path, valeur: str
) -> None:
    with pytest.raises(DeclarationRefusee, match="api_key_env") as erreur:
        load_agents_config(_manifeste(tmp_path, api_key_env=valeur))
    if valeur:
        assert valeur not in str(erreur.value)


@pytest.mark.parametrize("url", [None, "", "llm.test:1234", "ftp://llm.test"])
def test_une_base_url_absente_ou_invalide_est_refusee(
    tmp_path: Path, url: str | None
) -> None:
    projet = _manifeste(tmp_path, base_url=url)
    with pytest.raises(DeclarationRefusee, match="base_url"):
        load_agents_config(projet)


def test_openai_compatible_ne_peut_pas_servir_de_repli(tmp_path: Path) -> None:
    projet = _manifeste(
        tmp_path, provider="agent_sdk",
        fallback={"provider": "openai_compatible", "model": "x"},
    )
    with pytest.raises(DeclarationRefusee, match="repli"):
        load_agents_config(projet)


def test_set_agent_provider_refuse_openai_sans_base_url_et_n_ecrit_rien(
    tmp_path: Path,
) -> None:
    projet = _manifeste(tmp_path, provider="agent_sdk", base_url=None)
    avant = (projet / "agents.json").read_text(encoding="utf-8")
    with pytest.raises(DeclarationRefusee, match="base_url"):
        set_agent_provider(projet, "securite", "openai_compatible", fallback=None)
    assert (projet / "agents.json").read_text(encoding="utf-8") == avant


def test_set_agent_provider_garde_la_base_url_declaree(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, provider="agent_sdk")
    set_agent_provider(projet, "securite", "openai_compatible", fallback=None)
    [config] = load_agents_config(projet)
    assert (config.provider, config.base_url) == ("openai_compatible", _BASE)


def test_un_autre_provider_ne_recoit_ni_url_ni_cle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_ENDPOINT_KEY", _CLE)
    projet = _manifeste(tmp_path, provider="agent_sdk", api_key_env="TEST_ENDPOINT_KEY")
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> Any:
        appels.append(kwargs)
        return object()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    provider_pour_role(projet, "securite", allow_tools=False)
    assert appels[0]["base_url"] is None
    assert appels[0]["endpoint_key"] == ""


def test_le_provider_construit_par_role_porte_l_url_et_la_cle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_ENDPOINT_KEY", _CLE)
    projet = _manifeste(tmp_path, api_key_env="TEST_ENDPOINT_KEY")
    provider = provider_pour_role(projet, "securite", allow_tools=False)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == _BASE
    assert _CLE not in repr(provider)


def test_resoudre_cle_rend_vide_sans_nom_ou_sans_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_ENDPOINT_ABSENTE", raising=False)
    assert resoudre_cle(None) == ""
    assert resoudre_cle("TEST_ENDPOINT_ABSENTE") == ""
