"""A run executes in its own worktree, never in the checkout — ticket-519 (ADR-056).

Real repository with a local origin (`depot_worktree`); no model is called. The
pipeline stages are exercised through the pieces this ticket wires: opening, the
orchestrator built on the worktree, delivery on `origin/<base>`, and removal.
"""
import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services import run_dans_worktree
from tessera.services.git_workspace import GitWorkspaceError
from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tessera.services.assemblage_run import build_orchestrator
from tessera.services.database import init_db
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.politique_run import PolitiqueRun
from tessera.services.run_dans_worktree import (
    OrchestrateurRefuse,
    RunRefuse,
    ouvrir_worktree,
    retirer_en_fin_de_run,
)
from tessera.services.run_worktree import RunWorktree
from tests.depot_worktree import construire, git
from tests.revue_structuree import revue_depuis_texte

_LOGGER = "tessera.services.run_dans_worktree"
PROJET = "checkout"
TICKET = "ticket-7"
TITRE = "demo"
DECLARATION = {
    "autonomy": "pr",
    "artifacts": "tracked",
    "base_branch": "develop",
    "worktree": {
        "populate": [
            {"path": "node_modules", "mode": "link"},
            {"path": "absent.txt", "mode": "copy"},
        ]
    },
}


@pytest.fixture
def depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = construire(tmp_path, monkeypatch)
    (repo / "agents.json").write_text(json.dumps(DECLARATION), encoding="utf-8")
    (repo / "CLAUDE.md").write_text("# Projet\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", repo.parent)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return repo


async def _ouvrir(depot: Path) -> tuple[RunWorktree, list[str]]:
    ouvert = await ouvrir_worktree(depot, PROJET, TICKET, TITRE, PolitiqueRun.lire(depot))
    assert ouvert is not None
    return ouvert


async def _orchestrateur(depot: Path) -> Orchestrator:
    wt, absents = await _ouvrir(depot)
    return await build_orchestrator(PROJET, wt, tuple(absents))


async def test_worktree_is_created_on_the_ticket_branch_without_touching_the_checkout(
    depot: Path,
) -> None:
    avant = git(depot, "status", "--porcelain")
    wt, absents = await _ouvrir(depot)

    assert git(wt.racine, "branch", "--show-current") == wt.branche
    assert git(depot, "branch", "--show-current") == "develop"
    assert git(depot, "status", "--porcelain") == avant
    assert absents == ["absent.txt"]  # signalé, sans bloquer le peuplement
    assert (wt.racine / "node_modules" / "pkg" / "index.js").is_file()


async def test_orchestrator_reads_and_writes_inside_the_worktree(depot: Path) -> None:
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None

    assert orch._project_path == wt.projet
    assert orch._runner._project_path == wt.projet
    assert orch._log_path.is_relative_to(wt.racine)
    assert orch._ticket_svc._root == wt.projet
    assert orch._depot == depot


async def test_delivery_rebases_on_the_remote_base_and_leaves_the_local_base_alone(
    depot: Path,
) -> None:
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None and orch._git_workspace is not None
    assert await orch._git_workspace.adopter_worktree(wt.branche, "develop") == wt.branche
    (wt.racine / "travail.txt").write_text("travail", encoding="utf-8")
    await orch._git_workspace.commit_all("feat: work")
    # La base distante avance pendant le run.
    (depot / "autre.txt").write_text("autre", encoding="utf-8")
    git(depot, "add", "autre.txt")
    git(depot, "commit", "-m", "advance base")
    git(depot, "push", "origin", "develop")
    tete_locale = git(depot, "rev-parse", "develop")

    assert await orch._git_workspace.sync_base_depuis_distant("develop") is None
    assert await orch._git_workspace.rejouer_sur("develop") == ()

    assert (wt.racine / "autre.txt").is_file() and (wt.racine / "travail.txt").is_file()
    assert git(depot, "rev-parse", "develop") == tete_locale
    assert git(depot, "branch", "--show-current") == "develop"


