"""A failed worktree setup tidies up behind itself — ticket-579 (ADR-037, ADR-056).

Real repository with a local origin; no model is called, the setup is a double
that fails the way a timed-out install does. The run must end `blocked` with its
bookkeeping committed, its worktree removed, and the ticket must be relaunchable.
"""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.models.ticket import TicketStatus
from tessera.services.assemblage_run import build_orchestrator
from tessera.services.database import init_db
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.politique_run import PolitiqueRun
from tessera.services.preparation_worktree import ResultatPreparation
from tessera.services.run_dans_worktree import ouvrir_worktree
from tessera.services.run_worktree import RunWorktree
from tests.depot_worktree import construire, git

PROJET = "checkout"
TICKET = "ticket-7"
COMMANDE = "corepack pnpm@10 install --frozen-lockfile"
DECLARATION = {
    "autonomy": "pr",
    "artifacts": "tracked",
    "base_branch": "develop",
    "worktree": {"setup": COMMANDE},
}
FICHE = "\n".join([
    "---", "id: ticket-7", 'title: "demo"', "type: feat", "status: todo",
    "priority: medium", "agent: codeur", "---", "", "# ticket-7", "",
])


@pytest.fixture
async def depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = construire(tmp_path, monkeypatch)
    (repo / "agents.json").write_text(json.dumps(DECLARATION), encoding="utf-8")
    (repo / "CLAUDE.md").write_text("# Projet\n", encoding="utf-8")
    fiche = repo / "tickets" / "todo" / "ticket-7-demo.md"
    fiche.parent.mkdir(parents=True)
    fiche.write_text(FICHE, encoding="utf-8")
    git(repo, "add", "tickets")
    git(repo, "commit", "-m", "add ticket")
    git(repo, "push", "origin", "develop")
    monkeypatch.setattr(settings, "ide_workspace_dir", repo.parent)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "ide_db_path", tmp_path / "ide.db")
    await init_db(tmp_path / "ide.db")
    return repo


async def _evenement(_: OrchestratorEvent) -> None:
    return None


async def _run_qui_echoue(depot: Path) -> tuple[PipelineResult, RunWorktree]:
    ouvert = await ouvrir_worktree(depot, PROJET, TICKET, "demo", PolitiqueRun.lire(depot))
    assert ouvert is not None
    wt, absents = ouvert
    orch: Orchestrator = await build_orchestrator(PROJET, wt, tuple(absents))

    async def preparation_coupee() -> ResultatPreparation:
        arret = f"La préparation du worktree a échoué : `{COMMANDE}` — délai dépassé"
        return ResultatPreparation(COMMANDE, 420_000, None, arret)

    orch._preparation = preparation_coupee
    return await orch.run_pipeline(PROJET, TICKET, _evenement), wt


async def test_a_failed_setup_closes_the_run_blocked_with_its_bookkeeping_committed(
    depot: Path,
) -> None:
    resultat, wt = await _run_qui_echoue(depot)

    assert resultat.final_status is TicketStatus.blocked and not resultat.approved
    assert resultat.branch == wt.branche and resultat.arret is not None
    # Rien n'a été écrit hors du rangement : `commit_all` ne crée alors que le
    # commit de rangement (pas de commit « unapproved work » sans diff).
    sujet = git(depot, "log", "-1", "--format=%s", wt.branche)
    assert sujet == "chore: tessera pipeline bookkeeping"
    assert git(depot, "rev-parse", wt.branche) != git(depot, "rev-parse", "origin/develop")


async def test_the_unapproved_commit_names_the_setup_when_there_is_a_diff(
    depot: Path,
) -> None:
    ouvert = await ouvrir_worktree(depot, PROJET, TICKET, "demo", PolitiqueRun.lire(depot))
    assert ouvert is not None
    wt, absents = ouvert
    orch: Orchestrator = await build_orchestrator(PROJET, wt, tuple(absents))

    async def preparation_qui_ecrit() -> ResultatPreparation:
        (wt.racine / "reste.txt").write_text("sorti de la préparation", encoding="utf-8")
        return ResultatPreparation(COMMANDE, 1_000, 1, "échec")

    orch._preparation = preparation_qui_ecrit
    resultat = await orch.run_pipeline(PROJET, TICKET, _evenement)

    assert resultat.commit_sha is not None
    sujets = git(depot, "log", "-3", "--format=%s", wt.branche)
    assert "unapproved work (worktree setup failed" in sujets
    assert not wt.racine.exists()


async def test_the_worktree_is_gone_after_a_failed_setup(depot: Path) -> None:
    _, wt = await _run_qui_echoue(depot)

    assert not wt.racine.exists()
    assert str(wt.racine) not in git(depot, "worktree", "list")
    assert git(depot, "branch", "--show-current") == "develop"


async def test_the_log_line_of_the_failure_names_the_command_and_the_duration(
    depot: Path,
) -> None:
    _, wt = await _run_qui_echoue(depot)

    journal = git(depot, "show", f"{wt.branche}:memory/pipeline-log.md")
    # `git` décode en cp1252 sous Windows : on cherche sur les parties ASCII.
    lignes = [ln for ln in journal.splitlines() if COMMANDE in ln and "420000 ms" in ln]
    assert len(lignes) == 1 and "[ticket-7]" in lignes[0]


async def test_the_ticket_can_be_relaunched_after_a_failed_setup(depot: Path) -> None:
    _, wt = await _run_qui_echoue(depot)
    assert "tickets/blocked/ticket-7-demo.md" in git(
        depot, "ls-tree", "-r", "--name-only", wt.branche
    ).splitlines()

    relance = await ouvrir_worktree(depot, PROJET, TICKET, "demo", PolitiqueRun.lire(depot))

    assert relance is not None
    nouveau, _ = relance
    assert nouveau.racine == wt.racine and nouveau.racine.is_dir()
    assert git(nouveau.racine, "branch", "--show-current") == wt.branche
    assert git(nouveau.racine, "status", "--porcelain") == ""
