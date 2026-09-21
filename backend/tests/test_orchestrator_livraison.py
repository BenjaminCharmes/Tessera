"""La livraison suit chaque run, quel que soit le mode — ticket-084."""
from pathlib import Path
from typing import Any

from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.models.ticket import TicketStatus


def _resultat(ticket_id: str, approuve: bool = True) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done if approuve else TicketStatus.blocked,
        rounds=1,
        approved=approuve,
        branch=f"{ticket_id}-slug",
        commit_sha="abc",
    )


class _OrchestrateurDouble(Orchestrator):
    """Orchestrateur dont seul le pipeline interne est doublé.

    Le reste — l'enchaînement de la file, et la livraison qu'on teste ici —
    est le vrai code.
    """

    def __init__(self, resultats: list[PipelineResult], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultats = list(resultats)

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultats.pop(0)


def _construire(
    tmp_path: Path, resultats: list[PipelineResult], livrer: Any
) -> _OrchestrateurDouble:
    from unittest.mock import AsyncMock, MagicMock

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None
    return _OrchestrateurDouble(
        resultats,
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=livrer,
    )


async def test_la_livraison_suit_chaque_ticket_d_une_file(tmp_path: Path) -> None:
    # La livraison n'était branchée que sur le run unique : une file de dix
    # tickets n'en livrait aucun, alors que c'est le mode où l'absence de
    # clic compte le plus.
    livres: list[str] = []

    async def _livrer(resultat: PipelineResult) -> Livraison:
        livres.append(resultat.ticket_id)
        return Livraison(pr_number=7, merged=True)

    orch = _construire(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
    )

    resultats = await orch.run_queue("p", ["ticket-001", "ticket-002"])

    assert livres == ["ticket-001", "ticket-002"]
    assert all(r.livraison is not None and r.livraison.merged for r in resultats)


async def test_un_ticket_non_approuve_n_est_pas_livre(tmp_path: Path) -> None:
    livres: list[str] = []

    async def _livrer(resultat: PipelineResult) -> Livraison:
        livres.append(resultat.ticket_id)
        return Livraison()

    orch = _construire(tmp_path, [_resultat("ticket-001", approuve=False)], _livrer)

    await orch.run_pipeline("p", "ticket-001", _rien)

    assert livres == []


async def test_la_livraison_est_annoncee_sur_le_flux(tmp_path: Path) -> None:
    async def _livrer(resultat: PipelineResult) -> Livraison:
        return Livraison(etapes=("PR #7 ouverte",), pr_number=7)

    orch = _construire(tmp_path, [_resultat("ticket-001")], _livrer)
    recus: list[OrchestratorEvent] = []

    async def _capter(event: OrchestratorEvent) -> None:
        recus.append(event)

    await orch.run_pipeline("p", "ticket-001", _capter)

    livraison = [e for e in recus if e.type is EventType.LIVRAISON_DONE]
    assert len(livraison) == 1
    assert livraison[0].data["pr_number"] == 7


async def test_sans_livreur_le_run_est_rendu_tel_quel(tmp_path: Path) -> None:
    # Un orchestrateur construit sans livreur — appel programmatique, test —
    # ne doit pas changer de comportement.
    orch = _construire(tmp_path, [_resultat("ticket-001")], None)

    resultat = await orch.run_pipeline("p", "ticket-001", _rien)

    assert resultat.livraison is None


async def _rien(event: OrchestratorEvent) -> None:
    return None


# ------------------------------------------------------------------
# La documentation se met à jour une fois par lot — ticket-092
# ------------------------------------------------------------------


async def test_la_doc_se_met_a_jour_une_fois_apres_la_file(tmp_path: Path) -> None:
    # Le cœur du ticket : dix tickets ne déclenchent pas dix mises à jour.
    # La documentation décrit le produit, pas un changement.
    appels: list[int] = []

    async def _documenter() -> None:
        appels.append(1)

    orch = _construire(
        tmp_path,
        [_resultat(f"ticket-{n:03d}") for n in range(1, 4)],
        None,
    )
    orch._documenter = _documenter  # type: ignore[assignment]

    await orch.run_queue("p", ["ticket-001", "ticket-002", "ticket-003"])

    assert appels == [1]


async def test_un_run_unique_ne_declenche_pas_la_doc(tmp_path: Path) -> None:
    # Un ticket lancé seul, c'est un aller-retour rapide pendant qu'on
    # travaille : y ajouter un appel de documentation le ralentit sans que
    # personne l'ait demandé.
    appels: list[int] = []

    async def _documenter() -> None:
        appels.append(1)

    orch = _construire(tmp_path, [_resultat("ticket-001")], None)
    orch._documenter = _documenter  # type: ignore[assignment]

    await orch.run_pipeline("p", "ticket-001", _rien)

    assert appels == []


async def test_une_doc_qui_echoue_ne_casse_pas_la_file(tmp_path: Path) -> None:
    async def _documenter() -> None:
        raise RuntimeError("provider injoignable")

    orch = _construire(tmp_path, [_resultat("ticket-001")], None)
    orch._documenter = _documenter  # type: ignore[assignment]

    resultats = await orch.run_queue("p", ["ticket-001"])

    assert len(resultats) == 1