async def test_worktree_is_removed_after_the_run(depot: Path) -> None:
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None
    resultat = PipelineResult(
        ticket_id=TICKET, final_status=TicketStatus.done, rounds=1, approved=True
    )

    rendu = await retirer_en_fin_de_run(orch, resultat)

    assert rendu == resultat
    assert not wt.racine.exists()
    assert str(wt.racine) not in git(depot, "worktree", "list")
    assert (depot / "node_modules" / "pkg" / "index.js").is_file()  # la cible d'un lien survit


@pytest.mark.parametrize(
    "erreur", [OSError(3, "chemin introuvable"), GitWorkspaceError("worktree remove a échoué")]
)
async def test_a_removal_failure_after_delivery_leaves_the_run_result_unchanged(
    depot: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
    erreur: Exception,
) -> None:
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None

    async def panne(*_: object, **__: object) -> None:
        raise erreur

    monkeypatch.setattr(run_dans_worktree, "supprimer", panne)
    resultat = PipelineResult(
        ticket_id=TICKET, final_status=TicketStatus.done, rounds=1, approved=True
    )

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        rendu = await retirer_en_fin_de_run(orch, resultat)

    assert rendu == resultat  # même final_status, même arret : livré reste livré
    journal = [r for r in caplog.records if r.getMessage() == "run_worktree_non_supprime"]
    assert [r.__dict__["racine"] for r in journal] == [str(wt.racine)]
    assert wt.racine.exists()  # le worktree reste pour la reprise au démarrage


async def test_uncommitted_work_in_the_worktree_blocks_the_run_and_keeps_the_folder(depot: Path) -> None:
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None
    (wt.racine / "oublie.txt").write_text("pas commité", encoding="utf-8")
    resultat = PipelineResult(
        ticket_id=TICKET, final_status=TicketStatus.done, rounds=1, approved=True
    )

    rendu = await retirer_en_fin_de_run(orch, resultat)

    assert rendu.final_status is TicketStatus.blocked
    assert rendu.arret is not None and str(wt.racine) in rendu.arret
    assert (wt.racine / "oublie.txt").is_file()


async def test_branch_already_checked_out_refuses_the_run_without_any_commit(
    depot: Path,
) -> None:
    git(depot, "checkout", "-b", "ticket-7-demo")
    tete = git(depot, "rev-parse", "HEAD")

    with pytest.raises(OrchestrateurRefuse) as refus:
        await _ouvrir(depot)
    evenements: list[object] = []

    async def noter(evenement: object) -> None:
        evenements.append(evenement)

    resultat = await RunRefuse(refus.value.arret).run_pipeline(PROJET, TICKET, noter)

    assert resultat.final_status is TicketStatus.blocked and not resultat.approved
    assert "ticket-7-demo" in (resultat.arret or "")
    assert git(depot, "rev-parse", "HEAD") == tete and evenements


async def test_project_without_worktree_is_built_as_before(depot: Path) -> None:
    (depot / "agents.json").write_text(json.dumps({"autonomy": "pr"}), encoding="utf-8")

    orch = await build_orchestrator(PROJET)

    assert orch._worktree is None and orch._depot is None
    assert orch._project_path == depot
    assert await ouvrir_worktree(
        depot, PROJET, TICKET, TITRE, PolitiqueRun.lire(depot)
    ) is None
    resultat = PipelineResult(
        ticket_id=TICKET, final_status=TicketStatus.done, rounds=1, approved=True
    )
    assert await retirer_en_fin_de_run(orch, resultat) == resultat


# ------------------------------------------------------------------
# Un run complet, de la branche au push, avec un faux provider
# ------------------------------------------------------------------

FICHE = "\n".join([
    "---", "id: ticket-7", 'title: "demo"', "type: feat", "status: todo",
    "priority: medium", "agent: codeur", "---", "", "# ticket-7", "",
])
FICHE_A_LA_MAIN = "\n".join(
    ["---", "id: ticket-99", 'title: "manuel"', "type: feat", "status: todo", "---", ""]
)


