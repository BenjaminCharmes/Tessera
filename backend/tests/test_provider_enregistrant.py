"""Recording every LLM call within a pipeline run — ticket-211.

Ce que ce fichier vérifie :
- `ProviderEnregistrant` persiste chaque appel dans `agent_calls` quand un
  contexte de run est actif
- Il est transparent hors contexte (chat, analyse de projet)
- L'audit sécurité et le validateur produisent bien des lignes dans `agent_calls`
- Un appel Ollama s'enregistre avec `cost_usd = 0.0` et `provider = "ollama"`
- Un repli enregistre le provider et le modèle du repli, pas du principal
"""
from pathlib import Path
from typing import Any

import aiosqlite
import pytest

from tessera.services.database import create_run, init_db
from tessera.services.providers.base import ProviderResult
from tessera.services.providers.enregistrant import (
    ProviderEnregistrant,
    activer_enregistrement,
)
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.repli import ProviderAvecRepli
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.validator import ValidatorService
from tests.test_providers_base import FakeProvider


class OllamaFake:
    """Provider double that mimics Ollama: reports cost_usd=0.0."""

    name = "ollama"

    async def complete(self, *, system: str, user: str, model: str, max_tokens: int, **_: Any) -> ProviderResult:
        return ProviderResult(
            content="réponse ollama",
            input_tokens=5,
            output_tokens=5,
            cost_usd=0.0,
            provider_name="ollama",
        )

    async def stream(self, **kw: Any) -> ProviderResult:
        return await self.complete(**kw)


class OllamaIndisponible:
    """Provider double that raises ProviderIndisponible on every call."""

    name = "ollama"

    async def complete(self, **_: Any) -> ProviderResult:
        raise ProviderIndisponible("Ollama hors ligne")

    async def stream(self, **_: Any) -> ProviderResult:
        raise ProviderIndisponible("Ollama hors ligne")


async def test_enregistre_complete_dans_agent_calls(tmp_path: Path) -> None:
    """A `complete()` call is persisted when a run context is active."""
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    run_id = await create_run(db_path, "proj", "ticket-001")

    provider = ProviderEnregistrant(
        FakeProvider(tokens=20, cost_usd=0.01), role="codeur", db_path=db_path
    )
    activer_enregistrement(run_id, "ticket-001")
    await provider.complete(system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=512)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT role, provider, cost_usd FROM agent_calls WHERE run_id=?", (run_id,)
        ) as cur:
            rows = await cur.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "codeur"
    assert rows[0][1] == "fake"
    assert rows[0][2] == pytest.approx(0.01)


async def test_pas_d_enregistrement_hors_contexte(tmp_path: Path) -> None:
    """Outside a run context the wrapper is a pass-through — nothing is written."""
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    await create_run(db_path, "proj", "ticket-001")

    # Explicitly clear the context
    activer_enregistrement(None, None)
    provider = ProviderEnregistrant(FakeProvider(), role="codeur", db_path=db_path)
    await provider.complete(system="sys", user="usr", model="m", max_tokens=8)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute("SELECT COUNT(*) FROM agent_calls") as cur:
            (count,) = await cur.fetchone()  # type: ignore[misc]

    assert count == 0


async def test_securite_et_validateur_dans_agent_calls(tmp_path: Path) -> None:
    """A run with security + validator produces one row each in agent_calls."""
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    run_id = await create_run(db_path, "proj", "ticket-001")
    activer_enregistrement(run_id, "ticket-001")

    # Les services disposent de prompts de secours — pas besoin de fichiers.
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    # Audit sécurité — le provider enveloppé persiste l'appel
    audit_provider = ProviderEnregistrant(
        FakeProvider(content='{"verdict":"PASS","issues":[],"summary":"clean"}'),
        role="securite",
        db_path=db_path,
    )
    auditor = SecurityAuditorService(audit_provider, prompts)
    await auditor.audit("diff content", tmp_path)

    # Validateur — idem
    validator_provider = ProviderEnregistrant(
        FakeProvider(content='{"criteria":[],"feedback":"ok","verdict":"APPROVED"}'),
        role="validateur",
        db_path=db_path,
    )
    validator = ValidatorService(validator_provider, prompts)
    await validator.validate(criteria=[], code_produced="code", test_result=None)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT role FROM agent_calls WHERE run_id=? ORDER BY id", (run_id,)
        ) as cur:
            roles = [r[0] for r in await cur.fetchall()]

    assert "securite" in roles
    assert "validateur" in roles


async def test_ollama_enregistre_cost_zero(tmp_path: Path) -> None:
    """An Ollama call is recorded with cost_usd=0.0 and provider='ollama'."""
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    run_id = await create_run(db_path, "proj", "ticket-001")
    activer_enregistrement(run_id, "ticket-001")

    provider = ProviderEnregistrant(OllamaFake(), role="securite", db_path=db_path)
    await provider.complete(system="sys", user="usr", model="qwen2.5:7b", max_tokens=256)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT provider, cost_usd FROM agent_calls WHERE run_id=?", (run_id,)
        ) as cur:
            row = await cur.fetchone()

    assert row is not None
    assert row[0] == "ollama"
    assert row[1] == pytest.approx(0.0)


async def test_repli_enregistre_provider_de_repli(tmp_path: Path) -> None:
    """When Ollama is unavailable, the fallback provider and model are recorded."""
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    run_id = await create_run(db_path, "proj", "ticket-001")
    activer_enregistrement(run_id, "ticket-001")

    repli = FakeProvider(content="fallback", cost_usd=0.005)
    repli.name = "agent_sdk"  # type: ignore[attr-defined]

    provider_avec_repli = ProviderAvecRepli(
        OllamaIndisponible(),  # type: ignore[arg-type]
        repli,
        modele_repli="claude-haiku-4-5",
        role="securite",
        project_id=None,
    )
    wrapper = ProviderEnregistrant(provider_avec_repli, role="securite", db_path=db_path)

    await wrapper.complete(system="sys", user="usr", model="qwen2.5:7b", max_tokens=256)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT provider, model, cost_usd FROM agent_calls WHERE run_id=?", (run_id,)
        ) as cur:
            row = await cur.fetchone()

    assert row is not None
    assert row[0] == "agent_sdk"
    assert row[1] == "claude-haiku-4-5"
    assert row[2] == pytest.approx(0.005)
