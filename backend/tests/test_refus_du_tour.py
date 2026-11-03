"""Le reviewer et le validateur savent ce que le garde-fou a refusé — ticket-476."""
import json
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tessera.services.orchestrator import Orchestrator
from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.providers.refus_garde import (
    TITRE_REFUS,
    JournalDesRefus,
    refus_du_tour,
    section_refus,
)
from tessera.services.validator import ValidatorService
from tests.test_orchestrator import _FakeGit, _make_agent_result, _make_ticket, _noop
from tests.test_providers_base import FakeProvider

_VERDICT = {
    "criteria": [{"index": 1, "criterion": "c", "passed": True, "note": ""}],
    "feedback": "ok",
}


def test_le_journal_dedoublonne_et_se_vide() -> None:
    journal = JournalDesRefus()
    journal.noter("CLAUDE.md", "protégé")
    journal.noter("CLAUDE.md", "protégé")
    journal.noter("agents.json", "protégé")

    assert [r.chemin for r in journal.vider()] == ["CLAUDE.md", "agents.json"]
    assert journal.vider() == []


def test_la_section_porte_le_titre_le_chemin_et_la_consigne() -> None:
    journal = JournalDesRefus()
    journal.noter("CLAUDE.md", "un run ne modifie pas ses règles")

    section = section_refus(journal.vider())

    assert TITRE_REFUS in section and "`CLAUDE.md`" in section
    assert "Ne redemande pas" in section
    assert section_refus([]) == ""


def test_sans_journal_aucune_section() -> None:
    assert refus_du_tour(object()) == ""


async def test_le_hook_note_le_refus_de_claude_md(tmp_path: Path) -> None:
    journal = JournalDesRefus()
    hook = hook_refus_hors_perimetre(tmp_path, journal=journal)

    sortie = await hook(
        {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "CLAUDE.md")}},
        None, None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"
    (refus,) = journal.vider()
    assert refus.chemin.endswith("CLAUDE.md") and "règles" in refus.raison


class _CodeurRefuse:
    """Le codeur tente d'écrire `CLAUDE.md` : le garde-fou refuse, le journal le note."""

    def __init__(self, journal: JournalDesRefus) -> None:
        self._journal = journal
        self.contextes_reviewer: list[str] = []

    async def run(self, **kwargs: object) -> AgentResult:
        role = kwargs["role"]
        assert isinstance(role, AgentRole)
        if role == AgentRole.reviewer:
            self.contextes_reviewer.append(str(kwargs["project_context"]))
            return _make_agent_result("APPROVED", role=role)
        self._journal.noter("CLAUDE.md", "un run ne modifie pas ses propres règles")
        return _make_agent_result("prose du codeur", role=role)


async def test_un_refus_du_tour_arrive_au_reviewer_et_au_validateur(tmp_path: Path) -> None:
    journal = JournalDesRefus()
    runner = _CodeurRefuse(journal)
    provider = FakeProvider(content=json.dumps(_VERDICT))
    ticket = _make_ticket(body="## Critères d'acceptation\n- [ ] ça marche\n")
    service = AsyncMock()
    service.get_ticket.return_value = ticket
    orch = Orchestrator(
        runner=runner, ticket_service=service, project_context="ctx",  # type: ignore[arg-type]
        agent_configs=[], pipeline_log_path=tmp_path / "memory" / "pipeline-log.md",
        validator=ValidatorService(provider, Path("agents/prompts")),
        git_workspace=_FakeGit(), journal_refus=journal,  # type: ignore[arg-type]
    )

    result = await orch.run_pipeline("projet", "ticket-001", _noop)

    assert result.final_status is not TicketStatus.blocked
    (contexte,) = runner.contextes_reviewer
    assert TITRE_REFUS in contexte and "CLAUDE.md" in contexte
    (appel,) = provider.calls
    assert TITRE_REFUS in appel["user"] and "CLAUDE.md" in appel["user"]


async def test_sans_refus_le_message_du_validateur_est_inchange() -> None:
    provider = FakeProvider(content=json.dumps(_VERDICT))
    service = ValidatorService(provider, Path("agents/prompts"))

    await service.validate(criteria=["c"], code_produced="diff", test_result=None)

    assert TITRE_REFUS not in provider.calls[0]["user"]