class _RunnerFactice:
    """Plays the coder (writes a file where its cwd is) and the reviewer (approves)."""

    def __init__(self, racine: Path) -> None:
        self._racine = racine

    async def run(self, role: object, ticket: object, project_context: str, **_: object) -> AgentResult:
        nom = role.value if isinstance(role, AgentRole) else str(role)
        if nom == "codeur":
            (self._racine / "produit.txt").write_text("produit", encoding="utf-8")
        content = "fait" if nom == "codeur" else "APPROVED"
        return AgentResult(
            role=AgentRole(nom), ticket_id=TICKET,
            content=content, structured=revue_depuis_texte(content),
            suggested_status=TicketStatus.in_review, duration_ms=1,
        )


def _livreur_local(orch: Orchestrator) -> Callable[[PipelineResult], object]:
    """Phase 1 without GitHub: refresh the base, rebase, push the branch."""

    async def livrer(resultat: PipelineResult) -> Livraison:
        espace = orch._git_workspace
        assert espace is not None and resultat.branch is not None
        await espace.sync_base_depuis_distant("develop")
        await espace.commit_bookkeeping()
        assert await espace.rejouer_sur("develop") == ()
        await espace.push_branch(resultat.branch)
        return Livraison(etapes=("push",), durees_ms=(0.0,))

    return livrer


async def _depot_pret(depot: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # La fiche du ticket est sur origin/develop : c'est là que le worktree la prend.
    fiche = depot / "tickets" / "todo" / "ticket-7-demo.md"
    fiche.parent.mkdir(parents=True)
    fiche.write_text(FICHE, encoding="utf-8")
    git(depot, "add", "tickets")
    git(depot, "commit", "-m", "add ticket")
    git(depot, "push", "origin", "develop")
    # Une fiche écrite à la main dans le checkout, hors git (PR #508).
    (depot / "tickets" / "todo" / "ticket-99-manuel.md").write_text(FICHE_A_LA_MAIN, encoding="utf-8")
    monkeypatch.setattr(settings, "ide_db_path", tmp_path / "ide.db")
    await init_db(tmp_path / "ide.db")


async def _evenement(_: OrchestratorEvent) -> None:
    return None


async def test_a_full_run_leaves_the_checkout_identical_and_pushes_its_branch(
    depot: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _depot_pret(depot, tmp_path, monkeypatch)
    avant = git(depot, "status", "--porcelain")
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None
    orch._runner = _RunnerFactice(wt.projet)  # type: ignore[assignment]
    orch._livrer = _livreur_local(orch)  # type: ignore[assignment,assignment]
    orch._surveiller = None

    resultat = await orch.run_pipeline(PROJET, TICKET, _evenement)

    assert resultat.approved, resultat.arret
    assert git(depot, "branch", "--show-current") == "develop"
    assert git(depot, "status", "--porcelain") == avant
    assert (depot / "tickets" / "todo" / "ticket-99-manuel.md").read_text(encoding="utf-8") == FICHE_A_LA_MAIN
    assert "ticket-7-demo" in git(depot, "ls-remote", "--heads", "origin", "ticket-7-demo")
    # Le commit du run porte son travail, et pas la fiche posée à la main.
    fichiers = git(depot, "ls-tree", "-r", "--name-only", "origin/ticket-7-demo").splitlines()
    assert "produit.txt" in fichiers and "tickets/todo/ticket-99-manuel.md" not in fichiers
    assert not wt.racine.exists()


async def test_the_worktree_is_removed_when_the_run_raises(depot: Path) -> None:
    orch = await _orchestrateur(depot)
    wt = orch._worktree
    assert wt is not None

    async def panne(*_: object, **__: object) -> PipelineResult:
        raise RuntimeError("panne")

    orch._mener_le_run = panne  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        await orch.run_pipeline(PROJET, TICKET, _evenement)

    assert not wt.racine.exists()
    assert git(depot, "branch", "--show-current") == "develop"
