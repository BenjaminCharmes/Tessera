"""Tests for the resume from open GitHub PRs — ticket-516."""

import json
from pathlib import Path

import httpx
import respx

from tessera.services.database import create_run, init_db
from tessera.services.github_service import GitHubService, PrOuverte
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.politique_run import PolitiqueRun
from tessera.services.reprise_outils import prs_a_reprendre, ticket_de_branche
from tessera.services.reprise_surveillance import (
    SurveillanceProjet,
    reprendre_surveillances,
)
from tessera.services.sha_approbation import noter_poussee

PROJET = "demo"
BASE = "develop"
_API = "https://api.github.com"
_REPO = "owner/demo"


async def _sans_evenement(event: OrchestratorEvent) -> None:
    """Event callback that drops everything."""


class FauxGitHub:
    """Fake GitHub side: the open PRs listed, and the PRs handed to the watcher."""

    def __init__(self, ouvertes: list[PrOuverte], etats: dict[int, str] | None = None) -> None:
        self.ouvertes = ouvertes
        self.etats = etats or {}
        self.surveillees: list[tuple[str, str, int]] = []

    def fabrique(self, project_id: str, politique: PolitiqueRun) -> SurveillanceProjet:
        async def etat_pr(pr: int) -> str:
            return self.etats.get(pr, "open")

        async def surveiller(p_id: str, t_id: str, pr: int, _on_event: object) -> None:
            self.surveillees.append((p_id, t_id, pr))

        async def prs_ouvertes() -> list[PrOuverte]:
            return self.ouvertes

        return SurveillanceProjet(
            etat_pr=etat_pr,
            surveiller=surveiller,
            prs_ouvertes=prs_ouvertes,
            base_branch=BASE,
        )


async def _base(tmp_path: Path, pousse: tuple[str, ...] = ("ticket-034",)) -> tuple[Path, Path, Path]:
    workspace = tmp_path / "ws"
    projet = workspace / PROJET
    projet.mkdir(parents=True)
    (projet / "agents.json").write_text(json.dumps({"autonomy": "merge"}), encoding="utf-8")
    db = tmp_path / "ide.db"
    await init_db(db)
    for ticket_id in pousse:
        run_id = await create_run(db, PROJET, ticket_id)
        await noter_poussee(db, run_id, "a" * 40)
    return workspace, projet, db


def _ecrire_fiche(projet: Path, dossier: str, ticket_id: str, pr: int | None) -> None:
    cible = projet / "tickets" / dossier
    cible.mkdir(parents=True, exist_ok=True)
    pr_ligne = f"pr_number: {pr}\n" if pr is not None else ""
    (cible / f"{ticket_id}-sujet.md").write_text(
        f"---\nid: {ticket_id}\ntitle: Un ticket\ntype: feat\nstatus: {dossier}\n"
        f"priority: medium\nagent: codeur\n{pr_ligne}---\n\nCorps.\n",
        encoding="utf-8",
    )


async def test_open_pr_is_resumed_when_the_local_card_is_todo(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_fiche(projet, "todo", "ticket-034", None)
    github = FauxGitHub([PrOuverte(41, "ticket-034-une-feature", BASE)])

    await reprendre_surveillances(workspace, db, github.fabrique, _sans_evenement)

    assert github.surveillees == [(PROJET, "ticket-034", 41)]


async def test_pr_whose_branch_is_not_a_ticket_branch_is_not_resumed(tmp_path: Path) -> None:
    workspace, _projet, db = await _base(tmp_path)
    github = FauxGitHub([
        PrOuverte(41, "feature/une-idee", BASE),
        PrOuverte(42, "ticket-sans-numero", BASE),
        PrOuverte(43, "fix-ticket-034-x", BASE),
    ])

    await reprendre_surveillances(workspace, db, github.fabrique, _sans_evenement)

    assert github.surveillees == []


async def test_pr_toward_another_base_is_not_resumed(tmp_path: Path) -> None:
    workspace, _projet, db = await _base(tmp_path)
    github = FauxGitHub([PrOuverte(41, "ticket-034-une-feature", "main")])

    await reprendre_surveillances(workspace, db, github.fabrique, _sans_evenement)

    assert github.surveillees == []


async def test_pr_found_by_both_sources_is_handed_over_once(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_fiche(projet, "in-review", "ticket-034", 41)
    github = FauxGitHub([PrOuverte(41, "ticket-034-une-feature", BASE)])

    await reprendre_surveillances(workspace, db, github.fabrique, _sans_evenement)

    assert github.surveillees == [(PROJET, "ticket-034", 41)]


async def test_github_pr_without_pushed_commit_is_not_resumed(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path, pousse=())
    github = FauxGitHub([PrOuverte(41, "ticket-034-une-feature", BASE)])

    await reprendre_surveillances(workspace, db, github.fabrique, _sans_evenement)

    assert github.surveillees == []
    log = (projet / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "ticket-034 PR #41 non reprise" in log


async def test_failing_listing_still_resumes_the_local_cards(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path)
    _ecrire_fiche(projet, "in-review", "ticket-034", 41)
    github = FauxGitHub([])
    base_fabrique = github.fabrique

    def fabrique(project_id: str, politique: PolitiqueRun) -> SurveillanceProjet:
        surveillance = base_fabrique(project_id, politique)

        async def casse() -> list[PrOuverte]:
            raise RuntimeError("GitHub injoignable")

        return SurveillanceProjet(
            etat_pr=surveillance.etat_pr,
            surveiller=surveillance.surveiller,
            prs_ouvertes=casse,
            base_branch=BASE,
        )

    await reprendre_surveillances(workspace, db, fabrique, _sans_evenement)

    assert github.surveillees == [(PROJET, "ticket-034", 41)]


def test_ticket_de_branche_extracts_the_id_with_its_dash() -> None:
    assert ticket_de_branche("ticket-034-une-feature") == "ticket-034"
    assert ticket_de_branche("ticket-034") is None
    assert ticket_de_branche("chat-2026") is None


def test_prs_a_reprendre_keeps_nothing_without_a_base() -> None:
    assert prs_a_reprendre([PrOuverte(1, "ticket-001-x", BASE)], None) == []


@respx.mock
async def test_find_open_pull_requests_reads_open_prs_of_the_base() -> None:
    route = respx.get(f"{_API}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[
            {"number": 41, "head": {"ref": "ticket-034-x"}, "base": {"ref": BASE}},
            {"number": 42, "head": {"ref": "ticket-035-x"}, "base": {"ref": "main"}},
        ])
    )

    trouvees = await GitHubService(token="t", repo=_REPO).find_open_pull_requests(BASE)

    assert trouvees == [PrOuverte(41, "ticket-034-x", BASE)]
    params = route.calls.last.request.url.params
    assert params["state"] == "open" and params["base"] == BASE
