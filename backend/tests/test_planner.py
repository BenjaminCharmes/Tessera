"""TDD tests for PlannerService — ticket-028."""
import json
import logging
from pathlib import Path

import pytest

from tessera.services.prompt_loader import MissingPromptError

from tests.test_providers_base import FakeProvider
from tessera.models.project import PlanResult
from tessera.models.ticket import TicketDraftPlan
from tessera.services.planner import PlannerService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_VALID_RESPONSE = json.dumps(
    {
        "tickets": [
            {
                "title": "Configurer OAuth Google (backend)",
                "type": "feat",
                "priority": "high",
                "agent": "codeur",
                "description": "Mettre en place le flow OAuth Google côté serveur.",
                "acceptance_criteria": ["Token Google validé", "Session créée"],
                "depends_on_index": [],
            },
            {
                "title": "Page de connexion Google (frontend)",
                "type": "feat",
                "priority": "high",
                "agent": "codeur",
                "description": "Bouton « Se connecter avec Google » sur la page de login.",
                "acceptance_criteria": ["Bouton visible", "Redirection OAuth OK"],
                "depends_on_index": [0],
            },
        ],
        "summary": "Auth OAuth Google en 2 tickets (backend + frontend)",
    }
)


def _make_service(tmp_path: Path, response_text: str) -> PlannerService:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "planificateur.md").write_text(
        "Tu es un expert en découpage de features.", encoding="utf-8"
    )
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    return PlannerService(
        provider=FakeProvider(content=response_text),
        prompts_dir=prompts_dir,
        workspace_dir=workspace_dir,
    )


