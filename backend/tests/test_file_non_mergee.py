"""La file ne s'empile pas sur un ticket non mergé — ticket-302."""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import PipelineResult
from tessera.services.politique_run import PolitiqueRun
from tessera.routers.orchestrator import _sync_apres_livraison


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _resultat(ticket_id: str, livraison: Livraison | None = None) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        branch=f"{ticket_id}-slug",
        commit_sha="abc",
        livraison=livraison,
    )


def _ticket(ticket_id: str, depends_on: list[str] | None = None) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"Ticket {ticket_id}",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        depends_on=depends_on or [],
    )


class _OrchestrateurDouble(Orchestrator):
    """Orchestrateur dont seul le pipeline interne est doublé."""

    def __init__(self, resultats: list[PipelineResult], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultats_file = list(resultats)

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultats_file.pop(0)


def _construire(
    tmp_path: Path,
    resultats: list[PipelineResult],
    tickets: dict[str, Ticket],
) -> _OrchestrateurDouble:
    svc = AsyncMock()
    svc.get_ticket = AsyncMock(side_effect=lambda tid: tickets.get(tid))
    return _OrchestrateurDouble(
        resultats,
        runner=MagicMock(),
        ticket_service=svc,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
    )


# ------------------------------------------------------------------
# _sync_apres_livraison — critères 1, 3, 4
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_appele_apres_livraison_non_mergee_sur_projet_merge() -> None:
    """Critère 1 : merged=False + autonomy=merge → sync_base_depuis_distant appelé."""
    politique = PolitiqueRun(autonomy=NiveauAutonomie.merge, base_branch="develop")
    espace = MagicMock()
    espace.sync_base_depuis_distant = AsyncMock(return_value=None)
    livraison = Livraison(merged=False, pr_number=5, etapes=("PR #5 ouverte",))

    await _sync_apres_livraison(livraison, espace, politique, "develop")

    espace.sync_base_depuis_distant.assert_awaited_once_with("develop")


@pytest.mark.asyncio
async def test_sync_appele_apres_livraison_mergee() -> None:
    """Critère 3 : merged=True → sync_base_depuis_distant appelé (ticket-285 inchangé)."""
    politique = PolitiqueRun(autonomy=NiveauAutonomie.merge, base_branch="develop")
    espace = MagicMock()
    espace.sync_base_depuis_distant = AsyncMock(return_value=None)
    livraison = Livraison(merged=True, pr_number=5, etapes=("mergé",))

    await _sync_apres_livraison(livraison, espace, politique, "develop")

    espace.sync_base_depuis_distant.assert_awaited_once_with("develop")


@pytest.mark.asyncio
async def test_sync_non_appele_sur_projet_commit() -> None:
    """Critère 4 : autonomy=commit → empilement voulu, sync_base_depuis_distant non appelé."""
    politique = PolitiqueRun(autonomy=NiveauAutonomie.commit, base_branch="develop")
    espace = MagicMock()
    espace.sync_base_depuis_distant = AsyncMock(return_value=None)
    livraison = Livraison(merged=False, pr_number=5)

    await _sync_apres_livraison(livraison, espace, politique, "develop")

    espace.sync_base_depuis_distant.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_preserve_la_livraison_en_cas_d_erreur_distante() -> None:
    """Si sync échoue, la raison est dans livraison.arret et durees_ms est préservé."""
    politique = PolitiqueRun(autonomy=NiveauAutonomie.merge, base_branch="develop")
    espace = MagicMock()
    espace.sync_base_depuis_distant = AsyncMock(return_value="fetch échoué")
    livraison = Livraison(
        merged=False, pr_number=5, etapes=("PR #5 ouverte",), durees_ms=(120.0,)
    )

    resultat = await _sync_apres_livraison(livraison, espace, politique, "develop")

    assert resultat.arret == "fetch échoué"
    assert resultat.durees_ms == (120.0,)
    assert resultat.pr_number == 5


# ------------------------------------------------------------------
# run_queue — critère 2
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_file_s_arrete_si_ticket_suivant_depend_du_ticket_non_merge(
    tmp_path: Path,
) -> None:
    """Critère 2 : depends_on sur un ticket non mergé arrête la file avec un arret."""
    livraison_non_mergee = Livraison(
        merged=False, pr_number=42, etapes=("PR #42 ouverte",)
    )
    tickets = {
        "ticket-001": _ticket("ticket-001"),
        "ticket-002": _ticket("ticket-002", depends_on=["ticket-001"]),
    }
    orch = _construire(
        tmp_path,
        [_resultat("ticket-001", livraison=livraison_non_mergee)],
        tickets,
    )

    resultats = await orch.run_queue("projet", ["ticket-001", "ticket-002"])

    # La file s'arrête après ticket-001 — ticket-002 n'est pas lancé.
    assert len(resultats) == 1
    livraison = resultats[0].livraison
    assert livraison is not None
    assert livraison.arret is not None
    assert "42" in livraison.arret
    assert "ticket-002" in livraison.arret
    assert "ticket-001" in livraison.arret


@pytest.mark.asyncio
async def test_file_continue_sans_dependance_meme_sur_ticket_non_merge(
    tmp_path: Path,
) -> None:
    """Sans depends_on, la file continue même si le ticket précédent n'a pas mergé."""
    livraison_non_mergee = Livraison(merged=False, pr_number=42)
    livraison_ok = Livraison(merged=True, pr_number=43)
    tickets = {
        "ticket-001": _ticket("ticket-001"),
        "ticket-002": _ticket("ticket-002"),  # pas de depends_on
    }
    orch = _construire(
        tmp_path,
        [
            _resultat("ticket-001", livraison=livraison_non_mergee),
            _resultat("ticket-002", livraison=livraison_ok),
        ],
        tickets,
    )

    resultats = await orch.run_queue("projet", ["ticket-001", "ticket-002"])

    assert len(resultats) == 2
    assert resultats[1].livraison is not None
    assert resultats[1].livraison.merged is True
