import os
from pathlib import Path
from typing import Any

import aiosqlite
import pytest

from tests.test_providers_base import FakeProvider
from tessera.models.agent import AgentConfig, AgentResult, AgentRole
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.prompt_loader import MissingPromptError
from tessera.services.agent_runner import (
    _DEFAULT_MAX_TOKENS,
    _DEFAULT_MODEL,
    AgentRunner,
    _parse_suggested_status,
)
from tessera.services.cost_calculator import calculate_cost
from tessera.services.database import create_run, init_db


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_ticket(**kwargs: object) -> Ticket:
    defaults: dict[str, object] = {
        "id": "ticket-001",
        "title": "Implémenter la feature X",
        "type": TicketType.feat,
        "status": TicketStatus.todo,
        "priority": TicketPriority.medium,
        "agent": "codeur",
        "body": "## Description\nImplémenter la feature X.\n\n## Critères\n- [ ] Tests écrits",
    }
    return Ticket(**(defaults | kwargs))


def _runner(
    tmp_path: Path,
    provider: FakeProvider | None = None,
    project_path: Path | None = None,
) -> AgentRunner:
    # Les prompts sont désormais obligatoires (ticket-051) : un runner de test
    # doit disposer de vrais fichiers, sinon il échoue sur MissingPromptError
    # avant même d'atteindre ce qu'on veut vérifier.
    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    for role in ("codeur", "reviewer", "architect", "testeur", "redacteur"):
        prompt_file = prompts / f"{role}.md"
        if not prompt_file.exists():
            prompt_file.write_text(f"Tu es le {role}.", encoding="utf-8")

    registry = AgentRegistryService(prompts)
    return AgentRunner(
        provider or FakeProvider(),
        registry,
        project_path=project_path,
    )


# ------------------------------------------------------------------
# _parse_suggested_status
# ------------------------------------------------------------------


def test_parse_status_in_review() -> None:
    content = "## Analyse\nTout bon.\n\n## Statut suggéré\nIN_REVIEW — code prêt pour review"
    assert _parse_suggested_status(content) == TicketStatus.in_review


def test_parse_status_in_review_hyphen() -> None:
    assert _parse_suggested_status("## Statut suggéré\nIN-REVIEW") == TicketStatus.in_review


def test_parse_status_blocked() -> None:
    assert _parse_suggested_status("## Statut suggéré\nBLOCKED — besoin de précisions") == TicketStatus.blocked


def test_parse_status_done() -> None:
    assert _parse_suggested_status("## Statut suggéré\nDONE") == TicketStatus.done


def test_parse_status_todo() -> None:
    assert _parse_suggested_status("## Statut suggéré\nTODO") == TicketStatus.todo


def test_parse_status_default_when_absent() -> None:
    assert _parse_suggested_status("Réponse sans section statut.") == TicketStatus.in_review


def test_parse_status_accent_insensitive() -> None:
    content = "## Statut suggere\nIN_REVIEW"
    assert _parse_suggested_status(content) == TicketStatus.in_review


# ------------------------------------------------------------------
# _load_system_prompt
# ------------------------------------------------------------------


def test_load_system_prompt_reads_file(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "codeur.md").write_text("Tu es le codeur.", encoding="utf-8")

    registry = AgentRegistryService(prompts)
    runner = AgentRunner(FakeProvider(), registry)
    assert runner._load_system_prompt("codeur") == "Tu es le codeur."


def test_load_system_prompt_echoue_quand_le_role_est_absent(tmp_path: Path) -> None:
    # Un agent privé de son system prompt ne s'arrête pas : il produit du
    # travail hors sujet mais plausible. Échouer net coûte moins cher
    # (ticket-051).
    runner = _runner(tmp_path)

    with pytest.raises(MissingPromptError) as exc:
        runner._load_system_prompt("role-inexistant")

    message = str(exc.value)
    assert "role-inexistant.md" in message
    assert "IDE_PROMPTS_DIR" in message


