"""Tests for the ticket context handed to the security audit (ticket-731)."""

import json
from pathlib import Path

from tests.test_providers_base import FakeProvider
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.verdicts.security_auditor import SecurityAuditorService
from tessera.services.verification.test_runner import TestResult
from tessera.services.verdicts.security_contexte import (
    NOT_DONE_MAX_CHARS,
    AuditContext,
    FollowingTicket,
    build_audit_context,
    describe_test_outcome,
    extract_not_done,
)

_PROMPTS = Path(__file__).resolve().parents[2] / "agents" / "prompts"
_BODY = (
    "## Objectif\nRendre les cartes propres à chaque joueur.\n\n"
    "## Ce que ça ne fait pas\n"
    "Les routes `/api/progress` et `/api/stats` relèvent du ticket-075.\n\n"
    "## Critères d'acceptation\n- [ ] ça marche\n"
)


def _ticket(ticket_id: str, title: str = "Titre", body: str = "", **kwargs: object) -> Ticket:
    base: dict[str, object] = dict(
        id=ticket_id,
        title=title,
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body=body,
    )
    base.update(kwargs)
    return Ticket(**base)  # type: ignore[arg-type]


class _Reader:
    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = {t.id: t for t in tickets}

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)


class _BrokenReader:
    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        raise OSError("disk")


def _critical_response() -> str:
    return json.dumps(
        {
            "verdict": "BLOCK",
            "summary": "Routes ouvertes.",
            "issues": [
                {
                    "severity": "CRITICAL",
                    "type": "Missing authorization",
                    "location": "routes.py:12",
                    "description": "annoncée par ticket-075",
                    "fix": "Filter by user",
                }
            ],
        }
    )


def test_extract_not_done_reads_the_section_up_to_the_next_heading() -> None:
    section = extract_not_done(_BODY)

    assert "ticket-075" in section
    assert "Critères" not in section
    assert "Objectif" not in section


def test_extract_not_done_is_empty_without_the_section() -> None:
    assert extract_not_done("## Objectif\nrien\n") == ""


def test_extract_not_done_is_capped() -> None:
    body = "## Ce que ça ne fait pas\n" + "x" * 5_000

    assert len(extract_not_done(body)) == NOT_DONE_MAX_CHARS


def test_render_is_empty_without_context() -> None:
    assert AuditContext().render() == ""


async def test_context_lists_the_tickets_behind_in_the_queue() -> None:
    reader = _Reader([_ticket("ticket-075", "Stats\npar joueur"), _ticket("ticket-076", "Autre")])

    context = await build_audit_context(
        _ticket("ticket-074", body=_BODY),
        ["ticket-073", "ticket-074", "ticket-075", "ticket-076"],
        reader,
    )

    assert context.following == (
        FollowingTicket("ticket-075", "Stats par joueur"),
        FollowingTicket("ticket-076", "Autre"),
    )


async def test_context_skips_a_finished_ticket_and_keeps_an_unreadable_one() -> None:
    reader = _Reader([_ticket("ticket-075", status=TicketStatus.done)])

    context = await build_audit_context(
        _ticket("ticket-074"), ["ticket-074", "ticket-075", "ticket-077"], reader
    )

    assert context.following == (FollowingTicket("ticket-077", ""),)


async def test_context_survives_a_reader_that_fails() -> None:
    context = await build_audit_context(
        _ticket("ticket-074"), ["ticket-074", "ticket-075"], _BrokenReader()
    )

    assert context.following == (FollowingTicket("ticket-075", ""),)


async def test_audit_message_carries_the_section_and_the_following_tickets(
    tmp_path: Path,
) -> None:
    provider = FakeProvider()
    provider.set_content(_critical_response())
    reader = _Reader([_ticket("ticket-075", "Progress and stats per player")])
    context = await build_audit_context(
        _ticket("ticket-074", body=_BODY), ["ticket-074", "ticket-075"], reader
    )

    await SecurityAuditorService(provider, _PROMPTS).audit("+x = 1", tmp_path, context)

    message = provider.calls[0]["user"]
    assert "relèvent du ticket-075" in message
    assert "ticket-075 — Progress and stats per player" in message
    assert message.index("Contexte du ticket") < message.index("## Code à auditer")


