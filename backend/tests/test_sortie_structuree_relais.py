"""The schema travels through the wrappers and AgentRunner — ticket-612 (ADR-061)."""
from pathlib import Path
from typing import Any

from tessera.services.agent_runner import AgentRunner
from tessera.services.providers.base import LLMProvider, ProviderResult
from tessera.services.providers.enregistrant import ProviderEnregistrant
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.repli import ProviderAvecRepli
from tests.test_agent_runner import _make_ticket, _runner
from tests.test_providers_base import FakeProvider

SCHEMA: dict[str, Any] = {"type": "object", "properties": {"verdict": {"type": "string"}}}
SORTIE: dict[str, Any] = {"verdict": "OK"}
_APPEL: dict[str, Any] = {"system": "s", "user": "u", "model": "m", "max_tokens": 10}


class _Structure(FakeProvider):
    """Returns a validated output, like a provider that was given a schema."""

    async def complete(self, **kwargs: Any) -> ProviderResult:
        resultat = await super().complete(**kwargs)
        resultat.structured = SORTIE
        return resultat

    async def stream(self, **kwargs: Any) -> ProviderResult:
        resultat = await super().stream(**kwargs)
        resultat.structured = SORTIE
        return resultat


class _Indisponible(FakeProvider):
    async def complete(self, **kwargs: Any) -> ProviderResult:
        raise ProviderIndisponible("hors ligne")


class _SansSchema:
    """A double that knows nothing of `schema`: passing it would raise."""

    name = "strict"

    def __init__(self) -> None:
        self.appels = 0

    async def complete(
        self, *, system: str, user: str, model: str, max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        self.appels += 1
        return ProviderResult(content="ok", provider_name=self.name)

    async def stream(self, **kwargs: Any) -> ProviderResult:
        raise AssertionError("complete attendu")


def _avec_repli(principal: LLMProvider, repli: LLMProvider) -> ProviderAvecRepli:
    return ProviderAvecRepli(
        principal, repli, modele_repli="m2", role="validateur", project_id=None
    )


# --- ProviderAvecRepli ---


async def test_le_repli_recoit_le_meme_schema() -> None:
    repli = _Structure()
    resultat = await _avec_repli(_Indisponible(), repli).complete(**_APPEL, schema=SCHEMA)
    assert repli.calls[0]["schema"] == SCHEMA
    assert resultat.structured == SORTIE


async def test_une_sortie_invalide_du_principal_ne_declenche_aucun_repli() -> None:
    principal, repli = FakeProvider(), _Structure()
    resultat = await _avec_repli(principal, repli).complete(**_APPEL, schema=SCHEMA)
    assert resultat.structured is None
    assert principal.calls[0]["schema"] == SCHEMA
    assert repli.calls == []


# --- ProviderEnregistrant ---


async def test_l_enregistrant_transmet_le_schema_seulement_s_il_est_pose() -> None:
    interne = _Structure()
    enveloppe = ProviderEnregistrant(interne, role="validateur", db_path=None)
    await enveloppe.complete(**_APPEL, schema=SCHEMA)
    await enveloppe.complete(**_APPEL)
    assert interne.calls[0]["schema"] == SCHEMA
    assert "schema" not in interne.calls[1]


# --- AgentRunner ---


async def test_run_transmet_le_schema_et_reprend_la_sortie(tmp_path: Path) -> None:
    provider = _Structure()
    resultat = await _runner(tmp_path, provider).run(
        "reviewer", _make_ticket(), "ctx", schema=SCHEMA
    )
    assert provider.calls[0]["schema"] == SCHEMA
    assert resultat.structured == SORTIE


async def test_run_en_streaming_transmet_aussi_le_schema(tmp_path: Path) -> None:
    provider = _Structure()

    async def on_token(_: str) -> None:
        return None

    resultat = await _runner(tmp_path, provider).run(
        "reviewer", _make_ticket(), "ctx", stream_callback=on_token, schema=SCHEMA
    )
    assert provider.calls[0]["mode"] == "stream"
    assert provider.calls[0]["schema"] == SCHEMA
    assert resultat.structured == SORTIE


async def test_run_sans_schema_ne_change_rien(tmp_path: Path) -> None:
    provider = FakeProvider()
    resultat = await _runner(tmp_path, provider).run("reviewer", _make_ticket(), "ctx")
    assert "schema" not in provider.calls[0]
    assert resultat.structured is None


async def test_run_sans_schema_ne_le_transmet_pas_a_un_double_qui_l_ignore(
    tmp_path: Path,
) -> None:
    double = _SansSchema()
    runner: AgentRunner = _runner(tmp_path)
    runner._provider = double  # type: ignore[assignment]
    resultat = await runner.run("reviewer", _make_ticket(), "ctx")
    assert double.appels == 1
    assert resultat.content == "ok"
