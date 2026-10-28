"""The validator over the Ollama double: schema sent as `format` — ticket-613 (ADR-061)."""
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from tessera.services.providers.ollama import OllamaProvider, _reset_cooldowns
from tessera.services.validator import ValidatorService
from tessera.services.validator_schema import VALIDATOR_SCHEMA

_BASE = "http://ollama.test:11434"


@pytest.fixture(autouse=True)
def _remise_a_zero() -> None:
    _reset_cooldowns()


def _mock_ollama(contenu: str, **plus: Any) -> respx.Route:
    tags = {"models": [{"name": "q"}]}
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=tags))
    corps = {
        "message": {"role": "assistant", "content": contenu},
        "done": True, "prompt_eval_count": 1, "eval_count": 1, **plus,
    }
    return respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(200, json=corps))


def _service() -> ValidatorService:
    return ValidatorService(OllamaProvider(_BASE), Path("prompts-absents"), model="q")


@respx.mock
async def test_the_request_carries_the_validator_schema_in_format() -> None:
    reponse = {"criteria": [{"index": 1, "passed": True, "note": ""}], "feedback": "ok"}
    route = _mock_ollama(json.dumps(reponse))

    result = await _service().validate(criteria=["A"], code_produced="code", test_result=None)

    assert json.loads(route.calls[0].request.content)["format"] == VALIDATOR_SCHEMA
    assert result.verdict == "APPROVED"
    assert result.criteria[0].passed is True


@respx.mock
async def test_a_failed_criterion_from_the_double_gives_changes_requested() -> None:
    reponse = {
        "criteria": [{"index": 1, "passed": False, "note": "absent"}], "feedback": "non",
    }
    _mock_ollama(json.dumps(reponse))

    result = await _service().validate(criteria=["A"], code_produced="code", test_result=None)

    assert result.verdict == "CHANGES_REQUESTED"
    assert result.criteria[0].note == "absent"


@respx.mock
async def test_a_criterion_judged_by_index_keeps_the_text_that_was_sent() -> None:
    # La sortie structurée n'exige que `index` : le texte vide du validateur
    # remplaçait celui du ticket, et le Bureau affichait « critère 1 » (ticket-662).
    reponse = {"criteria": [{"index": 1, "passed": True}, {"index": 2, "passed": False, "note": "manque"}], "feedback": ""}
    _mock_ollama(json.dumps(reponse))

    result = await _service().validate(
        criteria=["Le bouton existe", "Le test passe"], code_produced="code", test_result=None
    )

    assert [c.criterion for c in result.criteria] == ["Le bouton existe", "Le test passe"]
    assert result.criteria[1].note == "manque"


@respx.mock
@pytest.mark.parametrize(
    ("contenu", "plus"),
    [
        ('{"criteria": [{"index": 1, "pas', {}),
        ('{"criteria": [], "feedback": "ok"}', {"done_reason": "length"}),
        ("pas du json", {}),
    ],
)
async def test_a_truncated_or_unreadable_answer_gives_changes_requested(
    contenu: str, plus: dict[str, Any]
) -> None:
    _mock_ollama(contenu, **plus)

    result = await _service().validate(criteria=["A"], code_produced="code", test_result=None)

    assert result.verdict == "CHANGES_REQUESTED"
    assert "sortie structurée" in result.feedback