def test_load_system_prompt_echoue_quand_le_prompt_est_vide(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    (tmp_path / "prompts" / "vide.md").write_text("  \n", encoding="utf-8")

    with pytest.raises(MissingPromptError):
        runner._load_system_prompt("vide")


# ------------------------------------------------------------------
# _build_user_prompt
# ------------------------------------------------------------------


def test_build_user_prompt_contains_ticket_body(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    ticket = _make_ticket(body="Corps du ticket précis.")

    prompt = runner._build_user_prompt(ticket, "codeur", "contexte projet")

    assert "Corps du ticket précis." in prompt
    assert "contexte projet" in prompt


def test_build_user_prompt_has_required_sections(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    prompt = runner._build_user_prompt(_make_ticket(), "codeur", "ctx")

    assert "## Contexte projet" in prompt
    assert "## Ticket assigné" in prompt
    assert "## Ta mission" in prompt


def test_build_user_prompt_instruction_varies_by_role(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    ticket = _make_ticket()

    codeur_prompt = runner._build_user_prompt(ticket, "codeur", "ctx")
    reviewer_prompt = runner._build_user_prompt(ticket, "reviewer", "ctx")

    assert codeur_prompt != reviewer_prompt


# ------------------------------------------------------------------
# AgentRunner.run — délégation au provider
# ------------------------------------------------------------------


async def test_run_returns_agent_result(tmp_path: Path) -> None:
    response = "## Analyse\nOK.\n\n## Statut suggéré\nIN_REVIEW"
    provider = FakeProvider(content=response)
    runner = _runner(tmp_path, provider)

    result = await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="Contexte test",
    )

    assert isinstance(result, AgentResult)
    assert result.ticket_id == "ticket-001"
    assert result.role == "codeur"
    assert result.suggested_status == TicketStatus.in_review
    assert result.duration_ms >= 0
    assert result.content == response


async def test_run_accepts_str_role(tmp_path: Path) -> None:
    response = "## Statut suggéré\nIN_REVIEW"
    provider = FakeProvider(content=response)
    runner = _runner(tmp_path, provider)

    result = await runner.run(
        role="redacteur",
        ticket=_make_ticket(),
        project_context="ctx",
    )

    assert result.role == "redacteur"


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
    assert provider.calls[0]["model"] == _DEFAULT_MODEL
    assert provider.calls[0]["max_tokens"] == _DEFAULT_MAX_TOKENS
    assert result.content == "## Statut suggéré\nIN_REVIEW"
    assert result.suggested_status == TicketStatus.in_review


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


async def test_run_transmet_le_project_path_en_cwd(tmp_path: Path) -> None:
    provider = FakeProvider()
    projet = tmp_path / "mon-projet"
    projet.mkdir()
    runner = _runner(tmp_path, provider, project_path=projet)
    await runner.run(
        role=AgentRole.codeur, ticket=_make_ticket(), project_context="ctx"
    )
    assert provider.calls[0]["cwd"] == projet.resolve()


# ------------------------------------------------------------------
# AgentRunner.run — streaming (via provider)
# ------------------------------------------------------------------


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


# ------------------------------------------------------------------
# AgentRunner.run — coût persisté (provider vs. calcul de repli)
# ------------------------------------------------------------------


async def test_run_persiste_le_cout_rapporte_par_le_provider(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    run_id = await create_run(db_path, "project-1", "ticket-001")

    provider = FakeProvider(tokens=100, cost_usd=0.042)
    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    (prompts / "codeur.md").write_text("Tu es le codeur.", encoding="utf-8")
    registry = AgentRegistryService(prompts)
    runner = AgentRunner(provider, registry, db_path=db_path)

    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
        run_id=run_id,
    )

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT cost_usd FROM agent_calls WHERE run_id=?", (run_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == pytest.approx(0.042)


async def test_run_calcule_le_cout_quand_le_provider_ne_le_rapporte_pas(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    run_id = await create_run(db_path, "project-1", "ticket-001")

    provider = FakeProvider(tokens=100)  # cost_usd=None par défaut
    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    (prompts / "codeur.md").write_text("Tu es le codeur.", encoding="utf-8")
    registry = AgentRegistryService(prompts)
    runner = AgentRunner(provider, registry, db_path=db_path)

    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
        run_id=run_id,
    )

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT cost_usd FROM agent_calls WHERE run_id=?", (run_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    expected_cost = calculate_cost(_DEFAULT_MODEL, 100, 100, 0)
    assert len(rows) == 1
    assert rows[0][0] == pytest.approx(expected_cost)


# ------------------------------------------------------------------
# Test d'intégration (API réelle — skippé si clé dummy)
# ------------------------------------------------------------------


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
    outils: list[tuple[str, dict[str, Any]]] = []

    async def on_tool(name: str, payload: dict[str, Any]) -> None:
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


@pytest.mark.integration
async def test_run_real_api(tmp_path: Path) -> None:
    """Requires a real ANTHROPIC_API_KEY (not 'dummy')."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "dummy":
        pytest.skip("ANTHROPIC_API_KEY non disponible pour le test d'intégration")

    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "codeur.md").write_text(
        "Tu es un agent de test. Réponds en 30 mots maximum.", encoding="utf-8"
    )

    from anthropic import AsyncAnthropic

    from tessera.services.providers.anthropic_api import AnthropicApiProvider

    provider = AnthropicApiProvider(AsyncAnthropic(api_key=api_key))
    registry = AgentRegistryService(prompts)
    runner = AgentRunner(provider, registry)
    ticket = _make_ticket(body="Dis bonjour en Python avec print().")

    result = await runner.run(
        role=AgentRole.codeur,
        ticket=ticket,
        project_context="Projet de test minimal.",
    )

    assert result.content
    assert result.duration_ms > 0
    assert isinstance(result.suggested_status, TicketStatus)
