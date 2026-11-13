"""A ticket that asks for a real proof stops at its PR (ticket-949)."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import frontmatter  # type: ignore[import-untyped]

from tessera.models.ticket import TicketStatus
from tessera.services.github.github_workflow import build_pr_body
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.noyau.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.pipeline import pipeline_livraison
from tessera.services.pipeline.pipeline_approbation import ARRET_PREUVE_REELLE, retenir_pour_preuve
from tessera.services.pipeline.pipeline_text import _extract_criteria
from tessera.services.projets.ticket_service import _ticket_from_post
from tessera.services.verdicts.validator import ValidatorService
from tests.test_providers_base import FakeProvider

_PREUVE = "Lancer le job sur la machine et constater la fin des processus."
_CORPS = (
    "## Objectif\n\nUn objectif.\n\n"
    "## Critères d'acceptation\n\n- [ ] Un test passe.\n\n"
    f"## Preuve réelle\n\n{_PREUVE}\n"
)


def _ticket(meta_extra: dict[str, Any], body: str = _CORPS) -> Any:
    meta: dict[str, Any] = {
        "id": "ticket-001",
        "title": "T",
        "type": "feat",
        "status": "todo",
        "priority": "medium",
        "agent": "codeur",
        **meta_extra,
    }
    path = Path("todo") / "ticket-001-t.md"
    return _ticket_from_post(frontmatter.Post(body, **meta), path, "p")


def test_preuve_reelle_is_loaded_from_the_frontmatter() -> None:
    assert _ticket({"preuve_reelle": True}).preuve_reelle is True


def test_preuve_reelle_defaults_to_false() -> None:
    assert _ticket({}).preuve_reelle is False


def test_validator_brief_does_not_contain_the_proof_section() -> None:
    service = ValidatorService(FakeProvider(), Path("agents/prompts"))
    message, _ = service._build_user_message(_extract_criteria(_CORPS), "diff", None)
    assert "Un test passe." in message
    assert _PREUVE not in message


def test_pr_body_copies_the_proof_section() -> None:
    assert _PREUVE in build_pr_body("ticket-001", "T", _CORPS)


def test_retenir_pour_preuve_keeps_an_opened_pr() -> None:
    retenue = retenir_pour_preuve(Livraison(pr_number=7), True)
    assert retenue.arret == ARRET_PREUVE_REELLE
    assert retenue.arret_voulu is True
    assert retenue.pr_orpheline is False


def test_retenir_pour_preuve_leaves_other_cases_unchanged() -> None:
    ouverte = Livraison(pr_number=7)
    sans_pr = Livraison(arret="Rebase refusé")
    assert retenir_pour_preuve(ouverte, False) == ouverte
    assert retenir_pour_preuve(sans_pr, True) == sans_pr


class _Tickets:
    def __init__(self, preuve_reelle: bool) -> None:
        self._ticket = SimpleNamespace(preuve_reelle=preuve_reelle)

    async def get_ticket(self, ticket_id: str) -> Any:
        return self._ticket


async def _livrer(preuve_reelle: bool, monkeypatch: Any) -> tuple[PipelineResult, list[int]]:
    surveilles: list[int] = []

    async def livrer(resultat: PipelineResult) -> Livraison:
        return Livraison(pr_number=7)

    async def surveiller(projet: str, ticket: str, pr: int, on_event: Any) -> None:
        surveilles.append(pr)

    async def finaliser(orch: Any, livraison: Livraison) -> None:
        return None

    async def on_event(event: OrchestratorEvent) -> None:
        return None

    monkeypatch.setattr(pipeline_livraison.fin_de_file, "finaliser_livraison", finaliser)
    orch = SimpleNamespace(
        _livrer=livrer,
        _surveiller=surveiller,
        _ticket_svc=_Tickets(preuve_reelle),
        _preuves_reelles={"ticket-001": preuve_reelle},
        _log=lambda ligne: None,
    )
    resultat = PipelineResult(
        ticket_id="ticket-001", final_status=TicketStatus.done, rounds=1, approved=True
    )
    rendu = await pipeline_livraison.livrer_le_resultat(orch, resultat, "p", on_event)  # type: ignore[arg-type]
    return rendu, surveilles


async def test_a_proof_ticket_opens_its_pr_without_the_automatic_merge(
    monkeypatch: Any,
) -> None:
    rendu, surveilles = await _livrer(True, monkeypatch)
    assert rendu.livraison is not None
    assert rendu.livraison.pr_number == 7
    assert rendu.livraison.arret == ARRET_PREUVE_REELLE
    assert rendu.livraison.arret_voulu is True
    assert surveilles == []


async def test_a_ticket_without_proof_is_delivered_as_before(monkeypatch: Any) -> None:
    rendu, surveilles = await _livrer(False, monkeypatch)
    assert rendu.livraison is not None
    assert rendu.livraison.arret is None
    assert surveilles == [7]
