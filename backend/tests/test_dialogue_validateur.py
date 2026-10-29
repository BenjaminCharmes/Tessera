"""The validator knows the human answers given during the run — ticket-537."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.services.dialogue import DialogueChannel, DialogueExchange
from tessera.services.orchestrator import Orchestrator
from tessera.services.validator import ValidatorService
from tessera.services.validator_decisions import DECISIONS_SECTION_TITLE, validator_extras
from tests.test_orchestrator import _FakeGit, _make_agent_result, _make_ticket, _noop
from tests.test_providers_base import FakeProvider

_VERDICT = {
    "criteria": [{"index": 1, "criterion": "c", "passed": True, "note": ""}],
    "feedback": "ok",
}
_PROMPTS = Path("agents/prompts")


async def _poser_et_repondre(canal: DialogueChannel, question: str, reponse: str) -> str:
    tache = asyncio.create_task(canal.ask(question))
    await canal.wait_for_question()
    canal.answer(reponse)
    return await tache


async def test_the_channel_keeps_each_question_with_its_human_answer_in_order() -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)

    await _poser_et_repondre(canal, "404 ou état vide ?", "B")
    await _poser_et_repondre(canal, "Quel nom ?", "slug")

    assert canal.exchanges == [
        DialogueExchange("404 ou état vide ?", "B"),
        DialogueExchange("Quel nom ?", "slug"),
    ]


async def test_an_unanswered_question_is_not_in_the_exchanges() -> None:
    canal = DialogueChannel(timeout_s=0.01, interactive=True)

    await canal.ask("Quel format ?")

    assert canal.exchanges == []


async def test_autonomous_and_stopped_channels_record_nothing() -> None:
    autonome = DialogueChannel(interactive=False)
    await autonome.ask("Quel format ?")
    arrete = DialogueChannel(timeout_s=5.0, interactive=True)
    arrete.request_stop()
    await arrete.ask("Quel format ?")

    assert autonome.exchanges == [] and arrete.exchanges == []


def test_a_late_answer_without_question_is_not_an_exchange() -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)

    canal.answer("réponse tardive")

    assert canal.exchanges == []


def test_the_message_has_the_decisions_section_only_with_exchanges() -> None:
    service = ValidatorService(FakeProvider(content="{}"), _PROMPTS)
    echanges = [DialogueExchange("404 ou état vide ?", "B")]

    avec, _ = service._build_user_message(["c"], "diff", None, exchanges=echanges)
    sans, _ = service._build_user_message(["c"], "diff", None)

    assert DECISIONS_SECTION_TITLE in avec
    assert "404 ou état vide ?" in avec and "Réponse : B" in avec
    # La section suit les critères et précède le code.
    assert avec.index("## Critères") < avec.index(DECISIONS_SECTION_TITLE) < avec.index("## Code produit")
    assert DECISIONS_SECTION_TITLE not in sans


async def test_validator_extras_carry_only_what_exists() -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)
    assert validator_extras("", canal) == {}

    await _poser_et_repondre(canal, "404 ou état vide ?", "B")

    assert validator_extras("refus", canal) == {
        "refus": "refus",
        "exchanges": [DialogueExchange("404 ou état vide ?", "B")],
    }


class _CodeurQuiDemande:
    """Le codeur pose une question au tour 1 ; l'utilisateur répond B."""

    def __init__(self, canal: DialogueChannel) -> None:
        self._canal = canal

    async def run(self, **kwargs: object) -> AgentResult:
        role = kwargs["role"]
        assert isinstance(role, AgentRole)
        if role == AgentRole.reviewer:
            return _make_agent_result("APPROVED", role=role)
        await _poser_et_repondre(self._canal, "404 ou état vide ?", "B")
        return _make_agent_result("prose du codeur", role=role)


async def test_the_orchestrator_hands_the_run_dialogue_to_the_validator(tmp_path: Path) -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)
    provider = FakeProvider(content=json.dumps(_VERDICT))
    service = AsyncMock()
    service.get_ticket.return_value = _make_ticket(
        body="## Critères d'acceptation\n- [ ] ça marche\n"
    )
    orch = Orchestrator(
        runner=_CodeurQuiDemande(canal), ticket_service=service, project_context="ctx",  # type: ignore[arg-type]
        agent_configs=[], pipeline_log_path=tmp_path / "memory" / "pipeline-log.md",
        validator=ValidatorService(provider, _PROMPTS), git_workspace=_FakeGit(),  # type: ignore[arg-type]
    )

    await orch.run_pipeline("projet", "ticket-001", _noop, dialogue=canal)

    (appel,) = provider.calls
    assert DECISIONS_SECTION_TITLE in appel["user"]
    assert "404 ou état vide ?" in appel["user"] and "Réponse : B" in appel["user"]


def test_the_validator_prompt_judges_a_changed_criterion_against_the_answer() -> None:
    brut = (Path(__file__).parents[2] / "agents" / "prompts" / "validateur.md").read_text(
        encoding="utf-8"
    )
    # Les retours à la ligne du prompt ne doivent pas casser la recherche.
    prompt = " ".join(brut.split())

    assert DECISIONS_SECTION_TITLE in prompt
    assert "se juge contre cette réponse" in prompt
