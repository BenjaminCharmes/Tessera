"""Tests for the CI watch resumed at startup — ticket-510."""

import json
from pathlib import Path

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.database import create_run, init_db
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.politique_run import PolitiqueRun
from tessera.services.reprise_surveillance import (
    SurveillanceProjet,
    reprendre_surveillances,
)
from tessera.services.sha_approbation import noter_poussee
from tessera.services.ticket_service import TicketService

PROJET = "demo"


async def _sans_evenement(event: OrchestratorEvent) -> None:
    """Event callback that drops everything."""


class Espion:
    """Fake GitHub side: a state per PR, and a record of the PR handed over."""

    def __init__(self, etats: dict[int, str | Exception]) -> None:
        self.etats = etats
        self.surveillees: list[tuple[str, str, int]] = []
        self.fabriques: list[str] = []

    def fabrique(self, project_id: str, politique: PolitiqueRun) -> SurveillanceProjet:
        self.fabriques.append(project_id)

        async def etat_pr(pr: int) -> str:
            etat = self.etats[pr]
            if isinstance(etat, Exception):
                raise etat
            return etat

        async def surveiller(p_id: str, t_id: str, pr: int, _on_event: object) -> None:
            self.surveillees.append((p_id, t_id, pr))

        return SurveillanceProjet(etat_pr=etat_pr, surveiller=surveiller)


def _ecrire_ticket(projet: Path, ticket_id: str, pr: int) -> None:
    dossier = projet / "tickets" / "in-review"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{ticket_id}-sujet.md").write_text(
        "---\n"
        f"id: {ticket_id}\n"
        "title: Un ticket\n"
        "type: feat\n"
        "status: in-review\n"
        "priority: medium\n"
        "agent: codeur\n"
        f"pr_number: {pr}\n"
        "---\n\nCorps.\n",
        encoding="utf-8",
    )


async def _base(
    tmp_path: Path, autonomy: str = "merge", pousse: tuple[str, ...] = ("ticket-901",)
) -> tuple[Path, Path, Path]:
    """A workspace with one project, its DB, and a pushed commit per `pousse` ticket."""
    workspace = tmp_path / "ws"
    projet = workspace / PROJET
    projet.mkdir(parents=True)
    (projet / "agents.json").write_text(json.dumps({"autonomy": autonomy}), encoding="utf-8")
    db = tmp_path / "ide.db"
    await init_db(db)
    for ticket_id in pousse:
        run_id = await create_run(db, PROJET, ticket_id)
        await noter_poussee(db, run_id, "a" * 40)
    return workspace, projet, db


def _log(projet: Path) -> str:
    chemin = projet / "memory" / "pipeline-log.md"
    return chemin.read_text(encoding="utf-8") if chemin.exists() else ""


async def test_open_pr_is_handed_back_to_the_watcher(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_ticket(projet, "ticket-901", 7)
    espion = Espion({7: "open"})

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == [(PROJET, "ticket-901", 7)]
    assert f"[{PROJET}] ticket-901 PR #7 reprise par le CIWatcher après redémarrage" in _log(projet)


async def test_merged_pr_moves_the_ticket_to_done_without_watching(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_ticket(projet, "ticket-901", 7)
    espion = Espion({7: "merged"})

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    ticket = await TicketService(projet, PROJET).get_ticket("ticket-901")
    assert ticket is not None and ticket.status is TicketStatus.done
    assert espion.surveillees == []


@pytest.mark.parametrize("autonomy", ["commit", "pr"])
async def test_project_below_merge_autonomy_is_never_resumed(
    tmp_path: Path, autonomy: str
) -> None:
    workspace, projet, db = await _base(tmp_path, autonomy=autonomy)
    _ecrire_ticket(projet, "ticket-901", 7)
    espion = Espion({7: "open"})

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == []
    assert espion.fabriques == []
    assert _log(projet) == ""


async def test_closed_pr_is_not_resumed_and_is_logged(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_ticket(projet, "ticket-901", 7)
    espion = Espion({7: "closed"})

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == []
    assert "ticket-901 PR #7 fermée sans merge" in _log(projet)
    ticket = await TicketService(projet, PROJET).get_ticket("ticket-901")
    assert ticket is not None and ticket.status is TicketStatus.in_review


async def test_github_error_is_logged_and_the_other_pr_is_still_resumed(
    tmp_path: Path,
) -> None:
    workspace, projet, db = await _base(tmp_path, pousse=("ticket-901", "ticket-902"))
    _ecrire_ticket(projet, "ticket-901", 7)
    _ecrire_ticket(projet, "ticket-902", 8)
    espion = Espion({7: RuntimeError("GitHub injoignable"), 8: "open"})

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == [(PROJET, "ticket-902", 8)]


async def test_failing_factory_does_not_raise(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_ticket(projet, "ticket-901", 7)

    def fabrique_cassee(project_id: str, politique: PolitiqueRun) -> SurveillanceProjet:
        raise OSError("dépôt illisible")

    await reprendre_surveillances(workspace, db, fabrique_cassee, _sans_evenement)


async def test_open_pr_without_pushed_commit_is_not_resumed(tmp_path: Path) -> None:
    # Pas de commit poussé noté : la signature d'une PR de résolution de conflit.
    workspace, projet, db = await _base(tmp_path, pousse=())
    _ecrire_ticket(projet, "ticket-901", 7)
    espion = Espion({7: "open"})

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == []
    assert "ticket-901 PR #7 non reprise" in _log(projet)


async def test_missing_workspace_is_a_no_op(tmp_path: Path) -> None:
    espion = Espion({})

    await reprendre_surveillances(
        tmp_path / "absent", tmp_path / "ide.db", espion.fabrique, _sans_evenement
    )

    assert espion.fabriques == []


async def test_startup_helper_swallows_a_resume_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tessera import main

    async def echoue(*_args: object) -> None:
        raise RuntimeError("boum")

    monkeypatch.setattr(main, "reprendre_surveillances", echoue)

    await main._reprendre_les_surveillances()