async def test_audit_message_outside_a_queue_has_no_following_tickets(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.set_content(_critical_response())
    context = await build_audit_context(_ticket("ticket-074", body=_BODY), None, None)

    await SecurityAuditorService(provider, _PROMPTS).audit("+x = 1", tmp_path, context)

    message = provider.calls[0]["user"]
    assert "relèvent du ticket-075" in message
    assert "Tickets qui suivent" not in message


async def test_audit_message_without_context_is_the_diff_alone(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.set_content(_critical_response())

    await SecurityAuditorService(provider, _PROMPTS).audit("+x = 1", tmp_path)

    assert provider.calls[0]["user"] == "## Code à auditer\n+x = 1"


async def test_a_critical_flaw_announced_by_a_following_ticket_still_blocks(
    tmp_path: Path,
) -> None:
    provider = FakeProvider()
    # Le LLM conclut PASS malgré la faille : le verdict reste BLOCK.
    provider.set_content(_critical_response().replace('"BLOCK"', '"PASS"'))
    context = AuditContext(
        not_done="Relève du ticket-075.",
        following=(FollowingTicket("ticket-075", "Stats"),),
    )

    result = await SecurityAuditorService(provider, _PROMPTS).audit("+x = 1", tmp_path, context)

    assert result.verdict == "BLOCK"
    assert result.has_critical is True
    assert "ticket-075" in result.issues[0].description


def test_the_prompts_carry_the_two_rules() -> None:
    # Les phrases des prompts sont coupées en lignes : on compare à blancs normalisés.
    securite = " ".join((_PROMPTS / "securite.md").read_text(encoding="utf-8").split())
    planificateur = " ".join((_PROMPTS / "planificateur.md").read_text(encoding="utf-8").split())

    assert "cite-le" in securite and "annoncée par ticket-075" in securite
    assert "faille atteignable entre deux tickets" in planificateur


def _tests(passed: bool, errors: list[str] | None = None) -> TestResult:
    return TestResult(
        passed=passed,
        total=12,
        failed=0 if passed else 2,
        output_summary="12 passed in 3s" if passed else "2 failed, 10 passed",
        errors=errors or [],
    )


async def test_context_carries_the_test_outcome_only_when_the_tester_ran() -> None:
    ticket = _ticket("ticket-074", body=_BODY)

    with_tests = await build_audit_context(ticket, None, None, _tests(True))
    without = await build_audit_context(ticket, None, None, None)

    assert "12 passed" in with_tests.tests
    assert without.tests == ""
    assert "Résultat des tests" not in without.render()


def test_describe_test_outcome_names_the_failures() -> None:
    assert describe_test_outcome(None) == ""
    text = describe_test_outcome(_tests(False, ["test_cp_moves", "test_rm_all"]))
    assert "rouges" in text and "- test_cp_moves" in text and "- test_rm_all" in text


async def test_audit_message_states_green_tests_as_a_fact(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.set_content(_critical_response())
    context = await build_audit_context(_ticket("ticket-074"), None, None, _tests(True))

    await SecurityAuditorService(provider, _PROMPTS).audit("+x = 1", tmp_path, context)

    message = provider.calls[0]["user"]
    assert "Les tests de ce tour sont verts : 12 passed in 3s" in message


async def test_audit_message_lists_the_failing_tests(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.set_content(_critical_response())
    context = await build_audit_context(
        _ticket("ticket-074"), None, None, _tests(False, ["test_cp_moves"])
    )

    await SecurityAuditorService(provider, _PROMPTS).audit("+x = 1", tmp_path, context)

    message = provider.calls[0]["user"]
    assert "rouges" in message and "test_cp_moves" in message


def test_the_security_prompt_ties_runtime_claims_to_the_test_result() -> None:
    securite = " ".join((_PROMPTS / "securite.md").read_text(encoding="utf-8").split())

    assert "échec à l'exécution" in securite and "s'accorder avec ce résultat" in securite
