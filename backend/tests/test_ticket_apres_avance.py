"""A run whose ticket is only on the remote base stops cleanly — ticket-923."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.services.pipeline.orchestrator import Orchestrator
from tessera.services.pipeline.ticket_apres_avance import lire_apres_avance


def _orchestrateur(refus: str | None, ticket_svc: MagicMock) -> tuple[Orchestrator, MagicMock]:
    git = MagicMock()
    git.restaurer_ticket_depuis_base = AsyncMock(return_value=False)
    git.sync_base_depuis_distant = AsyncMock(return_value=refus)
    git.retourner_sur_base = AsyncMock()
    git.create_branch = AsyncMock()
    orch = object.__new__(Orchestrator)
    orch._ticket_svc = ticket_svc
    orch._git_workspace = git
    orch._project_path = None
    orch._base_branch = "develop"
    return orch, git


@pytest.fixture(autouse=True)
def _sur_la_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tessera.services.pipeline.pipeline_fin_de_file.sur_la_base",
        AsyncMock(return_value=True),
    )


async def test_refused_fast_forward_with_missing_ticket_stops_without_branch() -> None:
    svc = MagicMock()
    svc.get_ticket = AsyncMock(return_value=None)
    svc.update_status = AsyncMock()
    orch, git = _orchestrateur("branche divergente", svc)

    resultat = await orch._run_pipeline("projet", "ticket-007", AsyncMock())

    assert not resultat.approved
    assert resultat.final_status.value == "blocked"
    assert resultat.branch is None
    assert resultat.arret is not None and "branche divergente" in resultat.arret
    git.create_branch.assert_not_called()
    svc.update_status.assert_not_called()
    git.sync_base_depuis_distant.assert_awaited_once_with("develop")


async def test_ticket_found_after_fast_forward_is_returned() -> None:
    svc = MagicMock()
    svc.get_ticket = AsyncMock(return_value="ticket")
    orch, _ = _orchestrateur(None, svc)

    assert await lire_apres_avance(orch, "ticket-007") == ("ticket", None)