def _make_service_with_project(tmp_path: Path, response_text: str) -> tuple[PlannerService, str]:
    """Returns (service, project_id) for a project that has a CLAUDE.md."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "planificateur.md").write_text(
        "Tu es un expert en découpage.", encoding="utf-8"
    )
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    project_id = "my-project"
    project_dir = workspace_dir / project_id
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text(
        "# My Project\n\n## Stack\n- Python, FastAPI\n", encoding="utf-8"
    )
    svc = PlannerService(
        provider=FakeProvider(content=response_text),
        prompts_dir=prompts_dir,
        workspace_dir=workspace_dir,
    )
    return svc, project_id


# ------------------------------------------------------------------
# plan() — résultat retourné
# ------------------------------------------------------------------


async def test_plan_returns_plan_result(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert isinstance(result, PlanResult)


async def test_plan_returns_correct_number_of_drafts(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert len(result.drafts) == 2


async def test_plan_returns_summary(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert "OAuth" in result.summary


async def test_plan_draft_has_correct_title(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert result.drafts[0].title == "Configurer OAuth Google (backend)"


async def test_plan_draft_has_acceptance_criteria(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert result.drafts[0].acceptance_criteria == ["Token Google validé", "Session créée"]


async def test_plan_draft_has_depends_on_index(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert result.drafts[1].depends_on_index == [0]


async def test_plan_first_draft_has_no_dependency(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("proj", "Ajouter OAuth Google")
    assert result.drafts[0].depends_on_index == []


# ------------------------------------------------------------------
# Chargement du CLAUDE.md
# ------------------------------------------------------------------


async def test_plan_includes_claude_md_in_user_message(tmp_path: Path) -> None:
    svc, project_id = _make_service_with_project(tmp_path, _VALID_RESPONSE)
    await svc.plan(project_id, "Ajouter OAuth Google")
    user_content = svc._provider.calls[0]["user"]
    assert "Python, FastAPI" in user_content


async def test_plan_includes_description_in_user_message(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.plan("proj", "Ajouter OAuth Google")
    user_content = svc._provider.calls[0]["user"]
    assert "Ajouter OAuth Google" in user_content


async def test_plan_works_without_claude_md(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.plan("nonexistent-project", "description")
    assert len(result.drafts) == 2


# ------------------------------------------------------------------
# Appel Anthropic
# ------------------------------------------------------------------


async def test_plan_calls_anthropic_with_system_prompt(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.plan("proj", "Ajouter OAuth Google")
    assert "Tu es un expert en découpage de features." in svc._provider.calls[0]["system"]


async def test_plan_calls_anthropic_with_user_role(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.plan("proj", "Ajouter OAuth Google")
    assert svc._provider.calls[0]["mode"] == "complete"


# ------------------------------------------------------------------
# Fallback sans fichier prompt
# ------------------------------------------------------------------


async def test_prompt_manquant_echoue_au_lieu_de_degrader(tmp_path: Path) -> None:
    # Le planificateur se repliait sur un prompt générique d'une ligne et
    # produisait des tickets hors sujet, sans autre signal qu'un WARNING
    # (ticket-051). Il doit désormais refuser net.
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    svc = PlannerService(
        provider=FakeProvider(content=_VALID_RESPONSE),
        prompts_dir=prompts_dir,
        workspace_dir=workspace_dir,
    )

    with pytest.raises(MissingPromptError) as exc:
        await svc.plan("proj", "description")

    assert "planificateur.md" in str(exc.value)
    assert "IDE_PROMPTS_DIR" in str(exc.value)


# ------------------------------------------------------------------
# JSON invalide → ValueError
# ------------------------------------------------------------------


async def test_invalid_json_raises_value_error(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, "Désolé, je ne peux pas planifier ça.")
    with pytest.raises(ValueError, match="JSON valide"):
        await svc.plan("proj", "description")


async def test_json_missing_tickets_raises_value_error(tmp_path: Path) -> None:
    bad_response = json.dumps({"summary": "test"})
    svc = _make_service(tmp_path, bad_response)
    with pytest.raises(ValueError, match="JSON valide"):
        await svc.plan("proj", "description")


async def test_illisible_logs_full_raw_response(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """An unreadable response is logged in full before the error is raised."""
    raw_response = "Désolé, voici quelque chose d'illisible — " + "x" * 500
    svc = _make_service(tmp_path, raw_response)
    with caplog.at_level(logging.WARNING, logger="tessera.services.planner"):
        with pytest.raises(ValueError, match="JSON valide"):
            await svc.plan("proj", "description")
    records = [r for r in caplog.records if r.getMessage() == "planner_reponse_illisible"]
    assert records, "Expected a 'planner_reponse_illisible' log record"
    assert records[0].__dict__.get("raw") == raw_response


async def test_json_in_markdown_code_block(tmp_path: Path) -> None:
    wrapped = f"Voici le plan :\n\n```json\n{_VALID_RESPONSE}\n```"
    svc = _make_service(tmp_path, wrapped)
    result = await svc.plan("proj", "description")
    assert len(result.drafts) == 2


# ------------------------------------------------------------------
# Validation des dépendances — self-reference
# ------------------------------------------------------------------


async def test_self_reference_raises_value_error(tmp_path: Path) -> None:
    response = json.dumps(
        {
            "tickets": [
                {
                    "title": "Ticket A",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "desc",
                    "acceptance_criteria": [],
                    "depends_on_index": [0],  # self-reference!
                }
            ],
            "summary": "test",
        }
    )
    svc = _make_service(tmp_path, response)
    with pytest.raises(ValueError, match="lui-même"):
        await svc.plan("proj", "description")


# ------------------------------------------------------------------
# Validation des dépendances — out-of-bounds
# ------------------------------------------------------------------


async def test_out_of_bounds_index_raises_value_error(tmp_path: Path) -> None:
    response = json.dumps(
        {
            "tickets": [
                {
                    "title": "Ticket A",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "desc",
                    "acceptance_criteria": [],
                    "depends_on_index": [5],  # index 5 n'existe pas
                }
            ],
            "summary": "test",
        }
    )
    svc = _make_service(tmp_path, response)
    with pytest.raises(ValueError, match="inexistant"):
        await svc.plan("proj", "description")


async def test_negative_index_raises_value_error(tmp_path: Path) -> None:
    response = json.dumps(
        {
            "tickets": [
                {
                    "title": "Ticket A",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "desc",
                    "acceptance_criteria": [],
                    "depends_on_index": [-1],
                }
            ],
            "summary": "test",
        }
    )
    svc = _make_service(tmp_path, response)
    with pytest.raises(ValueError, match="inexistant"):
        await svc.plan("proj", "description")


# ------------------------------------------------------------------
# Validation des dépendances — cycle
# ------------------------------------------------------------------


async def test_cyclic_dependency_raises_value_error(tmp_path: Path) -> None:
    response = json.dumps(
        {
            "tickets": [
                {
                    "title": "Ticket A",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "desc",
                    "acceptance_criteria": [],
                    "depends_on_index": [1],  # A dépend de B
                },
                {
                    "title": "Ticket B",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "desc",
                    "acceptance_criteria": [],
                    "depends_on_index": [0],  # B dépend de A → cycle!
                },
            ],
            "summary": "test",
        }
    )
    svc = _make_service(tmp_path, response)
    with pytest.raises(ValueError, match="cycle"):
        await svc.plan("proj", "description")


async def test_three_node_cycle_raises_value_error(tmp_path: Path) -> None:
    response = json.dumps(
        {
            "tickets": [
                {
                    "title": "A",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "",
                    "acceptance_criteria": [],
                    "depends_on_index": [2],  # A → C
                },
                {
                    "title": "B",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "",
                    "acceptance_criteria": [],
                    "depends_on_index": [0],  # B → A
                },
                {
                    "title": "C",
                    "type": "feat",
                    "priority": "medium",
                    "agent": "codeur",
                    "description": "",
                    "acceptance_criteria": [],
                    "depends_on_index": [1],  # C → B → cycle A→C→B→A
                },
            ],
            "summary": "test",
        }
    )
    svc = _make_service(tmp_path, response)
    with pytest.raises(ValueError, match="cycle"):
        await svc.plan("proj", "description")


# ------------------------------------------------------------------
# _has_cycle — tests unitaires
# ------------------------------------------------------------------


def test_has_cycle_false_for_empty(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    assert svc._has_cycle([]) is False


def test_has_cycle_false_for_linear_chain(tmp_path: Path) -> None:
    drafts = [
        TicketDraftPlan(
            title="A", type="feat", priority="medium", agent="codeur",
            description="", depends_on_index=[],
        ),
        TicketDraftPlan(
            title="B", type="feat", priority="medium", agent="codeur",
            description="", depends_on_index=[0],
        ),
        TicketDraftPlan(
            title="C", type="feat", priority="medium", agent="codeur",
            description="", depends_on_index=[1],
        ),
    ]
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    assert svc._has_cycle(drafts) is False


def test_has_cycle_true_for_two_node_cycle(tmp_path: Path) -> None:
    drafts = [
        TicketDraftPlan(
            title="A", type="feat", priority="medium", agent="codeur",
            description="", depends_on_index=[1],
        ),
        TicketDraftPlan(
            title="B", type="feat", priority="medium", agent="codeur",
            description="", depends_on_index=[0],
        ),
    ]
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    assert svc._has_cycle(drafts) is True
